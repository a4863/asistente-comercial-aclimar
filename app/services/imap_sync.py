"""Read-only IMAP ingestion with durable per-occurrence checkpoints."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
import json

from app.persistence.models import SourceRecord
from app.persistence.repositories import IMAPSyncRepository


@dataclass(frozen=True)
class FolderSyncResult:
    folder: str
    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failure_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SyncResult:
    state: str
    folders: tuple[FolderSyncResult, ...]
    failure_codes: tuple[str, ...] = ()


class _Failure(Exception):
    def __init__(self, code):
        self.code = code


_EMAIL_FIELDS = (
    "normalized_message_id", "sender_address", "recipient_addresses", "subject",
    "sent_at", "received_at", "in_reply_to", "references_header", "normalized_body",
    "body_size_bytes", "content_truncated",
)
_PART_FIELDS = ("part_index", "filename", "media_type", "byte_size", "content_id", "disposition", "provenance")


def _now(clock):
    value = clock.now() if hasattr(clock, "now") else datetime.combine(clock.today(), time.min, timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise _Failure("clock_invalid")
    return value


def _values(message):
    sent_at = message.sent_at
    if sent_at is not None and sent_at.tzinfo is not None:
        sent_at = sent_at.astimezone(timezone.utc).replace(tzinfo=None)
    return {
        "normalized_message_id": message.normalized_message_id,
        "sender_address": message.sender_address,
        "recipient_addresses": json.dumps(message.recipient_addresses, ensure_ascii=False, separators=(",", ":")),
        "subject": message.subject,
        "sent_at": sent_at,
        "received_at": None,
        "in_reply_to": message.in_reply_to,
        "references_header": message.references_header,
        "normalized_body": message.normalized_body,
        "body_size_bytes": message.body_size_bytes,
        "content_truncated": message.content_truncated,
    }


def _parts(message):
    return [dict(part_index=p.part_index, filename=p.filename, media_type=p.media_type,
                 byte_size=p.byte_size, content_id=p.content_id, disposition=p.disposition,
                 provenance="imap_sync") for p in message.attachments]


def _digest(values, parts):
    def safe(value):
        return value.isoformat() if isinstance(value, datetime) else value
    payload = ([safe(values[field]) for field in _EMAIL_FIELDS],
               [[safe(part[field]) for field in _PART_FIELDS] for part in sorted(parts, key=lambda p: p["part_index"])])
    return sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _candidate(repo, message, account_scope, inventories):
    if inventories is None or not message.normalized_message_id or message.normalized_body is None or message.content_truncated:
        return None
    matches = repo.find_message_id_candidates(account_scope, message.normalized_message_id)
    if len(matches) != 1:
        return None
    email = matches[0]
    if (email.content_truncated or email.normalized_body is None or email.normalized_body != message.normalized_body
            or not email.sender_address or not message.sender_address or email.sender_address != message.sender_address
            or email.sent_at is None or message.sent_at is None or email.sent_at != _values(message)["sent_at"]):
        return None
    incoming = _values(message)
    for field in ("subject", "recipient_addresses", "in_reply_to", "references_header"):
        if getattr(email, field) is not None and incoming[field] is not None and getattr(email, field) != incoming[field]:
            return None
    source = repo.session.get(SourceRecord, email.source_record_id)
    for location in repo.list_source_locations(source):
        snapshot = inventories.get(location.folder_name)
        if snapshot and location.uidvalidity == snapshot[0] and location.uid in snapshot[1]:
            return None
    return email


def _transaction(session_factory, action):
    session = session_factory()
    try:
        result = action(IMAPSyncRepository(session))
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _persist(repo, account, folder, uidvalidity, uid, message, observed_at, inventories):
    values, parts = _values(message), _parts(message)
    exact = repo.find_location(account, folder, uidvalidity, uid)
    if exact:
        location, email, source = exact
        if location.location_state != "active":
            raise _Failure("reactivation_deferred")
        repo.set_location_state(location, "active", observed_at)
        changed = repo.update_email(email, values)
        changed = repo.replace_attachments(email, parts) or changed
        kind = "updated" if changed else "skipped"
    else:
        email = _candidate(repo, message, account, inventories)
        if email is None:
            source, email, location = repo.create_independent_occurrence(account, folder, uidvalidity, uid, observed_at, values)
        else:
            source = repo.session.get(SourceRecord, email.source_record_id)
            location = repo.link_location(email, account, folder, uidvalidity, uid, observed_at)
            additions = {key: value for key, value in values.items() if getattr(email, key) is None and value is not None}
            if additions:
                repo.update_email(email, additions)
        repo.replace_attachments(email, parts)
        kind = "created"
    repo.reserve_occurrence_identity(source, account, folder, uidvalidity, uid)
    if kind != "skipped":
        stored = {field: getattr(email, field) for field in _EMAIL_FIELDS}
        event = "updated" if kind == "updated" else "ingested"
        _, appended = repo.append_observation(source, location, event, _digest(stored, parts), observed_at)
        if appended:
            repo.session.flush()
            repo.append_audit("imap_source_updated" if kind == "updated" else "imap_source_ingested",
                              "source_record", source.id, event, observed_at)
    repo.upsert_folder_checkpoint(account, folder, uidvalidity, uid, observed_at)
    return kind


def synchronize_account(adapter, settings, session_factory, clock) -> SyncResult:
    """Ingest configured folders without mailbox mutation or real-account assumptions."""
    results, global_failures = [], []
    connected = False
    try:
        adapter.connect()
        connected = True
        folders = tuple(f.name for f in adapter.allowed_folders() if f.name in settings.folder_allowlist)
        inventories, checkpoints, failures = {}, {}, {}
        for folder in folders:
            try:
                selected = adapter.select_read_only(folder)
                if not isinstance(selected.uidvalidity, int) or selected.uidvalidity <= 0:
                    raise _Failure("uidvalidity_invalid")
                uids = tuple(adapter.search_uids(None))
                if any(not isinstance(uid, int) or uid <= 0 for uid in uids):
                    raise _Failure("inventory_invalid")
                inventories[folder] = (selected.uidvalidity, frozenset(uids))
                checkpoints[folder] = _transaction(session_factory, lambda repo: repo.read_folder_checkpoint(settings.account_scope, folder))
            except _Failure as error:
                failures[folder] = error.code
            except Exception:
                failures[folder] = "inventory_failed"
        complete = inventories if not failures and len(inventories) == len(folders) else None
        for folder in folders:
            if folder in failures:
                results.append(FolderSyncResult(folder, failure_codes=(failures[folder],)))
                continue
            uidvalidity, inventory = inventories[folder]
            checkpoint = checkpoints[folder]
            processed = created = updated = skipped = 0
            failure = None
            try:
                selected = adapter.select_read_only(folder)
                if selected.uidvalidity != uidvalidity:
                    raise _Failure("uidvalidity_changed")
                if checkpoint is None or checkpoint[1] != uidvalidity:
                    since = clock.today() - timedelta(days=settings.initial_window_days)
                    uids = tuple(adapter.search_uids(since))
                    if any(not isinstance(uid, int) or uid <= 0 or uid not in inventory for uid in uids):
                        raise _Failure("historical_search_invalid")
                else:
                    uids = tuple(uid for uid in inventory if uid > checkpoint[2])
                ordered = sorted(set(uids))
                if not ordered:
                    highest = checkpoint[2] if checkpoint and checkpoint[1] == uidvalidity else 0
                    observed_at = _now(clock)
                    _transaction(session_factory, lambda repo: repo.upsert_folder_checkpoint(settings.account_scope, folder, uidvalidity, highest, observed_at))
                for uid in ordered:
                    try:
                        fetched = tuple(adapter.fetch_messages((uid,)))
                        if len(fetched) != 1 or fetched[0].uid != uid:
                            raise _Failure("fetch_invalid")
                        observed_at = _now(clock)
                        kind = _transaction(session_factory, lambda repo: _persist(repo, settings.account_scope, folder, uidvalidity, uid, fetched[0], observed_at, complete))
                    except _Failure as error:
                        failure = error.code
                        break
                    except Exception:
                        failure = "message_failed"
                        break
                    processed += 1
                    created += kind == "created"
                    updated += kind == "updated"
                    skipped += kind == "skipped"
            except _Failure as error:
                failure = error.code
            except Exception:
                failure = "folder_failed"
            results.append(FolderSyncResult(folder, processed, created, updated, skipped, (failure,) if failure else ()))
    except Exception:
        global_failures.append("connection_or_discovery_failed")
    finally:
        if connected:
            try:
                adapter.disconnect()
            except Exception:
                global_failures.append("disconnect_failed")
    return SyncResult("degraded" if global_failures or any(r.failure_codes for r in results) else "success",
                      tuple(results), tuple(global_failures))
