"""Read-only IMAP ingestion with durable per-occurrence checkpoints."""

from dataclasses import dataclass, replace
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
    moved: int = 0
    unavailable: int = 0
    reactivated: int = 0


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
            # Exact reappearance is evidence, but the state transition waits
            # for a complete, successful account-wide reconciliation pass.
            repo.reserve_occurrence_identity(source, account, folder, uidvalidity, uid)
            repo.upsert_folder_checkpoint(account, folder, uidvalidity, uid, observed_at)
            return "skipped"
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


def _is_present(location, inventories):
    snapshot = inventories.get(location.folder_name)
    return bool(snapshot and location.uidvalidity == snapshot[0] and location.uid in snapshot[1])


def _transition(repo, account, identity, target, observed_at, move_identity=None):
    exact = repo.find_location(account, *identity)
    if exact is None:
        raise _Failure("reconciliation_location_missing")
    location, email, source = exact
    if location.location_state == target:
        return False
    if target == "active" and location.location_state != "unavailable":
        raise _Failure("reconciliation_state_conflict")
    if target == "unavailable" and location.location_state != "active":
        raise _Failure("reconciliation_state_conflict")
    parts = list(repo.email_attachment_values(email))
    values = {field: getattr(email, field) for field in _EMAIL_FIELDS}
    digest = _digest(values, parts)
    repo.set_location_state(location, target, observed_at)
    event = "reactivated" if target == "active" else "unavailable"
    repo.append_observation(source, location, event, digest, observed_at)
    repo.append_audit("imap_location_transitioned", "imap_message_location", location.id, event, observed_at)
    if move_identity is not None:
        destination = repo.find_location(account, *move_identity)
        if destination is None:
            raise _Failure("reconciliation_move_conflict")
        new_location, new_email, new_source = destination
        if (new_location.id == location.id or new_email.id != email.id
                or new_source.id != source.id or new_location.location_state != "active"):
            raise _Failure("reconciliation_move_conflict")
        repo.append_observation(source, new_location, "moved", digest, observed_at)
        repo.append_audit("imap_reconciled", "imap_message_location", new_location.id, "moved", observed_at)
    return True


def _identity(location):
    return location.folder_name, location.uidvalidity, location.uid


def _reconcile(account, inventories, session_factory, clock, results):
    """Transition exact reappearances, then moves, then unmatched absence."""
    by_folder = {result.folder: index for index, result in enumerate(results)}
    try:
        locations = _transaction(session_factory, lambda repo: repo.list_account_locations(account))
    except Exception:
        return results, ("reconciliation_read_failed",)
    # An absent folder has no complete inventory; retain its historical state.
    reappearances = [row for row in locations if row[0].folder_name in inventories
                     and row[0].location_state == "unavailable" and _is_present(row[0], inventories)]
    for location, _, _ in reappearances:
        folder = location.folder_name
        try:
            changed = _transaction(session_factory, lambda repo: _transition(
                repo, account, _identity(location), "active", _now(clock)
            ))
            if changed:
                results[by_folder[folder]] = replace(results[by_folder[folder]], reactivated=results[by_folder[folder]].reactivated + 1)
        except Exception:
            result = results[by_folder[folder]]
            results[by_folder[folder]] = replace(result, failure_codes=result.failure_codes + ("reconciliation_failed",))
            return results, ()
    try:
        locations = _transaction(session_factory, lambda repo: repo.list_account_locations(account))
    except Exception:
        return results, ("reconciliation_read_failed",)
    present_by_email = {}
    for location, email, _ in locations:
        if location.location_state == "active" and _is_present(location, inventories):
            present_by_email.setdefault(email.id, []).append(location)
    for location, email, _ in locations:
        if location.folder_name not in inventories or location.location_state != "active" or _is_present(location, inventories):
            continue
        matches = [other for other in present_by_email.get(email.id, ()) if other.id != location.id]
        # A prior D1-C link is the only permitted move evidence. Ambiguous
        # destination multiplicity remains an unavailable finding, not a move.
        destination = matches[0] if len(matches) == 1 else None
        folder = location.folder_name
        try:
            changed = _transaction(session_factory, lambda repo: _transition(
                repo, account, _identity(location), "unavailable", _now(clock),
                _identity(destination) if destination else None,
            ))
            if changed:
                result = results[by_folder[folder]]
                results[by_folder[folder]] = replace(
                    result,
                    moved=result.moved + (destination is not None),
                    unavailable=result.unavailable + (destination is None),
                )
        except Exception:
            result = results[by_folder[folder]]
            results[by_folder[folder]] = replace(result, failure_codes=result.failure_codes + ("reconciliation_failed",))
            return results, ()
    return results, ()


def synchronize_account(adapter, settings, session_factory, clock) -> SyncResult:
    """Ingest configured folders without mailbox mutation or real-account assumptions."""
    results, global_failures = [], []
    inventories = {}
    complete = None
    connected = False
    try:
        adapter.connect()
        connected = True
        folders = tuple(f.name for f in adapter.allowed_folders() if f.name in settings.folder_allowlist)
        checkpoints, failures = {}, {}
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
    if complete is not None and not global_failures and not any(result.failure_codes for result in results):
        results, failures = _reconcile(settings.account_scope, complete, session_factory, clock, results)
        global_failures.extend(failures)
    return SyncResult("degraded" if global_failures or any(r.failure_codes for r in results) else "success",
                      tuple(results), tuple(global_failures))
