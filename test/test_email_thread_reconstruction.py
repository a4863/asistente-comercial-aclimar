"""Synthetic, caller-transaction tests for the 3D3C reconstruction core."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.persistence.models import (
    AuditEvent, Base, Conversation, ConversationMembership, EmailMessage, SourceRecord,
    ThreadEvidence, ThreadEvidenceDecision, ThreadLineageEdge,
    ThreadLineageOperation, ThreadMembershipChange,
)
from app.persistence.database import make_session_factory
from app.persistence.repositories import ThreadPersistenceRepository
import app.services.email_thread_reconstruction as reconstruction_module
from app.services.email_thread_reconstruction import (
    ThreadReconstructionError, reconstruct_account_threads,
    reconstruct_account_threads_in_session,
)

SCOPE = "imap:test"


def _email(session, name, *, parent=None, references=None, subject="Synthetic", scope=SCOPE):
    session.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    source = SourceRecord(source_type="email_message", source_system_scope=scope,
        provenance="test")
    session.add(source)
    session.flush()
    session.add(EmailMessage(source_record_id=source.id,
        normalized_message_id=f"<{name}@example.test>",
        in_reply_to=f"<{parent}@example.test>" if parent else None,
        references_header=references, subject=subject, normalized_body="private body",
        provenance="test"))
    session.flush()
    return source


def _conversation(session, *sources, scope=SCOPE, legacy=False, superseded=False):
    row = Conversation(account_scope=None if legacy else scope,
        legacy_status="legacy_unresolved" if legacy else "resolved",
        stable_key=str(uuid4()), provenance="test",
        superseded_at=datetime.now(timezone.utc) if superseded else None)
    session.add(row)
    session.flush()
    for source in sources:
        session.add(ConversationMembership(source_record_id=source.id,
            conversation_id=row.id, evidence_type="legacy_assignment",
            evidence_reference=f"source:{source.id}"))
    session.flush()
    return row


def _count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def _run(session):
    session.connection()  # The test caller, not the service, opens the transaction.
    session.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    return reconstruct_account_threads_in_session(session, SCOPE)


def _current(session, source):
    return session.scalar(select(ConversationMembership).where(
        ConversationMembership.source_record_id == source.id))


def test_empty_corpus_and_no_audit(db_session):
    result = _run(db_session)
    assert (result.source_count, result.component_count, result.conversations_created,
            result.memberships_changed, result.lineage_operations_created) == (0, 0, 0, 0, 0)
    assert len(result.reconstruction_key) == 64
    assert _count(db_session, AuditEvent) == 0


def test_initial_singleton_replay_and_caller_transaction(db_session, monkeypatch):
    source = _email(db_session, "a")
    db_session.connection()
    for name in ("commit", "rollback", "begin", "close"):
        monkeypatch.setattr(db_session, name,
            lambda name=name: pytest.fail(f"service called {name}"))
    first = _run(db_session)
    assert (first.source_count, first.component_count, first.conversations_created,
            first.memberships_changed, first.lineage_operations_created) == (1, 1, 1, 1, 0)
    membership = _current(db_session, source)
    assert membership.evidence_type == "singleton"
    assert membership.evidence_reference == f"source:{source.id}"
    counts = tuple(_count(db_session, model) for model in (
        Conversation, ThreadEvidence, ThreadEvidenceDecision, ThreadMembershipChange,
        ThreadLineageOperation, ThreadLineageEdge))
    second = _run(db_session)
    assert second.reconstruction_key == first.reconstruction_key
    assert (second.conversations_created, second.memberships_changed,
            second.lineage_operations_created) == (0, 0, 0)
    assert counts == tuple(_count(db_session, model) for model in (
        Conversation, ThreadEvidence, ThreadEvidenceDecision, ThreadMembershipChange,
        ThreadLineageOperation, ThreadLineageEdge))
    assert _count(db_session, AuditEvent) == 0


def test_initial_multi_email_component_and_source_local_decision(db_session):
    root = _email(db_session, "root")
    child = _email(db_session, "child", parent="root")
    result = _run(db_session)
    assert (result.component_count, result.conversations_created, result.memberships_changed) == (1, 1, 2)
    assert _current(db_session, root).conversation_id == _current(db_session, child).conversation_id
    assert _current(db_session, root).evidence_type == "thread_decision"
    assert _current(db_session, root).evidence_reference == f"source:{root.id}"
    assert _current(db_session, child).evidence_type == "thread_decision"
    decision_id = int(_current(db_session, child).evidence_reference.removeprefix("decision:"))
    history = db_session.scalar(select(ThreadMembershipChange).where(
        ThreadMembershipChange.source_record_id == child.id))
    assert history.evidence_decision_id == decision_id
    root_history = db_session.scalar(select(ThreadMembershipChange).where(
        ThreadMembershipChange.source_record_id == root.id))
    assert root_history.evidence_decision_id is None
    decision = db_session.get(ThreadEvidenceDecision, decision_id)
    assert decision.target_source_record_id == root.id
    assert db_session.get(ThreadEvidence, decision.evidence_id).source_record_id == child.id


def test_same_subject_malformed_and_ambiguous_remain_singletons(db_session):
    first = _email(db_session, "same-a", subject="Same")
    second = _email(db_session, "same-b", subject="Re: Same")
    malformed = _email(db_session, "bad", parent="not a valid id")
    result = _run(db_session)
    assert result.component_count == 3
    assert len({_current(db_session, row).conversation_id for row in (first, second, malformed)}) == 3


def test_merge_and_new_unassigned_source(db_session):
    first = _email(db_session, "first")
    second = _email(db_session, "second", parent="first")
    fresh = _email(db_session, "fresh", parent="second")
    old_first = _conversation(db_session, first)
    old_second = _conversation(db_session, second)
    result = _run(db_session)
    assert (result.conversations_created, result.memberships_changed,
            result.lineage_operations_created) == (1, 3, 1)
    successor = _current(db_session, first).conversation_id
    assert successor not in (old_first.id, old_second.id)
    assert {_current(db_session, row).conversation_id for row in (first, second, fresh)} == {successor}
    assert {row.reason for row in db_session.scalars(select(ThreadMembershipChange))} == {
        "merge", "initial_assignment"}
    assert _count(db_session, ThreadLineageEdge) == 2


def test_split(db_session):
    first = _email(db_session, "first")
    second = _email(db_session, "second")
    old = _conversation(db_session, first, second)
    result = _run(db_session)
    assert (result.component_count, result.conversations_created,
            result.memberships_changed, result.lineage_operations_created) == (2, 2, 2, 1)
    assert _current(db_session, first).conversation_id != _current(db_session, second).conversation_id
    assert old.superseded_at is not None
    assert _count(db_session, ThreadLineageEdge) == 2


def test_repartition(db_session):
    a = _email(db_session, "a")
    b = _email(db_session, "b", parent="a")
    c = _email(db_session, "c")
    d = _email(db_session, "d", parent="c")
    _conversation(db_session, a, c)
    _conversation(db_session, b, d)
    result = _run(db_session)
    assert (result.conversations_created, result.memberships_changed,
            result.lineage_operations_created) == (2, 4, 1)
    assert _count(db_session, ThreadLineageEdge) == 4
    assert _current(db_session, a).conversation_id == _current(db_session, b).conversation_id
    assert _current(db_session, c).conversation_id == _current(db_session, d).conversation_id


@pytest.mark.parametrize("excluded", [False, True])
def test_correction_changed_set_or_excluded_old_member(db_session, excluded):
    first = _email(db_session, "first")
    other = _email(db_session, "other", parent="first")
    if excluded:
        old = _conversation(db_session, first, other)
        other.retention_state = "redacted"
        other.deleted_or_redacted_at = datetime.now(timezone.utc)
        db_session.flush()
    else:
        old = _conversation(db_session, first)
    result = _run(db_session)
    assert result.lineage_operations_created == 1
    assert old.superseded_at is not None
    assert db_session.scalar(select(ThreadLineageOperation.kind)) == "correction"
    assert _count(db_session, ThreadLineageEdge) == 1
    if excluded:
        assert _current(db_session, other).conversation_id == old.id
    else:
        assert _current(db_session, other).conversation_id == _current(db_session, first).conversation_id


def test_new_key_same_topology_no_history_transition(db_session):
    root = _email(db_session, "root")
    child = _email(db_session, "child", parent="root")
    first = _run(db_session)
    email = db_session.scalar(select(EmailMessage).where(EmailMessage.source_record_id == child.id))
    email.references_header = "<root@example.test>"
    db_session.flush()
    second = _run(db_session)
    assert second.reconstruction_key != first.reconstruction_key
    assert (second.conversations_created, second.memberships_changed,
            second.lineage_operations_created) == (0, 0, 0)
    assert _count(db_session, Conversation) == 1
    assert _count(db_session, ThreadMembershipChange) == 2
    assert _count(db_session, ThreadEvidenceDecision) > _count(db_session, ThreadMembershipChange)


@pytest.mark.parametrize("kind,code", [
    ("legacy", "legacy_unresolved"),
    ("superseded", "superseded_membership"),
    ("foreign", "invalid_partition"),
    ("non_email", "invalid_partition"),
])
def test_preflight_fails_before_topology_write(db_session, kind, code):
    source = _email(db_session, "source")
    if kind == "non_email":
        manual = SourceRecord(source_type="manual_note", source_system_scope="manual",
            provenance="test")
        db_session.add(manual)
        db_session.flush()
        _conversation(db_session, source, manual)
    else:
        _conversation(db_session, source, legacy=kind == "legacy",
            superseded=kind == "superseded",
            scope="imap:other" if kind == "foreign" else SCOPE)
    with pytest.raises(ThreadReconstructionError) as raised:
        _run(db_session)
    assert raised.value.code == code
    assert _count(db_session, ThreadEvidence) == 0
    assert _count(db_session, ThreadMembershipChange) == 0
    assert _count(db_session, ThreadLineageOperation) == 0


@pytest.mark.parametrize("scope,code", [
    ("", "invalid_scope"), (" ", "invalid_scope"),
    ("x" * 101, "invalid_scope"),
])
def test_invalid_scope(db_session, scope, code):
    db_session.connection()
    with pytest.raises(ThreadReconstructionError) as raised:
        reconstruct_account_threads_in_session(db_session, scope)
    assert raised.value.code == code


@pytest.fixture
def wrapper_engine(isolated_tmp_path):
    factory = make_session_factory(f"sqlite:///{isolated_tmp_path / 'thread-wrapper.db'}")
    engine = factory.kw["bind"]
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def _committed_email(engine, name, *, parent=None, old_group=None):
    with Session(engine) as session:
        source = _email(session, name, parent=parent)
        if old_group is not None:
            _conversation(session, source)
        session.commit()
        return source.id


def _counts(engine):
    with Session(engine) as session:
        return tuple(_count(session, model) for model in (
            Conversation, ThreadEvidence, ThreadEvidenceDecision,
            ThreadMembershipChange, ThreadLineageOperation, ThreadLineageEdge, AuditEvent))


def test_wrapper_empty_success_and_single_commit(wrapper_engine):
    commits = []
    def on_commit(connection):
        commits.append(connection)
    event.listen(wrapper_engine, "commit", on_commit)
    try:
        result = reconstruct_account_threads(wrapper_engine, SCOPE)
    finally:
        event.remove(wrapper_engine, "commit", on_commit)
    assert result.status == "completed"
    assert (result.source_count, result.component_count, result.conversations_created,
            result.memberships_changed, result.lineage_operations_created) == (0, 0, 0, 0, 0)
    assert len(result.reconstruction_key) == 64
    assert len(commits) == 1
    assert _counts(wrapper_engine) == (0,) * 7


def test_wrapper_reserves_before_snapshot_and_binds_same_connection(wrapper_engine, monkeypatch):
    _committed_email(wrapper_engine, "a")
    statements = []
    def on_sql(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(wrapper_engine, "before_cursor_execute", on_sql)
    original = ThreadPersistenceRepository.load_account_thread_snapshot
    observed = []
    def snapshot(repo, scope):
        observed.append((repo.session.connection(), tuple(statements)))
        return original(repo, scope)
    monkeypatch.setattr(ThreadPersistenceRepository, "load_account_thread_snapshot", snapshot)
    try:
        result = reconstruct_account_threads(wrapper_engine, SCOPE)
    finally:
        event.remove(wrapper_engine, "before_cursor_execute", on_sql)
    assert result.status == "completed" and result.source_count == 1
    assert len(observed) == 1
    assert "BEGIN IMMEDIATE" in observed[0][1]
    assert observed[0][1].index("BEGIN IMMEDIATE") < len(observed[0][1]) - 1
    assert observed[0][0].engine is wrapper_engine
    assert _counts(wrapper_engine)[-1] == 0


def test_wrapper_exact_replay_has_no_duplicates(wrapper_engine):
    _committed_email(wrapper_engine, "root")
    _committed_email(wrapper_engine, "child", parent="root")
    first = reconstruct_account_threads(wrapper_engine, SCOPE)
    before = _counts(wrapper_engine)
    second = reconstruct_account_threads(wrapper_engine, SCOPE)
    assert first.status == second.status == "completed"
    assert first.reconstruction_key == second.reconstruction_key
    assert (second.conversations_created, second.memberships_changed,
            second.lineage_operations_created) == (0, 0, 0)
    assert _counts(wrapper_engine) == before


@pytest.mark.parametrize("stage", ["append_evidence", "append_decision",
    "create_resolved_conversation", "record_lineage_operation", "assign_current_membership"])
def test_wrapper_rolls_back_every_injected_stage(wrapper_engine, monkeypatch, stage):
    with Session(wrapper_engine) as session:
        first = _email(session, "first")
        second = _email(session, "second", parent="first")
        if stage == "record_lineage_operation":
            _conversation(session, first)
            _conversation(session, second)
        session.commit()
    before = _counts(wrapper_engine)
    original = getattr(ThreadPersistenceRepository, stage)
    calls = []
    def fail_after_write(repo, *args, **kwargs):
        result = original(repo, *args, **kwargs)
        calls.append(1)
        raise RuntimeError("injected after write")
    monkeypatch.setattr(ThreadPersistenceRepository, stage, fail_after_write)
    with pytest.raises(ThreadReconstructionError) as raised:
        reconstruct_account_threads(wrapper_engine, SCOPE)
    assert raised.value.code == "persistence_conflict"
    assert calls == [1]
    assert _counts(wrapper_engine) == before


def test_wrapper_preserves_core_error_and_rolls_back(wrapper_engine, monkeypatch):
    _committed_email(wrapper_engine, "a")
    before = _counts(wrapper_engine)
    def fail(session, scope):
        session.add(Conversation(account_scope=SCOPE, legacy_status="resolved",
            stable_key=str(uuid4()), provenance="test"))
        session.flush()
        raise ThreadReconstructionError("invalid_partition")
    monkeypatch.setattr(reconstruction_module, "reconstruct_account_threads_in_session", fail)
    with pytest.raises(ThreadReconstructionError) as raised:
        reconstruct_account_threads(wrapper_engine, SCOPE)
    assert raised.value.code == "invalid_partition"
    assert _counts(wrapper_engine) == before


@pytest.mark.parametrize("busy_attempts", [1, 2, 3])
def test_wrapper_retries_only_busy_acquisition(wrapper_engine, monkeypatch, busy_attempts):
    attempts = []
    waits = []
    def on_sql(connection, cursor, statement, parameters, context, executemany):
        if statement == "BEGIN IMMEDIATE":
            attempts.append(connection)
            if len(attempts) <= busy_attempts:
                raise __import__("sqlite3").OperationalError("database is locked")
    event.listen(wrapper_engine, "before_cursor_execute", on_sql)
    monkeypatch.setattr(reconstruction_module, "_sleep", waits.append)
    try:
        result = reconstruct_account_threads(wrapper_engine, SCOPE)
    finally:
        event.remove(wrapper_engine, "before_cursor_execute", on_sql)
    assert len(attempts) == min(busy_attempts + 1, 3)
    assert len({id(connection) for connection in attempts}) == len(attempts)
    assert waits == [0.1] * min(busy_attempts, 2)
    if busy_attempts == 3:
        assert (result.status, result.reconstruction_key, result.source_count,
                result.component_count, result.conversations_created,
                result.memberships_changed, result.lineage_operations_created) == (
                "busy_retry_later", None, None, None, 0, 0, 0)
    else:
        assert result.status == "completed"


def test_wrapper_busy_after_reservation_does_not_retry(wrapper_engine, monkeypatch):
    attempts = []
    def on_sql(connection, cursor, statement, parameters, context, executemany):
        if statement == "BEGIN IMMEDIATE":
            attempts.append(connection)
    event.listen(wrapper_engine, "before_cursor_execute", on_sql)
    monkeypatch.setattr(reconstruction_module, "reconstruct_account_threads_in_session",
        lambda session, scope: (_ for _ in ()).throw(
            __import__("sqlite3").OperationalError("database is locked")))
    try:
        with pytest.raises(ThreadReconstructionError) as raised:
            reconstruct_account_threads(wrapper_engine, SCOPE)
    finally:
        event.remove(wrapper_engine, "before_cursor_execute", on_sql)
    assert raised.value.code == "persistence_conflict"
    assert len(attempts) == 1


def test_wrapper_real_concurrent_writer_is_bounded(wrapper_engine, monkeypatch):
    monkeypatch.setattr(reconstruction_module, "_sleep", lambda seconds: None)
    with wrapper_engine.connect() as writer:
        writer.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            result = reconstruct_account_threads(wrapper_engine, SCOPE)
        finally:
            writer.rollback()
    assert result.status == "busy_retry_later"
    assert reconstruct_account_threads(wrapper_engine, SCOPE).status == "completed"


def test_wrapper_invalid_scope_never_connects(wrapper_engine, monkeypatch):
    monkeypatch.setattr(wrapper_engine, "connect", lambda: pytest.fail("connected"))
    with pytest.raises(ThreadReconstructionError) as raised:
        reconstruct_account_threads(wrapper_engine, " ")
    assert raised.value.code == "invalid_scope"


def test_wrapper_rejects_non_sqlite_engine(wrapper_engine, monkeypatch):
    monkeypatch.setattr(wrapper_engine.dialect, "name", "postgresql")
    with pytest.raises(ThreadReconstructionError) as raised:
        reconstruct_account_threads(wrapper_engine, SCOPE)
    assert raised.value.code == "persistence_conflict"
