"""Synthetic-only tests for the 3C2 synchronization boundary."""

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import IMAPSettings
from app.integrations.imap_adapter import AttachmentMetadata, FetchedMessage, MailboxFolder, SelectedMailbox
from app.persistence.models import (
    AuditEvent, EmailAttachmentMetadata, EmailMessage, IdempotencyIdentity,
    IMAPMessageLocation, SourceObservation, SourceRecord, SynchronizationCheckpoint,
)
from app.services.imap_sync import synchronize_account


WHEN = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)


class Clock:
    def today(self):
        return date(2026, 9, 22)

    def now(self):
        return WHEN


def message(uid, **changes):
    base = FetchedMessage(
        uid=uid, normalized_message_id=f"<{uid}@example.test>", sender_address="from@example.test",
        recipient_addresses=("to@example.test",), subject="Synthetic", sent_at=WHEN,
        in_reply_to=None, references_header=None, normalized_body="safe body",
        body_size_bytes=9, content_truncated=False,
        attachments=(AttachmentMetadata(0, "quote.pdf", "application/pdf", 42, None, "attachment"),),
    )
    return replace(base, **changes)


class FakeAdapter:
    def __init__(self, folders):
        # folder -> (uidvalidity, {uid: FetchedMessage})
        self.folders = folders
        self.selected = None
        self.calls = []
        self.fail = set()
        self.connected = False
        self.history = {}

    def connect(self):
        self.calls.append(("connect",))
        self.connected = True

    def disconnect(self):
        self.calls.append(("disconnect",))
        self.connected = False

    def allowed_folders(self):
        self.calls.append(("allowed_folders",))
        return tuple(MailboxFolder(name, "/", ()) for name in self.folders)

    def select_read_only(self, folder):
        self.calls.append(("select_read_only", folder))
        if ("select", folder) in self.fail:
            raise RuntimeError("SECRET select failure")
        self.selected = folder
        return SelectedMailbox(folder, self.folders[folder][0], ())

    def search_uids(self, since=None):
        self.calls.append(("search_uids", self.selected, since))
        if ("inventory" if since is None else "history", self.selected) in self.fail:
            raise RuntimeError("SECRET search failure")
        messages = self.folders[self.selected][1]
        if since is None:
            return tuple(reversed(tuple(messages)))
        return self.history.get(self.selected, tuple(reversed(tuple(messages))))

    def fetch_messages(self, uids):
        self.calls.append(("fetch_messages", self.selected, tuple(uids)))
        if ("fetch", self.selected) in self.fail:
            raise RuntimeError("SECRET fetch failure")
        return tuple(self.folders[self.selected][1][uid] for uid in uids)


@pytest.fixture
def factory(db_session):
    return sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)


def settings(*folders):
    return IMAPSettings(account_scope="imap:test", folder_allowlist=folders or ("INBOX",), initial_window_days=30)


def rows(factory, model):
    with factory() as session:
        return tuple(session.scalars(select(model).order_by(model.id)))


def run(adapter, factory, *folders):
    return synchronize_account(adapter, settings(*folders), factory, Clock())


def test_initial_sorted_two_folders_and_persistence(factory):
    adapter = FakeAdapter({"INBOX": (42, {9: message(9), 2: message(2)}), "Sent": (17, {4: message(4)})})
    result = run(adapter, factory, "INBOX", "Sent")
    assert result.state == "success"
    assert [(r.processed, r.created) for r in result.folders] == [(2, 2), (1, 1)]
    assert [call[-1] for call in adapter.calls if call[0] == "fetch_messages" and call[1] == "INBOX"] == [(2,), (9,)]
    assert ("search_uids", "INBOX", date(2026, 8, 23)) in adapter.calls
    assert len(rows(factory, SourceRecord)) == len(rows(factory, EmailMessage)) == 3
    assert len(rows(factory, IMAPMessageLocation)) == len(rows(factory, IdempotencyIdentity)) == 3
    assert len(rows(factory, EmailAttachmentMetadata)) == len(rows(factory, SourceObservation)) == len(rows(factory, AuditEvent)) == 3
    assert len(rows(factory, SynchronizationCheckpoint)) == 2
    assert all(r.provenance == "imap_sync" for r in rows(factory, EmailAttachmentMetadata))
    assert all("safe body" not in str(r.source_version_marker) for r in rows(factory, SourceObservation))
    assert not adapter.connected
    assert not any(call[0] in {"move", "create_folder", "append", "store", "expunge"} for call in adapter.calls)


def test_empty_initial_incremental_holes_restart_and_replay(factory):
    adapter = FakeAdapter({"INBOX": (42, {})})
    assert run(adapter, factory).state == "success"
    assert rows(factory, SynchronizationCheckpoint)[0].checkpoint_marker == "v1:42:0"
    adapter.folders["INBOX"][1].update({3: message(3), 8: message(8)})
    assert run(adapter, factory).folders[0].created == 2
    assert rows(factory, SynchronizationCheckpoint)[0].checkpoint_marker == "v1:42:8"
    before = (len(rows(factory, SourceObservation)), len(rows(factory, AuditEvent)))
    assert run(adapter, factory).folders[0].processed == 0
    assert run(adapter, factory).folders[0].processed == 0
    assert (len(rows(factory, SourceObservation)), len(rows(factory, AuditEvent))) == before
    adapter.folders["INBOX"][1][12] = message(12)
    assert run(adapter, factory).folders[0].created == 1
    assert rows(factory, SynchronizationCheckpoint)[0].checkpoint_marker == "v1:42:12"


def test_reset_restarts_window_and_preserves_old_location(factory):
    adapter = FakeAdapter({"INBOX": (42, {80: message(80)})})
    assert run(adapter, factory).state == "success"
    adapter.folders["INBOX"] = (43, {2: message(2)})
    result = run(adapter, factory)
    assert result.state == "success" and result.folders[0].created == 1
    assert ("search_uids", "INBOX", date(2026, 8, 23)) in adapter.calls
    assert rows(factory, SynchronizationCheckpoint)[0].checkpoint_marker == "v1:43:2"
    assert {(r.uidvalidity, r.uid, r.location_state) for r in rows(factory, IMAPMessageLocation)} == {(42, 80, "active"), (43, 2, "active")}


def test_exact_replay_and_material_update(factory):
    adapter = FakeAdapter({"INBOX": (42, {7: message(7)})})
    assert run(adapter, factory).state == "success"
    # Force an exact replay through a fresh namespace checkpoint while retaining the location.
    with factory.begin() as session:
        session.delete(session.scalar(select(SynchronizationCheckpoint)))
    assert run(adapter, factory).folders[0].skipped == 1
    assert len(rows(factory, SourceObservation)) == len(rows(factory, AuditEvent)) == 1
    adapter.folders["INBOX"][1][7] = message(7, subject="Changed", attachments=())
    with factory.begin() as session:
        session.delete(session.scalar(select(SynchronizationCheckpoint)))
    assert run(adapter, factory).folders[0].updated == 1
    assert len(rows(factory, SourceObservation)) == len(rows(factory, AuditEvent)) == 2
    assert len(rows(factory, EmailAttachmentMetadata)) == 0
    assert rows(factory, EmailMessage)[0].subject == "Changed"


def test_conservative_correlation_and_duplicate_cases(factory):
    first = message(1, normalized_message_id="<shared@test>")
    adapter = FakeAdapter({"INBOX": (42, {1: first}), "Sent": (42, {})})
    assert run(adapter, factory, "INBOX", "Sent").state == "success"
    # Old UID absent from a complete inventory: one corroborated candidate links.
    adapter.folders["INBOX"][1].clear()
    adapter.folders["Sent"][1][2] = message(2, normalized_message_id="<shared@test>")
    result = run(adapter, factory, "INBOX", "Sent")
    assert result.folders[1].created == 1
    assert len(rows(factory, SourceRecord)) == 1
    assert len(rows(factory, IMAPMessageLocation)) == 2
    # A conflicting subject creates a separate logical occurrence.
    adapter.folders["Sent"][1][3] = message(3, normalized_message_id="<shared@test>", subject="Conflict")
    assert run(adapter, factory, "INBOX", "Sent").folders[1].created == 1
    assert len(rows(factory, SourceRecord)) == 2
    # Multiple candidates never merge, even with otherwise matching content.
    adapter.folders["Sent"][1][4] = message(4, normalized_message_id="<shared@test>")
    assert run(adapter, factory, "INBOX", "Sent").folders[1].created == 1
    assert len(rows(factory, SourceRecord)) == 3
    adapter.folders["Sent"][1][5] = message(5, normalized_message_id=None)
    assert run(adapter, factory, "INBOX", "Sent").folders[1].created == 1
    assert len(rows(factory, SourceRecord)) == 4


@pytest.mark.parametrize("stage", ["select", "inventory", "history", "fetch"])
def test_adapter_failures_are_safe_and_other_folder_continues(factory, stage):
    adapter = FakeAdapter({"INBOX": (42, {1: message(1)}), "Sent": (42, {2: message(2)})})
    adapter.fail.add((stage, "INBOX"))
    result = run(adapter, factory, "INBOX", "Sent")
    assert result.state == "degraded"
    assert result.folders[0].failure_codes and result.folders[1].created == 1
    assert "SECRET" not in repr(result)
    assert len(rows(factory, SourceRecord)) == 1
    adapter.fail.clear()
    assert run(adapter, factory, "INBOX", "Sent").state == "success"
    assert len(rows(factory, SourceRecord)) == 2


def test_partial_inventory_disables_correlation(factory):
    adapter = FakeAdapter({"INBOX": (42, {1: message(1, normalized_message_id="<same@test>")}), "Sent": (42, {})})
    run(adapter, factory, "INBOX", "Sent")
    adapter.folders["INBOX"][1].clear()
    adapter.folders["Sent"][1][2] = message(2, normalized_message_id="<same@test>")
    adapter.fail.add(("inventory", "INBOX"))
    result = run(adapter, factory, "INBOX", "Sent")
    assert result.state == "degraded" and result.folders[1].created == 1
    assert len(rows(factory, SourceRecord)) == 2


def test_present_old_location_and_unavailable_replay_do_not_transition(factory):
    adapter = FakeAdapter({"INBOX": (42, {1: message(1, normalized_message_id="<same@test>")}), "Sent": (42, {})})
    run(adapter, factory, "INBOX", "Sent")
    adapter.folders["Sent"][1][2] = message(2, normalized_message_id="<same@test>")
    assert run(adapter, factory, "INBOX", "Sent").folders[1].created == 1
    assert len(rows(factory, SourceRecord)) == 2
    with factory.begin() as session:
        location = session.scalar(select(IMAPMessageLocation).where(IMAPMessageLocation.uid == 1))
        location.location_state = "unavailable"
        session.delete(session.scalar(select(SynchronizationCheckpoint).where(SynchronizationCheckpoint.checkpoint_marker == "v1:42:1")))
    result = run(adapter, factory, "INBOX", "Sent")
    assert result.state == "degraded"
    assert result.folders[0].failure_codes == ("reactivation_deferred",)
    assert next(r for r in rows(factory, IMAPMessageLocation) if r.uid == 1).location_state == "unavailable"


def test_repository_write_failure_rolls_back_and_retries(factory, monkeypatch):
    from app.persistence.repositories import IMAPSyncRepository
    adapter = FakeAdapter({"INBOX": (42, {1: message(1)})})
    original = IMAPSyncRepository.reserve_occurrence_identity

    def fail_write(self, *args, **kwargs):
        raise RuntimeError("SECRET repository failure")

    monkeypatch.setattr(IMAPSyncRepository, "reserve_occurrence_identity", fail_write)
    result = run(adapter, factory)
    assert result.state == "degraded" and result.folders[0].failure_codes == ("message_failed",)
    assert "SECRET" not in repr(result)
    assert not rows(factory, SourceRecord)
    assert not rows(factory, SynchronizationCheckpoint)
    monkeypatch.setattr(IMAPSyncRepository, "reserve_occurrence_identity", original)
    assert run(adapter, factory).folders[0].created == 1


def test_repository_audit_and_commit_failures_rollback(factory, monkeypatch):
    from app.persistence.repositories import IMAPSyncRepository
    adapter = FakeAdapter({"INBOX": (42, {1: message(1), 2: message(2)}), "Sent": (42, {3: message(3)})})
    original = IMAPSyncRepository.append_audit

    def broken_audit(self, *args, **kwargs):
        if self.session.scalar(select(IMAPMessageLocation).where(IMAPMessageLocation.uid == 2)):
            raise RuntimeError("SECRET audit failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(IMAPSyncRepository, "append_audit", broken_audit)
    result = run(adapter, factory, "INBOX", "Sent")
    assert result.state == "degraded" and result.folders[0].processed == 1 and result.folders[1].created == 1
    assert "SECRET" not in repr(result)
    assert rows(factory, SynchronizationCheckpoint)[0].checkpoint_marker == "v1:42:1"
    assert {r.uid for r in rows(factory, IMAPMessageLocation)} == {1, 3}
    monkeypatch.setattr(IMAPSyncRepository, "append_audit", original)
    assert run(adapter, factory, "INBOX", "Sent").folders[0].created == 1

    class CommitFailSession:
        def __init__(self, inner):
            self.inner = inner
            self.fail_once = True

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def commit(self):
            self.inner.flush()
            raise RuntimeError("SECRET commit failure")

    adapter.folders["INBOX"][1][4] = message(4)
    normal_factory = factory
    counter = {"calls": 0}

    def failing_factory():
        counter["calls"] += 1
        session = normal_factory()
        # Inventory checkpoint read is the first session. Fail the message commit.
        return CommitFailSession(session) if counter["calls"] == 3 else session

    result = run(adapter, failing_factory, "INBOX", "Sent")
    assert result.state == "degraded" and "SECRET" not in repr(result)
    assert rows(factory, SynchronizationCheckpoint)[0].checkpoint_marker == "v1:42:2"
    assert 4 not in {r.uid for r in rows(factory, IMAPMessageLocation)}
    assert run(adapter, factory, "INBOX", "Sent").folders[0].created == 1
