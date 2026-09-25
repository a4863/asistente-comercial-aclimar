from datetime import datetime, timezone
from dataclasses import FrozenInstanceError
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.persistence.models import (
    Alert,
    AnalysisDerivationLink,
    AnalysisOperationalLink,
    AnalysisRun,
    AnalysisSourceEvidence,
    AnalysisSummary,
    ApprovalDecision,
    AuditEvent,
    Commitment,
    ConfigurationReference,
    Conversation,
    ConversationMembership,
    ExecutionResult,
    CRMContextLink,
    EmailAttachmentMetadata,
    EmailMessage,
    FactSourceEvidence,
    FollowUpPreferenceHistory,
    IdentityLink,
    IdentityLinkCorrection,
    IMAPMessageLocation,
    IdempotencyIdentity,
    InferenceSupport,
    OperationalEvidenceLink,
    ProposalSupport,
    SourceObservation,
    SourceRecord,
    SynchronizationCheckpoint,
    Task,
    ThreadEvidence,
    ThreadEvidenceDecision,
    ThreadLineageEdge,
    ThreadLineageOperation,
    ThreadMembershipChange,
)
from app.persistence.repositories import (
    ActionRepository,
    AnalysisRepository,
    AnalysisRepositoryError,
    AnalysisSourceSnapshot,
    AuditRepository,
    DerivationRepository,
    IMAPSyncRepository,
    OperationalRepository,
    ProvenanceRepository,
    SourceRepository,
    ThreadPersistenceRepository,
)
from app.domain.email_analysis import (
    AnalysisCandidates, AnalyticalSignalCandidate, CommitmentCandidate,
    EvidenceCandidate, FactCandidate, InferenceCandidate, NextStepCandidate,
    ProposalCandidate, QuestionCandidate, SupportRef, TaskCandidate,
    select_analysis_input,
)
from app.persistence.models import ExtractedFact, Inference, Proposal, Question, NextStep


def _source(db_session, external_id=None):
    source = SourceRecord(
        source_type="manual_note",
        source_system_scope="manual",
        stable_external_id=external_id,
        manual_entry=True,
        provenance="test",
    )
    db_session.add(source)
    db_session.flush()
    return source


def _imap_occurrence(db_session, *, folder="INBOX", uid=7, message_id="<one@example.test>"):
    repository = IMAPSyncRepository(db_session)
    when = datetime(2026, 9, 22, tzinfo=timezone.utc)
    source, email, location = repository.create_independent_occurrence(
        "imap:account", folder, 42, uid, when,
        {"normalized_message_id": message_id, "subject": "Synthetic", "body_size_bytes": 4, "normalized_body": "body", "content_truncated": False},
    )
    db_session.flush()
    return repository, source, email, location, when


def test_imap_exact_location_candidates_and_independent_duplicate(db_session):
    repo, source, email, location, when = _imap_occurrence(db_session)
    assert repo.find_location("imap:account", "INBOX", 42, 7) == (location, email, source)
    assert repo.find_location("imap:account", "INBOX", 42, 8) is None
    assert source.stable_external_id == "imap-occ:v1:" + repo.location_key("imap:account", "INBOX", 42, 7)
    assert source.source_type == "email_message"
    assert repo.find_message_id_candidates("imap:account", "<one@example.test>") == (email,)
    assert repo.find_message_id_candidates("imap:account", "") == ()
    second_source, second_email, _ = repo.create_independent_occurrence(
        "imap:account", "Sent", 42, 9, when,
        {"normalized_message_id": "<one@example.test>"},
    )
    db_session.flush()
    assert second_source.id != source.id
    assert repo.find_message_id_candidates("imap:account", "<one@example.test>") == (email, second_email)
    assert repo.find_message_id_candidates("other-account", "<one@example.test>") == ()
    _, missing_email, _ = repo.create_independent_occurrence("imap:account", "INBOX", 42, 10, when, {})
    db_session.flush()
    assert missing_email.normalized_message_id is None
    assert repo.find_message_id_candidates("imap:account", " ") == ()
    linked = repo.link_location(email, "imap:account", "Sent", 42, 11, when)
    db_session.flush()
    assert linked.email_message_id == email.id
    assert repo.link_location(email, "imap:account", "Sent", 42, 11, when) is linked
    assert repo.list_source_locations(source) == (location, linked)
    assert repo.list_active_locations("imap:account", "INBOX", 42) == (location, repo.find_location("imap:account", "INBOX", 42, 10)[0])
    with pytest.raises(ValueError):
        repo.link_location(second_email, "imap:account", "INBOX", 42, 7, when)
    with pytest.raises(ValueError):
        repo.link_location(email, "other-account", "INBOX", 42, 12, when)


def test_imap_idempotency_identity_and_conflict(db_session):
    repo, source, _, _, _ = _imap_occurrence(db_session)
    first = repo.reserve_occurrence_identity(source, "imap:account", "INBOX", 42, 7)
    db_session.flush()
    assert repo.reserve_occurrence_identity(source, "imap:account", "INBOX", 42, 7) is first
    assert first.operation_kind == "imap_occurrence"
    assert first.scope.startswith("imap-account:v1:")
    assert len(first.scope) == len("imap-account:v1:") + 64
    assert first.identity_key == "v1:" + repo.location_key("imap:account", "INBOX", 42, 7)
    assert db_session.query(IdempotencyIdentity).count() == 1
    other_source, _, _ = repo.create_independent_occurrence("imap:account", "Sent", 42, 8, datetime.now(timezone.utc), {})
    db_session.flush()
    with pytest.raises(ValueError):
        repo.reserve_occurrence_identity(other_source, "imap:account", "INBOX", 42, 7)
    with pytest.raises(ValueError):
        repo.reserve_occurrence_identity(source, "other-account", "INBOX", 42, 7)


def test_imap_email_updates_and_attachment_metadata_are_idempotent(db_session):
    repo, _, email, _, _ = _imap_occurrence(db_session)
    assert repo.update_email(email, {"subject": "Synthetic"}) is False
    assert repo.update_email(email, {"subject": "Updated", "normalized_body": "new body"}) is True
    with pytest.raises(ValueError):
        repo.update_email(email, {"source_record_id": 999})
    with pytest.raises(ValueError):
        repo.update_email(email, {"normalized_body": b"raw MIME"})
    original = [{"part_index": 0, "filename": "quote.pdf", "media_type": "application/pdf", "byte_size": 5, "provenance": "imap_sync"}]
    assert repo.replace_attachments(email, original) is True
    db_session.flush()
    part = db_session.scalar(select(EmailAttachmentMetadata).where(EmailAttachmentMetadata.email_message_id == email.id))
    assert repo.replace_attachments(email, original) is False
    assert db_session.scalar(select(EmailAttachmentMetadata).where(EmailAttachmentMetadata.email_message_id == email.id)) is part
    revised = [{**original[0], "filename": "revised.pdf"}]
    assert repo.replace_attachments(email, revised) is True
    assert part.filename == "revised.pdf"
    assert repo.replace_attachments(email, []) is True
    db_session.flush()
    assert db_session.scalar(select(EmailAttachmentMetadata).where(EmailAttachmentMetadata.email_message_id == email.id)) is None
    with pytest.raises(ValueError):
        repo.replace_attachments(email, [{**original[0], "payload": b"forbidden"}])
    with pytest.raises(ValueError):
        repo.replace_attachments(email, [{**original[0], "filename": b"raw"}])


def test_imap_observation_transition_audit_and_checkpoint(db_session):
    repo, source, _, location, when = _imap_occurrence(db_session)
    digest = "a" * 64
    first, created = repo.append_observation(source, location, "ingested", digest, when)
    assert created is True
    db_session.flush()
    repeat, created = repo.append_observation(source, location, "ingested", digest, when)
    assert (repeat, created) == (first, False)
    updated, created = repo.append_observation(source, location, "updated", "b" * 64, when)
    assert created is True
    db_session.flush()
    assert updated.source_version_marker != first.source_version_marker
    assert len(first.source_version_marker) < 255
    assert repo.set_location_state(location, "unavailable", when) is True
    unavailable, created = repo.append_observation(source, location, "unavailable", digest, when)
    assert created is True
    db_session.flush()
    assert unavailable.observed_state == "unavailable"
    assert repo.list_active_locations("imap:account", "INBOX", 42) == ()
    assert repo.set_location_state(location, "active", when) is True
    reactivated, created = repo.append_observation(source, location, "reactivated", digest, when)
    assert created is True
    assert reactivated.source_version_marker != first.source_version_marker
    assert location.last_observed_at == when
    event = repo.append_audit("imap_location_transitioned", "imap_message_location", location.id, "reactivated", when)
    assert event.outcome_reference == "reactivated"
    assert event.provenance == "imap_sync"
    with pytest.raises(ValueError):
        repo.append_audit("imap_source_updated", "source_record", source.id, "raw body", when)
    checkpoint = repo.upsert_folder_checkpoint("imap:account", "INBOX", 42, 7, when)
    db_session.flush()
    assert checkpoint.source_system_scope == repo.checkpoint_scope("imap:account", "INBOX")
    assert repo.read_folder_checkpoint("imap:account", "INBOX") == (checkpoint, 42, 7)
    assert repo.upsert_folder_checkpoint("imap:account", "INBOX", 42, 11, when) is checkpoint
    with pytest.raises(ValueError):
        repo.upsert_folder_checkpoint("imap:account", "INBOX", 42, 10, when)
    assert repo.upsert_folder_checkpoint("imap:account", "INBOX", 43, 0, when) is checkpoint
    assert repo.read_folder_checkpoint("imap:account", "INBOX") == (checkpoint, 43, 0)
    checkpoint.checkpoint_marker = "corrupt"
    with pytest.raises(ValueError):
        repo.read_folder_checkpoint("imap:account", "INBOX")


def test_imap_reactivation_after_unavailable_appends_new_observation(db_session):
    repo, source, email, location, when = _imap_occurrence(db_session)
    digest = "c" * 64

    first, first_created = repo.append_observation(source, location, "reactivated", digest, when)
    db_session.flush()
    assert first_created is True

    repo.set_location_state(location, "unavailable", when)
    unavailable, unavailable_created = repo.append_observation(source, location, "unavailable", digest, when)
    db_session.flush()
    assert unavailable_created is True

    repo.set_location_state(location, "active", when)
    second, second_created = repo.append_observation(source, location, "reactivated", digest, when)
    db_session.flush()

    assert second_created is True
    assert second.id != first.id
    assert second.id != unavailable.id
    assert second.observed_state == "active"
    assert second.outcome == "reactivated"


def test_imap_account_location_inventory_and_attachment_values_are_scoped(db_session):
    repo, source, email, location, when = _imap_occurrence(db_session)
    linked = repo.link_location(email, "imap:account", "Sent", 42, 9, when)
    repo.replace_attachments(email, [{
        "part_index": 2, "filename": "synthetic.pdf", "media_type": "application/pdf",
        "byte_size": 17, "content_id": None, "disposition": "attachment", "provenance": "imap_sync",
    }])
    other_source, other_email, other_location = repo.create_independent_occurrence(
        "imap:other", "INBOX", 1, 1, when, {"normalized_message_id": "<other@test>"},
    )
    db_session.flush()
    assert {row[0].id for row in repo.list_account_locations("imap:account")} == {location.id, linked.id}
    assert all(row[1].id == email.id and row[2].id == source.id for row in repo.list_account_locations("imap:account"))
    assert {row[0].id for row in repo.list_account_locations("imap:other")} == {other_location.id}
    assert repo.list_account_locations("imap:missing") == ()
    assert repo.email_attachment_values(email) == ({
        "part_index": 2, "filename": "synthetic.pdf", "media_type": "application/pdf",
        "byte_size": 17, "content_id": None, "disposition": "attachment", "provenance": "imap_sync",
    },)
    assert repo.email_attachment_values(other_email) == ()
    with pytest.raises(ValueError):
        repo.list_account_locations("")


def test_imap_repository_never_commits_and_caller_rollback_removes_rows(db_session):
    repo, source, email, location, when = _imap_occurrence(db_session)
    repo.reserve_occurrence_identity(source, "imap:account", "INBOX", 42, 7)
    repo.append_observation(source, location, "ingested", "b" * 64, when)
    repo.upsert_folder_checkpoint("imap:account", "INBOX", 42, 7, when)
    db_session.flush()
    db_session.rollback()
    assert db_session.get(SourceRecord, source.id) is None
    assert db_session.get(EmailMessage, email.id) is None
    assert db_session.get(IMAPMessageLocation, location.id) is None
    assert db_session.query(SynchronizationCheckpoint).count() == 0
    assert db_session.query(SourceObservation).count() == 0


def test_imap_location_unique_conflict_recovers_by_reread(db_session):
    repo, _, email, location, when = _imap_occurrence(db_session)
    db_session.commit()
    duplicate = IMAPMessageLocation(
        email_message_id=email.id,
        account_scope="imap:account",
        folder_name="INBOX",
        uidvalidity=42,
        uid=7,
        location_state="active",
        last_observed_at=when,
        provenance="imap_sync",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
    recovered = IMAPSyncRepository(db_session).find_location("imap:account", "INBOX", 42, 7)
    assert recovered is not None
    assert recovered[0].id == location.id
    assert db_session.query(IMAPMessageLocation).count() == 1


def test_source_repository_checkpoint_and_idempotency(db_session):
    repository = SourceRepository(db_session)

    created = repository.upsert_checkpoint(
        "imap",
        checkpoint_marker="1",
        last_success_at=None,
        last_outcome="ok",
    )
    db_session.flush()
    assert repository.get_checkpoint("imap") is created

    updated = repository.upsert_checkpoint(
        "imap",
        checkpoint_marker="2",
        last_success_at=datetime.now(timezone.utc),
        last_outcome="ok",
    )
    assert updated is created
    assert updated.checkpoint_marker == "2"

    first = repository.reserve_idempotency(
        operation_kind="source",
        scope="manual",
        identity_key="one",
    )
    db_session.flush()
    second = repository.reserve_idempotency(
        operation_kind="source",
        scope="manual",
        identity_key="one",
    )
    assert second is first
    assert repository.get_idempotency("source", "manual", "one") is first


def test_retention_transition_preserves_observation_history(db_session):
    repository = SourceRepository(db_session)
    source = _source(db_session, "retention-1")
    at = datetime.now(timezone.utc)

    observation = repository.mark_retention(source, "redacted", at)
    db_session.flush()

    assert source.retention_state == "redacted"
    assert source.deleted_or_redacted_at == at
    assert isinstance(observation, SourceObservation)
    assert observation.source_record_id == source.id
    assert observation.observed_state == "redacted"
    assert observation.outcome == "retention_transition"


def test_provenance_conversation_notes_activity_and_crm_reference(db_session):
    db_session.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    provenance = ProvenanceRepository(db_session)
    _, source, _, _, _ = _imap_occurrence(db_session)

    conversation = provenance.create_conversation("test", "imap:account")
    db_session.flush()
    membership = provenance.add_conversation_membership(
        conversation.id,
        source.id,
        "singleton",
        f"source:{source.id}",
        account_scope="imap:account",
        reconstruction_key="a" * 64,
    )

    note_source = _source(db_session, "note-1")
    chat_source = _source(db_session, "chat-1")
    note = provenance.create_manual_note(note_source.id, "note")
    chat = provenance.create_whatsapp_import(chat_source.id, "chat")

    activity = provenance.create_activity(
        "email",
        datetime.now(timezone.utc),
        "ref",
        "test",
    )
    db_session.flush()
    link = provenance.add_activity_source_link(activity.id, source.id, "evidence")

    crm = provenance.get_or_create_crm_reference(
        "company",
        "crm-1",
        display_reference="Company",
        provenance="test",
    )
    db_session.flush()
    same = provenance.get_or_create_crm_reference("company", "crm-1")

    assert membership.source_record_id == source.id
    assert note.original_text == "note"
    assert chat.original_text == "chat"
    assert link.activity_id == activity.id
    assert same is crm


def _thread_repo(db_session):
    db_session.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    return ThreadPersistenceRepository(db_session)


def _thread_source(db_session, scope="imap:one", message_id="<one@example.test>"):
    source = SourceRecord(source_type="email_message", source_system_scope=scope, provenance="test")
    db_session.add(source)
    db_session.flush()
    db_session.add(EmailMessage(source_record_id=source.id, normalized_message_id=message_id,
                                references_header="<root@example.test>", provenance="test"))
    db_session.flush()
    return source


def _snapshot_membership(db_session, source, conversation):
    row = ConversationMembership(source_record_id=source.id,
        conversation_id=conversation.id, evidence_type="singleton",
        evidence_reference=f"source:{source.id}")
    db_session.add(row)
    db_session.flush()
    return row


def test_account_thread_snapshot_empty_scope_and_no_commit(db_session, monkeypatch):
    repo = _thread_repo(db_session)
    monkeypatch.setattr(db_session, "commit", lambda: pytest.fail("snapshot committed"))
    assert repo.load_account_thread_snapshot("imap:one").sources == ()
    for scope in ("", " ", "x" * 101, None):
        with pytest.raises(ValueError, match="scope"):
            repo.load_account_thread_snapshot(scope)
    source = _thread_source(db_session)
    email = db_session.scalar(select(EmailMessage).where(EmailMessage.source_record_id == source.id))
    email.in_reply_to = "<parent@example.test>"
    email.subject = "Synthetic subject"
    email.normalized_body = "private body"
    db_session.flush()
    snapshot = repo.load_account_thread_snapshot("imap:one")
    assert snapshot.account_scope == "imap:one"
    assert len(snapshot.sources) == 1
    row = snapshot.sources[0]
    assert (row.source_record_id, row.eligible, row.normalized_message_id,
            row.in_reply_to, row.references_header, row.subject) == (
            source.id, True, "<one@example.test>", "<parent@example.test>",
            "<root@example.test>", "Synthetic subject")
    assert row.current_conversation_id is None and row.full_current_member_ids == ()
    assert not hasattr(row, "normalized_body")
    with pytest.raises(FrozenInstanceError):
        row.subject = "changed"


@pytest.mark.parametrize("locations", ["none", "unavailable", "multiple"])
def test_account_thread_snapshot_ignores_imap_location_cardinality(db_session, locations):
    repo = _thread_repo(db_session)
    source = _thread_source(db_session)
    email = db_session.scalar(select(EmailMessage).where(EmailMessage.source_record_id == source.id))
    if locations != "none":
        for uid in range(1, 3 if locations == "multiple" else 2):
            db_session.add(IMAPMessageLocation(email_message_id=email.id,
                account_scope="imap:one", folder_name="INBOX", uidvalidity=1, uid=uid,
                location_state="unavailable", last_observed_at=datetime.now(timezone.utc),
                provenance="test"))
        db_session.flush()
    assert [row.source_record_id for row in repo.load_account_thread_snapshot("imap:one").sources] == [source.id]


@pytest.mark.parametrize("state", ["deleted", "redacted"])
def test_account_thread_snapshot_excludes_valid_terminal_source(db_session, state):
    repo = _thread_repo(db_session)
    source = _thread_source(db_session)
    source.retention_state = state
    source.deleted_or_redacted_at = datetime.now(timezone.utc)
    db_session.flush()
    row = repo.load_account_thread_snapshot("imap:one").sources[0]
    assert row.source_record_id == source.id and row.eligible is False
    assert row.deleted_or_redacted_at is not None
    assert row.normalized_message_id is None


@pytest.mark.parametrize("state,timestamp", [
    ("active", True), ("deleted", False), ("redacted", False), ("unknown", False),
])
def test_account_thread_snapshot_rejects_invalid_retention(db_session, state, timestamp):
    repo = _thread_repo(db_session)
    source = _thread_source(db_session)
    source.retention_state = state
    source.deleted_or_redacted_at = datetime.now(timezone.utc) if timestamp else None
    db_session.flush()
    with pytest.raises(ValueError, match="retention state"):
        repo.load_account_thread_snapshot("imap:one")


def test_account_thread_snapshot_rejects_missing_email(db_session):
    repo = _thread_repo(db_session)
    db_session.add(SourceRecord(source_type="email_message", source_system_scope="imap:one",
                                provenance="test"))
    db_session.flush()
    with pytest.raises(ValueError, match="missing EmailMessage"):
        repo.load_account_thread_snapshot("imap:one")


@pytest.mark.parametrize("kind", ["resolved", "legacy", "superseded", "foreign"])
def test_account_thread_snapshot_surfaces_touched_conversation_state(db_session, kind):
    repo = _thread_repo(db_session)
    source = _thread_source(db_session)
    if kind == "legacy":
        conversation = Conversation(account_scope=None, legacy_status="legacy_unresolved",
            stable_key=str(uuid4()), provenance="test")
        db_session.add(conversation)
        db_session.flush()
    else:
        conversation = repo.create_resolved_conversation(
            "imap:other" if kind == "foreign" else "imap:one", "test")
    if kind == "superseded":
        conversation.superseded_at = datetime.now(timezone.utc)
    _snapshot_membership(db_session, source, conversation)
    row = repo.load_account_thread_snapshot("imap:one").sources[0]
    assert row.current_conversation_id == conversation.id
    assert row.conversation_account_scope == conversation.account_scope
    assert row.conversation_legacy_status == conversation.legacy_status
    assert (row.conversation_superseded_at is not None) == (kind == "superseded")
    assert row.full_current_member_ids == (source.id,)


def test_account_thread_snapshot_full_members_and_deterministic_order(db_session):
    repo = _thread_repo(db_session)
    first = _thread_source(db_session)
    excluded = _thread_source(db_session, message_id="<excluded@example.test>")
    other = _source(db_session)
    last = _thread_source(db_session, message_id="<last@example.test>")
    foreign = _thread_source(db_session, scope="imap:other")
    excluded.retention_state = "redacted"
    excluded.deleted_or_redacted_at = datetime.now(timezone.utc)
    conversation = repo.create_resolved_conversation("imap:one", "test")
    for source in (last, other, excluded, first):
        _snapshot_membership(db_session, source, conversation)
    rows = repo.load_account_thread_snapshot("imap:one").sources
    assert tuple(row.source_record_id for row in rows) == (first.id, excluded.id, last.id)
    assert tuple(row.eligible for row in rows) == (True, False, True)
    assert rows[1].current_conversation_id is None
    assert rows[0].full_current_member_ids == tuple(sorted((first.id, excluded.id, other.id, last.id)))
    assert rows[2].full_current_member_ids == rows[0].full_current_member_ids
    assert tuple(member.source_record_id for member in rows[0].full_current_members) == rows[0].full_current_member_ids
    member_by_id = {member.source_record_id: member for member in rows[0].full_current_members}
    assert member_by_id[other.id].source_type == "manual_note"
    assert member_by_id[other.id].account_scope == "manual"
    assert member_by_id[excluded.id].source_type == "email_message"
    assert member_by_id[excluded.id].account_scope == "imap:one"
    assert foreign.id not in [row.source_record_id for row in rows]


def _thread_evidence(repo, source, token="one@example.test"):
    email = repo.session.scalar(select(EmailMessage).where(EmailMessage.source_record_id == source.id))
    return repo.append_evidence(
        account_scope=source.source_system_scope, source_record_id=source.id,
        header_kind="message_id", ordinal=0, parse_status="valid", canonical_token=token,
        token_digest=sha256(token.encode()).hexdigest(), normalization_version=1,
        source_revision=repo._digest("3d1/source-revision/v1", source.id,
            email.normalized_message_id, email.in_reply_to, email.references_header),
    )


def test_thread_repository_scope_email_and_old_boundary(db_session):
    repo = _thread_repo(db_session)
    email = _thread_source(db_session)
    foreign = _thread_source(db_session, scope="imap:other")
    manual = _source(db_session)
    conversation = repo.create_resolved_conversation("imap:one", "test")
    assert conversation.stable_key and conversation.legacy_status == "resolved"
    assert len(repo.conversations_for_account("imap:one")) == 1
    with pytest.raises(ValueError, match="same account"):
        repo.current_membership("imap:one", foreign.id)
    with pytest.raises(ValueError, match="logical email"):
        repo.current_membership("imap:one", manual.id)
    with pytest.raises(ValueError, match="same account"):
        repo.assign_current_membership(account_scope="imap:other", source_record_id=email.id,
            new_conversation_id=conversation.id, reason="initial_assignment", reconstruction_key="a" * 64,
            evidence_type="singleton", evidence_reference=f"source:{email.id}")
    with pytest.raises(TypeError):
        ProvenanceRepository(db_session).create_conversation("old-unscoped")


def test_thread_evidence_decision_replay_and_cycle(db_session):
    repo = _thread_repo(db_session)
    first, second = _thread_source(db_session), _thread_source(db_session, message_id="<two@example.test>")
    first_ev = _thread_evidence(repo, first)
    assert repo.append_evidence(account_scope="imap:one", source_record_id=first.id,
        header_kind="message_id", ordinal=0, parse_status="valid", canonical_token="one@example.test",
        token_digest=sha256(b"one@example.test").hexdigest(), normalization_version=1,
        source_revision=first_ev.source_revision) is first_ev
    second_ev = _thread_evidence(repo, second, "two@example.test")
    assert len(repo.evidence_for_source("imap:one", first.id)) == 1
    with pytest.raises(ValueError, match="digest mismatch"):
        repo.append_evidence(account_scope="imap:one", source_record_id=first.id,
            header_kind="references", ordinal=0, parse_status="valid", canonical_token="bad@example.test",
            token_digest="a" * 64, normalization_version=1, source_revision=first_ev.source_revision)
    with pytest.raises(ValueError, match="replay key mismatch"):
        repo.append_evidence(account_scope="imap:one", source_record_id=first.id,
            header_kind="message_id", ordinal=0, parse_status="valid", canonical_token="one@example.test",
            token_digest=first_ev.token_digest, normalization_version=1,
            source_revision=first_ev.source_revision, replay_key="b" * 64)
    decision = repo.append_decision(evidence_id=first_ev.id, reconstruction_key="a" * 64,
                                    outcome="accepted_direct_parent", target_source_record_id=second.id)
    assert repo.append_decision(evidence_id=first_ev.id, reconstruction_key="a" * 64,
                                outcome="accepted_direct_parent", target_source_record_id=second.id) is decision
    with pytest.raises(ValueError, match="already has a decision"):
        repo.append_decision(evidence_id=first_ev.id, reconstruction_key="a" * 64, outcome="conflict")
    later = repo.append_decision(evidence_id=first_ev.id, reconstruction_key="b" * 64, outcome="conflict")
    assert later.id != decision.id and len(repo.decisions_for_reconstruction("b" * 64)) == 1
    with pytest.raises(ValueError, match="parent cycle"):
        repo.append_decision(evidence_id=second_ev.id, reconstruction_key="a" * 64,
                             outcome="accepted_ancestor", target_source_record_id=first.id)
    with pytest.raises(ValueError, match="same account"):
        outside = _thread_source(db_session, scope="imap:other")
        repo.append_decision(evidence_id=second_ev.id, reconstruction_key="c" * 64,
                             outcome="accepted_ancestor", target_source_record_id=outside.id)
    assert db_session.query(ThreadEvidenceDecision).count() == 2


def test_thread_membership_projection_history_replay_and_rollback(db_session):
    repo = _thread_repo(db_session)
    source = _thread_source(db_session)
    first = repo.create_resolved_conversation("imap:one", "test")
    second = repo.create_resolved_conversation("imap:one", "test")
    unrelated = repo.create_resolved_conversation("imap:one", "test")
    values = dict(account_scope="imap:one", source_record_id=source.id,
                  new_conversation_id=first.id, reason="initial_assignment",
                  reconstruction_key="a" * 64, evidence_type="singleton",
                  evidence_reference=f"source:{source.id}")
    membership = repo.assign_current_membership(**values)
    assert repo.assign_current_membership(**values) is membership
    assert len(repo.membership_history("imap:one", source.id)) == 1
    with pytest.raises(ValueError, match="stale"):
        repo.assign_current_membership(**(values | {"new_conversation_id": second.id,
            "reason": "correction", "reconstruction_key": "b" * 64,
            "expected_old_conversation_id": unrelated.id}))
    with db_session.begin_nested() as savepoint:
        repo.assign_current_membership(**(values | {"new_conversation_id": second.id,
            "reason": "correction", "reconstruction_key": "b" * 64,
            "expected_old_conversation_id": first.id}))
        assert membership.conversation_id == second.id
        savepoint.rollback()
    db_session.expire_all()
    assert repo.current_membership("imap:one", source.id).conversation_id == first.id
    assert len(repo.membership_history("imap:one", source.id)) == 1
    assert db_session.query(ThreadMembershipChange).count() == 1
    repo.assign_current_membership(**(values | {"new_conversation_id": second.id,
        "reason": "correction", "reconstruction_key": "b" * 64,
        "expected_old_conversation_id": first.id}))
    assert repo.assign_current_membership(**values).conversation_id == second.id
    assert len(repo.membership_history("imap:one", source.id)) == 2


def test_thread_lineage_merge_split_repartition_and_guards(db_session):
    repo = _thread_repo(db_session)
    rows = [repo.create_resolved_conversation("imap:one", "test") for _ in range(10)]
    merge = repo.record_lineage_operation(account_scope="imap:one", kind="merge",
        predecessor_ids=[rows[0].id, rows[1].id], successor_ids=[rows[2].id],
        reconstruction_key="a" * 64)
    assert len(repo.lineage_from(rows[0].id)) == 1
    assert len(repo.lineage_to(rows[2].id)) == 2
    assert repo.record_lineage_operation(account_scope="imap:one", kind="merge",
        predecessor_ids=[rows[1].id, rows[0].id], successor_ids=[rows[2].id],
        reconstruction_key="a" * 64) is merge
    with pytest.raises(ValueError, match="already superseded"):
        repo.record_lineage_operation(account_scope="imap:one", kind="merge",
            predecessor_ids=[rows[0].id, rows[3].id], successor_ids=[rows[4].id],
            reconstruction_key="b" * 64)
    split = repo.record_lineage_operation(account_scope="imap:one", kind="split",
        predecessor_ids=[rows[3].id], successor_ids=[rows[4].id, rows[5].id],
        reconstruction_key="c" * 64)
    assert len(repo.lineage_from(rows[3].id)) == 2
    repartition = repo.record_lineage_operation(account_scope="imap:one", kind="repartition",
        predecessor_ids=[rows[6].id, rows[7].id], successor_ids=[rows[8].id, rows[9].id],
        reconstruction_key="d" * 64)
    assert len(repo.session.scalars(select(ThreadLineageEdge).where(ThreadLineageEdge.operation_id == repartition.id)).all()) == 4
    assert db_session.query(ThreadLineageOperation).count() == 3
    with pytest.raises(ValueError, match="invalid lineage"):
        repo.record_lineage_operation(account_scope="imap:one", kind="merge",
            predecessor_ids=[rows[4].id, rows[5].id], successor_ids=[rows[4].id],
            reconstruction_key="e" * 64)
    assert split.id != merge.id


def test_thread_lineage_correction_shape_replay_and_scope(db_session):
    repo = _thread_repo(db_session)
    rows = [repo.create_resolved_conversation("imap:one", "test") for _ in range(5)]
    foreign = repo.create_resolved_conversation("imap:other", "test")
    base = dict(account_scope="imap:one", kind="correction", reconstruction_key="a" * 64)
    for predecessors, successors in (
        ([rows[0].id], [rows[1].id, rows[2].id]),
        ([rows[0].id, rows[1].id], [rows[2].id]),
        ([rows[0].id, rows[1].id], [rows[2].id, rows[3].id]),
        ([rows[0].id], [rows[0].id]),
        ([rows[0].id, rows[0].id], [rows[2].id]),
    ):
        with pytest.raises(ValueError, match="invalid lineage operation shape"):
            repo.record_lineage_operation(**base, predecessor_ids=predecessors,
                                          successor_ids=successors)
    with pytest.raises(ValueError, match="same account"):
        repo.record_lineage_operation(**base, predecessor_ids=[rows[0].id],
                                      successor_ids=[foreign.id])
    operation = repo.record_lineage_operation(**base, predecessor_ids=[rows[0].id],
                                              successor_ids=[rows[1].id])
    assert operation.kind == "correction"
    assert rows[0].superseded_at is not None
    assert [(edge.predecessor_conversation_id, edge.successor_conversation_id)
            for edge in repo.lineage_from(rows[0].id)] == [(rows[0].id, rows[1].id)]
    assert repo.record_lineage_operation(**base, predecessor_ids=[rows[0].id],
                                         successor_ids=[rows[1].id]) is operation
    operation.provenance = "tampered"
    with pytest.raises(ValueError, match="payload conflict"):
        repo.record_lineage_operation(**base, predecessor_ids=[rows[0].id],
                                      successor_ids=[rows[1].id])
    operation.provenance = "thread_reconstruction"
    with pytest.raises(ValueError, match="replay key mismatch"):
        repo.record_lineage_operation(**base, predecessor_ids=[rows[0].id],
                                      successor_ids=[rows[1].id], replay_key="f" * 64)
    with pytest.raises(ValueError, match="already superseded"):
        repo.record_lineage_operation(**(base | {"reconstruction_key": "b" * 64}),
                                      predecessor_ids=[rows[0].id], successor_ids=[rows[2].id])
    rows[3].superseded_at = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="already superseded"):
        repo.record_lineage_operation(**base, predecessor_ids=[rows[3].id],
                                      successor_ids=[rows[4].id])
    rows[2].superseded_at = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="already superseded"):
        repo.record_lineage_operation(**base, predecessor_ids=[rows[4].id],
                                      successor_ids=[rows[2].id])


def test_thread_lineage_correction_cycle_guard(db_session):
    repo = _thread_repo(db_session)
    first, second = [repo.create_resolved_conversation("imap:one", "test") for _ in range(2)]
    prior = ThreadLineageOperation(account_scope="imap:one", kind="correction",
        reconstruction_key="a" * 64, replay_key="b" * 64, provenance="test")
    db_session.add(prior)
    db_session.flush()
    db_session.add(ThreadLineageEdge(operation_id=prior.id,
        predecessor_conversation_id=second.id, successor_conversation_id=first.id))
    db_session.flush()
    with pytest.raises(ValueError, match="lineage cycle"):
        repo.record_lineage_operation(account_scope="imap:one", kind="correction",
            predecessor_ids=[first.id], successor_ids=[second.id], reconstruction_key="c" * 64)
    assert first.superseded_at is None and second.superseded_at is None


def test_thread_lineage_cycle_is_rejected_without_mutation(db_session):
    repo = _thread_repo(db_session)
    first, second, third = [repo.create_resolved_conversation("imap:one", "test") for _ in range(3)]
    # An existing historical edge can be imported or otherwise observed before supersession projection.
    prior = ThreadLineageOperation(account_scope="imap:one", kind="merge",
        reconstruction_key="a" * 64, replay_key="b" * 64, provenance="test")
    db_session.add(prior)
    db_session.flush()
    db_session.add(ThreadLineageEdge(operation_id=prior.id,
        predecessor_conversation_id=first.id, successor_conversation_id=second.id))
    db_session.flush()
    with pytest.raises(ValueError, match="lineage cycle"):
        repo.record_lineage_operation(account_scope="imap:one", kind="merge",
            predecessor_ids=[second.id, third.id], successor_ids=[first.id],
            reconstruction_key="c" * 64)
    assert first.superseded_at is None and second.superseded_at is None
    assert db_session.query(ThreadLineageOperation).count() == 1


def test_crm_context_repository_guards(db_session):
    provenance = ProvenanceRepository(db_session)
    crm = provenance.get_or_create_crm_reference("company", "crm-ctx")
    db_session.flush()

    valid = provenance.create_crm_context_link(
        crm_reference_id=crm.id,
        assistant_record_type="source_record",
        assistant_record_id=1,
        relationship_purpose="company_context",
        confirmation_state="confirmed",
        confirmed_at=datetime.now(timezone.utc),
        provenance="test",
    )
    db_session.flush()
    assert isinstance(valid, CRMContextLink)

    with pytest.raises(ValueError):
        provenance.create_crm_context_link(
            crm.id,
            "source_record",
            1,
            "company_context",
            "confirmed",
            None,
            "test",
        )

    with pytest.raises(ValueError):
        provenance.create_crm_context_link(
            crm.id,
            "source_record",
            1,
            "company_context",
            "ambiguous",
            datetime.now(timezone.utc),
            "test",
        )

    with pytest.raises(ValueError):
        provenance.create_crm_context_link(
            crm.id,
            "not-a-2a-record",
            1,
            "company_context",
            "proposed",
            None,
            "test",
        )


def test_crm_reference_signature_rejects_master_data_fields(db_session):
    provenance = ProvenanceRepository(db_session)
    with pytest.raises(TypeError):
        provenance.get_or_create_crm_reference(
            "company",
            "crm-master",
            display_reference="Company",
            provenance="test",
            legal_name="Should not be copied",
        )


def test_identity_correction_preserves_and_supersedes_prior(db_session):
    provenance = ProvenanceRepository(db_session)
    crm1 = provenance.get_or_create_crm_reference("contact", "c-1")
    crm2 = provenance.get_or_create_crm_reference("contact", "c-2")
    db_session.flush()

    prior = provenance.create_identity_link(
        "email",
        "old@example.com",
        crm1.id,
        provenance="test",
    )
    replacement = provenance.create_identity_link(
        "email",
        "new@example.com",
        crm2.id,
        provenance="test",
    )
    db_session.flush()

    correction = provenance.append_identity_correction(
        prior.id,
        replacement.id,
        provenance="test",
    )
    db_session.flush()

    assert db_session.get(IdentityLink, prior.id) is prior
    assert prior.superseded_at is not None
    assert db_session.get(IdentityLink, replacement.id) is replacement
    assert db_session.get(IdentityLinkCorrection, correction.id) is correction

    with pytest.raises(ValueError):
        provenance.append_identity_correction(prior.id, prior.id)


def test_derivation_fact_inference_and_proposal_supports(db_session):
    source = _source(db_session, "derivation-1")
    repository = DerivationRepository(db_session)

    fact = repository.append_fact("question", "Q1", "test")
    db_session.flush()
    evidence = repository.add_fact_evidence(fact.id, source.id, "body:1")
    assert isinstance(evidence, FactSourceEvidence)

    inference = repository.append_inference("intent", "reply_needed", "test")
    db_session.flush()
    support = repository.add_inference_support(inference.id, "fact", fact.id)
    assert isinstance(support, InferenceSupport)

    with pytest.raises(ValueError):
        repository.add_inference_support(inference.id, "proposal", 1)

    proposal = repository.append_proposal("reply", "draft-1", "test")
    db_session.flush()
    proposal_support = repository.add_proposal_support(
        proposal.id,
        "inference",
        inference.id,
    )
    assert isinstance(proposal_support, ProposalSupport)

    with pytest.raises(ValueError):
        repository.add_proposal_support(proposal.id, "unknown", 1)


def test_audit_repository_rejects_unsafe_or_unknown_fields(db_session):
    source = _source(db_session, "audit-1")
    audit = AuditRepository(db_session)

    event = audit.append(
        event_type="source_created",
        affected_record_type="source_record",
        affected_record_id=source.id,
        actor_or_source="test",
        provenance="test",
    )
    db_session.flush()
    assert isinstance(event, AuditEvent)
    assert audit.list_for("source_record", source.id) == [event]
    assert not hasattr(audit, "delete")
    assert not hasattr(audit, "update")

    with pytest.raises(ValueError):
        audit.append(
            event_type="unsafe",
            affected_record_type="source_record",
            affected_record_id=source.id,
            actor_or_source="test",
            provenance="test",
            raw_content="secret",
        )

    with pytest.raises(ValueError):
        audit.append(
            event_type="unknown",
            affected_record_type="source_record",
            affected_record_id=source.id,
            actor_or_source="test",
            provenance="test",
            arbitrary="x",
        )


def test_operational_task_lifecycle_and_audit(db_session):
    repository = OperationalRepository(db_session)

    pending = repository.create_task("pending", "test")
    completed = repository.create_task("completed", "test")
    cancelled = repository.create_task("cancelled", "test")
    pending_cancelled = repository.create_task("pending-cancelled", "test")
    db_session.flush()

    assert repository.transition_task(pending.id, "pending").state == "pending"
    assert repository.transition_task(completed.id, "pending").state == "pending"
    with pytest.raises(ValueError):
        repository.transition_task(completed.id, "completed")
    assert repository.transition_task(completed.id, "completed", "confirmed-by-user").completion_reference == "confirmed-by-user"
    assert repository.transition_task(cancelled.id, "cancelled").state == "cancelled"
    assert repository.transition_task(pending_cancelled.id, "pending").state == "pending"
    assert repository.transition_task(pending_cancelled.id, "cancelled").state == "cancelled"
    with pytest.raises(ValueError):
        repository.transition_task(cancelled.id, "pending")
    db_session.flush()

    assert isinstance(db_session.get(Task, completed.id), Task)
    assert any(event.event_type == "task_transitioned" for event in AuditRepository(db_session).list_for("task", completed.id))


def test_commitment_question_and_next_step_lifecycles(db_session):
    repository = OperationalRepository(db_session)
    past = datetime(2025, 1, 1, tzinfo=timezone.utc)
    future = datetime(2030, 1, 1, tzinfo=timezone.utc)
    overdue = repository.create_commitment("past", "test", due_at=past)
    future_commitment = repository.create_commitment("future", "test", due_at=future)
    fulfilled = repository.create_commitment("fulfilled", "test")
    question = repository.create_question("What is due?", "test")
    next_step = repository.create_next_step("call", "test")
    db_session.flush()

    for commitment in (overdue, future_commitment, fulfilled):
        assert repository.transition_commitment(commitment.id, "confirmed").state == "confirmed"
    with pytest.raises(ValueError):
        repository.transition_commitment(fulfilled.id, "fulfilled")
    assert repository.transition_commitment(fulfilled.id, "fulfilled", "user-confirmed").state == "fulfilled"
    evaluated = repository.evaluate_overdue(datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert evaluated == [overdue]
    assert overdue.state == "overdue"
    assert future_commitment.state == "confirmed"
    assert isinstance(db_session.get(Commitment, overdue.id), Commitment)

    assert repository.transition_question(question.id, "open").state == "open"
    with pytest.raises(ValueError):
        repository.transition_question(question.id, "answered")
    assert repository.transition_question(question.id, "answered", "answer-evidence").answer_reference == "answer-evidence"
    with pytest.raises(ValueError):
        repository.transition_question(question.id, "dismissed")

    assert repository.transition_next_step(next_step.id, "planned").state == "planned"
    with pytest.raises(ValueError):
        repository.transition_next_step(next_step.id, "completed")
    assert repository.transition_next_step(next_step.id, "completed", "completed-by-user").completion_reference == "completed-by-user"


def test_alerts_and_follow_up_preferences(db_session):
    repository = OperationalRepository(db_session)
    active = repository.get_or_create_alert("follow_up", "company", 1, "company:1", "test")
    db_session.flush()
    assert repository.get_or_create_alert("follow_up", "company", 1, "company:1", "test") is active
    assert repository.resolve_alert(active.id).state == "resolved"
    recurrence = repository.get_or_create_alert("follow_up", "company", 1, "company:1", "test")
    assert recurrence is not active
    db_session.flush()
    with pytest.raises(ValueError):
        repository.dismiss_alert(recurrence.id, "")
    assert repository.dismiss_alert(recurrence.id, "alejandro").state == "dismissed"
    assert isinstance(db_session.get(Alert, recurrence.id), Alert)

    global_preference = repository.set_follow_up_preference("global", None, "sent_offer", inactivity_days=5, provenance="test")
    company_preference = repository.set_follow_up_preference("company", "crm-company", "sent_offer", inactivity_days=8, provenance="test")
    opportunity_preference = repository.set_follow_up_preference("opportunity", "crm-opportunity", "sent_offer", inactivity_days=3, provenance="test")
    repository.set_follow_up_preference("opportunity", "crm-opportunity", "sent_offer", inactivity_days=4, provenance="test")
    db_session.flush()
    history = list(db_session.scalars(select(FollowUpPreferenceHistory).where(FollowUpPreferenceHistory.follow_up_preference_id == opportunity_preference.id)))
    assert len(history) == 2
    exact = repository.resolve_follow_up_preference("sent_offer", crm_scopes=[("company", "crm-company"), ("opportunity", "crm-opportunity")])
    assert exact["preference"] is opportunity_preference
    assert exact["inactivity_days"] == 4
    crm_over_manual = repository.resolve_follow_up_preference("sent_offer", crm_scopes=[("company", "crm-company")], manual_scope=("opportunity", "manual-opportunity"))
    assert crm_over_manual["preference"] is company_preference
    future_date = datetime(2030, 2, 1, tzinfo=timezone.utc)
    repository.set_follow_up_preference("contact", "crm-contact", "homologation_docs", inactivity_days=7, explicit_future_date=future_date, provenance="test")
    date_resolution = repository.resolve_follow_up_preference("homologation_docs", crm_scopes=[("contact", "crm-contact")])
    assert date_resolution["explicit_future_date"].replace(tzinfo=timezone.utc) == future_date
    assert date_resolution["inactivity_days"] is None
    assert repository.resolve_follow_up_preference("new_or_qualified_opportunity")["inactivity_days"] == 7
    assert repository.resolve_follow_up_preference("negotiation_review")["inactivity_days"] == 5
    assert global_preference.id is not None


def test_action_approval_execution_idempotency_and_audit(db_session):
    repository = ActionRepository(db_session)
    proposal = repository.create_action_proposal("move_message", "message", "m-1", "external_action", "mailbox", "m-1:move", "test")
    db_session.flush()
    assert repository.create_action_proposal("move_message", "message", "m-1", "external_action", "mailbox", "m-1:move", "test") is proposal
    with pytest.raises(ValueError):
        repository.append_execution_result(proposal.id, "executed", "revalidated", "test")
    approval = repository.decide_action(proposal.id, "approved", "alejandro", "test")
    db_session.flush()
    assert isinstance(approval, ApprovalDecision)
    with pytest.raises(ValueError):
        repository.decide_action(proposal.id, "approved", "alejandro", "test")
    with pytest.raises(ValueError):
        repository.append_execution_result(proposal.id, "executed", "", "test")
    error = repository.append_execution_result(proposal.id, "error", "still-current", "test", failure_code="temporary")
    assert isinstance(error, ExecutionResult)
    assert proposal.state == "error"
    executed = repository.append_execution_result(proposal.id, "executed", "still-current", "test", external_result_reference="moved")
    assert executed.outcome == "executed"
    assert proposal.state == "executed"
    with pytest.raises(ValueError):
        repository.append_execution_result(proposal.id, "error", "still-current", "test")
    rejected = repository.create_action_proposal("create_draft", "message", "m-2", "external_action", "mailbox", "m-2:draft", "test")
    db_session.flush()
    assert repository.decide_action(rejected.id, "rejected", "alejandro", "test").decision == "rejected"
    assert any(event.event_type == "action_proposal_execution_recorded" for event in AuditRepository(db_session).list_for("action_proposal", proposal.id))


def test_operational_evidence_validation(db_session):
    repository = OperationalRepository(db_session)
    task = repository.create_task("evidence", "test")
    db_session.flush()
    confirmation = repository.add_operational_evidence("task", task.id, "user_confirmation", evidence_reference="confirmed-by-user", provenance="test")
    assert isinstance(confirmation, OperationalEvidenceLink)
    evidence = repository.add_operational_evidence("task", task.id, "fact", evidence_id=1, provenance="test")
    assert evidence.evidence_id == 1
    with pytest.raises(ValueError):
        repository.add_operational_evidence("fact", task.id, "fact", evidence_id=1)
    with pytest.raises(ValueError):
        repository.add_operational_evidence("task", task.id, "user_confirmation", evidence_id=1, evidence_reference="bad")
    with pytest.raises(ValueError):
        repository.add_operational_evidence("task", task.id, "source")


def _analysis_target(db_session, *, scope="imap:one"):
    source = SourceRecord(source_type="email_message", source_system_scope=scope,
                          stable_external_id=str(uuid4()), provenance="test")
    conversation = Conversation(account_scope=scope, stable_key=str(uuid4()),
                                legacy_status="resolved", provenance="test")
    db_session.add_all((source, conversation))
    db_session.flush()
    db_session.add_all((
        EmailMessage(source_record_id=source.id, normalized_body="body", provenance="test"),
        ConversationMembership(conversation_id=conversation.id, source_record_id=source.id,
                               evidence_type="test", evidence_reference="test"),
    ))
    db_session.flush()
    return source, conversation


def _reserve_analysis(repo, source, conversation, *, digest="a" * 64,
                      mode="automatic", contract_version=1, policy_version=1,
                      scope="imap:one"):
    return repo.reserve_run(scope, source.id, conversation.id, digest,
                            contract_version, policy_version, mode)


def _cutover_marker(db_session):
    return db_session.scalar(select(ConfigurationReference).where(
        ConfigurationReference.scope == "phase6_lock_cutover"))


def test_analysis_cutover_clean_creation_and_idempotent_reentry(db_session):
    repo = AnalysisRepository(db_session)
    assert repo.establish_cutover_or_recover() == ("created", 0)
    marker = _cutover_marker(db_session)
    assert (marker.reference_kind, marker.reference_value) == ("operational_ownership", "v1")
    db_session.commit()
    assert repo.establish_cutover_or_recover() == ("recovered", 0)
    assert _cutover_marker(db_session).id == marker.id
    assert db_session.scalar(select(ConfigurationReference).where(
        ConfigurationReference.scope == "phase6_lock_cutover")).id == marker.id


def test_analysis_cutover_refuses_legacy_reserved_without_mutation(db_session):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    run = _reserve_analysis(repo, source, conversation).run
    run_id = run.id
    db_session.commit()

    with pytest.raises(AnalysisRepositoryError, match="cutover_requires_operator"):
        repo.establish_cutover_or_recover()
    db_session.rollback()
    assert _cutover_marker(db_session) is None
    assert (db_session.get(AnalysisRun, run_id).status,
            db_session.get(AnalysisRun, run_id).failure_code) == ("reserved", None)


def test_analysis_cutover_recovers_only_reserved_and_replays_without_change(db_session):
    repo = AnalysisRepository(db_session)
    assert repo.establish_cutover_or_recover() == ("created", 0)
    db_session.commit()
    source, conversation = _analysis_target(db_session)
    runs = [_reserve_analysis(repo, source, conversation, digest=letter * 64).run
            for letter in "abcd"]
    repo.finalize_run_status(runs[1].id)
    repo.mark_retryable(runs[2].id, status="stale_retryable", failure_code="input_changed")
    repo.mark_retryable(runs[3].id, status="failed_retryable", failure_code="provider_failure")
    ids = [run.id for run in runs]
    db_session.commit()
    db_session.expire_all()
    before = {run_id: (db_session.get(AnalysisRun, run_id).status,
                       db_session.get(AnalysisRun, run_id).failure_code,
                       db_session.get(AnalysisRun, run_id).updated_at)
              for run_id in ids}
    assert repo.establish_cutover_or_recover() == ("recovered", 1)
    db_session.commit()
    db_session.expire_all()
    recovered = db_session.get(AnalysisRun, ids[0])
    assert (recovered.status, recovered.failure_code) == ("failed_retryable", "interrupted")
    assert {run_id: (db_session.get(AnalysisRun, run_id).status,
                     db_session.get(AnalysisRun, run_id).failure_code,
                     db_session.get(AnalysisRun, run_id).updated_at)
            for run_id in ids[1:]} == {run_id: before[run_id] for run_id in ids[1:]}
    timestamp = recovered.updated_at
    assert repo.establish_cutover_or_recover() == ("recovered", 0)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(AnalysisRun, ids[0]).updated_at == timestamp


@pytest.mark.parametrize("kind,value", [("wrong", "v1"), ("operational_ownership", "wrong")])
def test_analysis_cutover_rejects_malformed_marker(db_session, kind, value):
    db_session.add(ConfigurationReference(scope="phase6_lock_cutover",
                                          reference_kind=kind, reference_value=value))
    db_session.commit()
    with pytest.raises(AnalysisRepositoryError, match="invalid_cutover_marker"):
        AnalysisRepository(db_session).establish_cutover_or_recover()


def test_analysis_cutover_marker_creation_is_caller_transactional(db_session):
    repo = AnalysisRepository(db_session)
    assert repo.establish_cutover_or_recover() == ("created", 0)
    db_session.rollback()
    assert _cutover_marker(db_session) is None


def test_analysis_cutover_recovery_is_caller_transactional(db_session):
    repo = AnalysisRepository(db_session)
    assert repo.establish_cutover_or_recover() == ("created", 0)
    db_session.commit()
    source, conversation = _analysis_target(db_session)
    run_id = _reserve_analysis(repo, source, conversation).run.id
    db_session.commit()
    assert repo.establish_cutover_or_recover() == ("recovered", 1)
    db_session.rollback()
    db_session.expire_all()
    assert (db_session.get(AnalysisRun, run_id).status,
            db_session.get(AnalysisRun, run_id).failure_code) == ("reserved", None)


def test_analysis_reservation_in_progress_and_changed_input_versions(db_session):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    first = _reserve_analysis(repo, source, conversation)
    assert first.outcome == "reserved_new" and first.run.run_version == 1
    assert first.run.status == "reserved"
    assert _reserve_analysis(repo, source, conversation).outcome == "in_progress"
    second = _reserve_analysis(repo, source, conversation, digest="b" * 64)
    assert second.outcome == "reserved_new" and second.run.run_version == 2
    assert [run.run_version for run in repo.run_history("imap:one", source.id)] == [1, 2]
    assert repo.run_provenance(first.run.id) == "not_completed"


def test_analysis_manual_automatic_replay_and_repeated_force(db_session):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    first = _reserve_analysis(repo, source, conversation).run
    repo.finalize_run_status(first.id)
    for mode in ("manual", "automatic"):
        replay = _reserve_analysis(repo, source, conversation, mode=mode)
        assert replay.outcome == "completed_replay" and replay.run.id == first.id
    second = _reserve_analysis(repo, source, conversation, mode="force").run
    assert second.run_version == 2
    assert _reserve_analysis(repo, source, conversation, mode="force").outcome == "in_progress"
    repo.finalize_run_status(second.id)
    third = _reserve_analysis(repo, source, conversation, mode="force").run
    assert third.run_version == 3
    repo.finalize_run_status(third.id)
    assert second.supersedes_run_id == first.id
    assert third.supersedes_run_id == second.id
    assert repo.run_provenance(first.id) == "superseded_analysis_needs_review"
    assert repo.run_provenance(third.id) == "current_analysis"
    assert repo.latest_completed_run("imap:one", source.id).id == third.id
    assert repo.replay_lookup("imap:one", source.id, "a" * 64, 1, 1).id == third.id
    assert len(repo.run_history("imap:one", source.id)) == 3


def test_analysis_replay_only_latest_completed_with_matching_versions(db_session):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    first = _reserve_analysis(repo, source, conversation).run
    repo.finalize_run_status(first.id)
    second = _reserve_analysis(repo, source, conversation, digest="b" * 64).run
    repo.finalize_run_status(second.id)
    assert repo.replay_lookup("imap:one", source.id, "a" * 64, 1, 1) is None
    assert repo.replay_lookup("imap:one", source.id, "b" * 64, 2, 1) is None
    assert _reserve_analysis(repo, source, conversation, digest="a" * 64).run.run_version == 3


@pytest.mark.parametrize("status,code", [
    ("stale_retryable", "input_changed"),
    ("failed_retryable", "provider_failure"),
    ("failed_retryable", "invalid_output"),
    ("failed_retryable", "persistence_failure"),
    ("failed_retryable", "interrupted"),
])
def test_analysis_retryable_history_gets_new_version(db_session, status, code):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    old = _reserve_analysis(repo, source, conversation).run
    updated = repo.mark_retryable(old.id, status=status, failure_code=code)
    assert updated.status == status and updated.failure_code == code
    retry = _reserve_analysis(repo, source, conversation)
    assert retry.outcome == "reserved_new" and retry.run.run_version == 2
    assert repo.run_history("imap:one", source.id)[0].status == status
    with pytest.raises(AnalysisRepositoryError) as error:
        repo.mark_retryable(old.id, status=status, failure_code=code)
    assert error.value.code == "run_state_conflict"


@pytest.mark.parametrize("status,code", [
    ("failed_retryable", "input_changed"),
    ("stale_retryable", "provider_failure"),
    ("failed_retryable", "raw exception text"),
    ("completed", "provider_failure"),
])
def test_analysis_invalid_retryable_transition_is_bounded(db_session, status, code):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    run = _reserve_analysis(repo, source, conversation).run
    with pytest.raises(AnalysisRepositoryError) as error:
        repo.mark_retryable(run.id, status=status, failure_code=code)
    assert error.value.code == "invalid_retryable_transition"
    assert run.status == "reserved" and run.failure_code is None


def test_analysis_completed_run_cannot_retry_or_recomplete(db_session):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    run = _reserve_analysis(repo, source, conversation).run
    repo.finalize_run_status(run.id)
    with pytest.raises(AnalysisRepositoryError):
        repo.mark_retryable(run.id, status="failed_retryable", failure_code="provider_failure")
    with pytest.raises(AnalysisRepositoryError):
        repo.finalize_run_status(run.id)
    assert run.status == "completed" and run.supersedes_run_id is None


@pytest.mark.parametrize("change", [
    {"mode": "unknown"}, {"digest": "A" * 64}, {"digest": "bad"},
    {"contract_version": 0}, {"policy_version": -1},
])
def test_analysis_invalid_reservation_input_creates_no_run(db_session, change):
    source, conversation = _analysis_target(db_session)
    with pytest.raises(AnalysisRepositoryError):
        _reserve_analysis(AnalysisRepository(db_session), source, conversation, **change)
    assert db_session.scalars(select(AnalysisRun)).all() == []


def test_analysis_rejects_cross_account_wrong_membership_and_inactive_target(db_session):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    wrong = Conversation(account_scope="imap:one", stable_key=str(uuid4()),
                         legacy_status="resolved", provenance="test")
    db_session.add(wrong)
    db_session.flush()
    for scope, target_conversation in (("imap:two", conversation), ("imap:one", wrong)):
        with pytest.raises(AnalysisRepositoryError):
            _reserve_analysis(repo, source, target_conversation, scope=scope)
    source.retention_state = "redacted"
    db_session.flush()
    with pytest.raises(AnalysisRepositoryError):
        _reserve_analysis(repo, source, conversation)


@pytest.mark.parametrize("legacy,superseded", [(True, False), (False, True)])
def test_analysis_rejects_unresolved_or_superseded_conversation(db_session, legacy, superseded):
    source, conversation = _analysis_target(db_session)
    conversation.legacy_status = "legacy_unresolved" if legacy else "resolved"
    conversation.account_scope = None if legacy else "imap:one"
    conversation.superseded_at = datetime.now(timezone.utc) if superseded else None
    db_session.flush()
    with pytest.raises(AnalysisRepositoryError):
        _reserve_analysis(AnalysisRepository(db_session), source, conversation)


def test_analysis_supersession_stays_scoped_and_unique(db_session):
    source, conversation = _analysis_target(db_session)
    other_source, other_conversation = _analysis_target(db_session, scope="imap:two")
    repo = AnalysisRepository(db_session)
    first = _reserve_analysis(repo, source, conversation).run
    other = _reserve_analysis(repo, other_source, other_conversation, scope="imap:two").run
    repo.finalize_run_status(first.id)
    repo.finalize_run_status(other.id)
    successor = _reserve_analysis(repo, source, conversation, digest="b" * 64).run
    repo.finalize_run_status(successor.id)
    assert successor.supersedes_run_id == first.id
    assert other.supersedes_run_id is None
    assert successor.supersedes_run_id != successor.id
    assert repo.latest_completed_run("imap:two", other_source.id).id == other.id
    assert repo.run_history("imap:two", source.id) == ()
    third = _reserve_analysis(repo, source, conversation, digest="c" * 64).run
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            third.supersedes_run_id = first.id
            db_session.flush()


def test_analysis_caller_owns_transaction_and_rollback(db_session, monkeypatch):
    source, conversation = _analysis_target(db_session)
    db_session.commit()  # Persist only the synthetic fixture rows.
    repo = AnalysisRepository(db_session)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("repository owns no commit or rollback")

    with monkeypatch.context() as patcher:
        patcher.setattr(db_session, "commit", forbidden)
        patcher.setattr(db_session, "rollback", forbidden)
        assert _reserve_analysis(repo, source, conversation).run.id is not None
    db_session.rollback()
    assert db_session.scalars(select(AnalysisRun)).all() == []


def test_analysis_reservation_integrity_error_is_bounded(db_session, monkeypatch):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    original_flush = db_session.flush

    def conflict(objects=None):
        if objects and any(isinstance(row, AnalysisRun) for row in objects):
            raise IntegrityError("INSERT", {}, Exception("private SQL detail"))
        return original_flush(objects)

    with monkeypatch.context() as patcher:
        patcher.setattr(db_session, "flush", conflict)
        with pytest.raises(AnalysisRepositoryError) as error:
            _reserve_analysis(repo, source, conversation)
    assert error.value.code == "reservation_conflict"
    assert "private SQL detail" not in str(error.value)


def test_manual_selector_is_bounded_scoped_ordered_and_metadata_only(db_session):
    repo = AnalysisRepository(db_session)
    for index in range(24):
        source, _ = _analysis_target(db_session)
        email = db_session.scalar(select(EmailMessage).where(
            EmailMessage.source_record_id == source.id))
        email.sender_address = f"sender{index}@example.test"
        email.subject = f"Subject {index}"
        email.normalized_body = f"PRIVATE BODY {index}"
        email.sent_at = datetime(2026, 1, index + 1, tzinfo=timezone.utc)
    hidden, _ = _analysis_target(db_session, scope="imap:two")
    redacted, _ = _analysis_target(db_session)
    redacted.retention_state = "redacted"
    no_body, _ = _analysis_target(db_session)
    db_session.scalar(select(EmailMessage).where(
        EmailMessage.source_record_id == no_body.id)).normalized_body = None
    db_session.flush()
    refs = repo.list_eligible_email_refs("imap:one")
    assert len(refs) == 20
    assert [ref.subject for ref in refs] == [f"Subject {index}" for index in range(23, 3, -1)]
    assert all(ref.account_scope == "imap:one" for ref in refs)
    assert all(not hasattr(ref, "normalized_body") for ref in refs)
    assert hidden.id not in {ref.source_record_id for ref in refs}
    assert redacted.id not in {ref.source_record_id for ref in refs}
    assert no_body.id not in {ref.source_record_id for ref in refs}
    for invalid in (0, 21, True):
        with pytest.raises(AnalysisRepositoryError):
            repo.list_eligible_email_refs("imap:one", limit=invalid)


def test_manual_intent_reservation_requires_explicit_retry_without_new_identity(db_session):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)

    def reserve(intent, digest="a" * 64):
        return repo.reserve_manual_run("imap:one", source.id, conversation.id,
                                       digest, 1, 1, intent=intent)

    assert reserve("retry").outcome == "retry_not_available"
    assert repo.latest_run_for_target("imap:one", source.id) is None
    first = reserve("initial")
    assert first.outcome == "reserved_new" and first.run.request_mode == "manual"
    assert reserve("initial").outcome == "in_progress"
    assert reserve("retry").outcome == "in_progress"
    repo.mark_retryable(first.run.id, status="failed_retryable", failure_code="provider_failure")
    assert reserve("initial").outcome == "retry_required"
    assert len(repo.run_history("imap:one", source.id)) == 1
    second = reserve("retry")
    assert second.outcome == "reserved_new" and second.run.run_version == 2
    repo.finalize_run_status(second.run.id)
    assert reserve("initial").outcome == "completed_replay"
    assert reserve("retry").outcome == "completed_replay"
    assert reserve("retry", digest="b" * 64).outcome == "retry_not_available"
    assert reserve("initial", digest="b" * 64).outcome == "reserved_new"
    with pytest.raises(AnalysisRepositoryError):
        reserve("force")


def test_manual_retry_reservation_rollback_is_caller_owned(db_session):
    source, conversation = _analysis_target(db_session)
    db_session.commit()
    repo = AnalysisRepository(db_session)
    first = repo.reserve_manual_run("imap:one", source.id, conversation.id,
                                    "a" * 64, 1, 1, intent="initial")
    db_session.commit()
    repo.mark_retryable(first.run.id, status="stale_retryable", failure_code="input_changed")
    db_session.commit()
    assert repo.reserve_manual_run("imap:one", source.id, conversation.id,
                                   "a" * 64, 1, 1, intent="retry").outcome == "reserved_new"
    db_session.rollback()
    assert [run.run_version for run in repo.run_history("imap:one", source.id)] == [1]


def test_analysis_run_repository_does_not_create_derivations(db_session):
    source, conversation = _analysis_target(db_session)
    repo = AnalysisRepository(db_session)
    run = _reserve_analysis(repo, source, conversation).run
    repo.finalize_run_status(run.id)
    for model in (AnalysisSourceEvidence, AnalysisDerivationLink,
                  AnalysisSummary, AnalysisOperationalLink):
        assert db_session.scalars(select(model)).all() == []


def _completion_fixture(db_session, body="Can you send a quote?\nI promise a reply.\n"):
    source, conversation = _analysis_target(db_session)
    email = db_session.scalar(select(EmailMessage).where(EmailMessage.source_record_id == source.id))
    email.normalized_body = body
    db_session.flush()
    analysis_input = select_analysis_input(db_session, "imap:one", source.id)
    snapshot = AnalysisSourceSnapshot(analysis_input, ((source.id, body),))
    repo = AnalysisRepository(db_session)
    run = _reserve_analysis(repo, source, conversation, digest=analysis_input.input_digest).run
    return repo, run, snapshot


def _span(source_id, body, text):
    start = body.index(text)
    return EvidenceCandidate(source_id, start, start + len(text),
                             sha256(text.encode("utf-8")).hexdigest(), text)


def test_analysis_completion_persists_typed_graph_and_operational_links(db_session):
    body = "Can you send a quote?\nI promise a reply.\n"
    repo, run, snapshot = _completion_fixture(db_session, body)
    question = _span(run.target_source_record_id, body, "Can you send a quote?")
    promise = _span(run.target_source_record_id, body, "I promise a reply.")
    candidates = AnalysisCandidates(
        summary="A quote was requested and a reply promised.",
        facts=(FactCandidate("request", "quote", question),),
        inferences=(InferenceCandidate("intent", "follow_up", (SupportRef("fact", 0),)),),
        proposals=(ProposalCandidate("reply", "prepare_quote", (SupportRef("inference", 0),)),),
        questions=(QuestionCandidate(question.exact_text, question, "new"),),
        commitments=(CommitmentCandidate("Reply", "self", "none", None, None,
                                         promise, True),),
        tasks=(TaskCandidate("Prepare quote", None, (SupportRef("proposal", 0),)),),
        next_steps=(NextStepCandidate("Send proposal", None, (SupportRef("proposal", 0),)),),
        response_needed=AnalyticalSignalCandidate("yes", (SupportRef("fact", 0),)),
    )
    completed = repo.complete_run(run.id, run.input_digest, candidates, snapshot)
    assert completed.status == "completed"
    assert len(db_session.scalars(select(AnalysisSourceEvidence)).all()) == 2
    assert len(db_session.scalars(select(ExtractedFact)).all()) == 3
    assert len(db_session.scalars(select(Inference)).all()) == 2
    assert len(db_session.scalars(select(Proposal)).all()) == 3
    assert len(db_session.scalars(select(AnalysisDerivationLink)).all()) == 8
    assert len(db_session.scalars(select(AnalysisOperationalLink)).all()) == 4
    assert len(db_session.scalars(select(OperationalEvidenceLink)).all()) == 6
    assert db_session.scalar(select(Question)).state == "detected"
    assert db_session.scalar(select(Commitment)).state == "confirmed"
    assert db_session.scalar(select(Task)).state == "proposed"
    assert db_session.scalar(select(NextStep)).state == "proposed"
    assert db_session.scalar(select(AnalysisSummary)).summary_digest == sha256(
        candidates.summary.encode("utf-8")).hexdigest()
    with pytest.raises(AnalysisRepositoryError):
        repo.complete_run(run.id, run.input_digest, candidates, snapshot)


@pytest.mark.parametrize("change", ["summary_copy", "wrong_digest", "wrong_source", "stale_body"])
def test_analysis_completion_rejects_invalid_preconditions_without_rows(db_session, change):
    repo, run, snapshot = _completion_fixture(db_session)
    body = snapshot.original_bodies[0][1]
    evidence = _span(run.target_source_record_id, body, "Can you send a quote?")
    candidates = AnalysisCandidates(facts=(FactCandidate("request", "quote", evidence),))
    digest = run.input_digest
    if change == "summary_copy":
        candidates = AnalysisCandidates(summary=body)
    elif change == "wrong_digest":
        digest = "b" * 64
    elif change == "wrong_source":
        wrong = EvidenceCandidate(9999, evidence.start_offset, evidence.end_offset,
                                  evidence.span_digest, evidence.exact_text)
        candidates = AnalysisCandidates(facts=(FactCandidate("request", "quote", wrong),))
    else:
        email = db_session.scalar(select(EmailMessage).where(
            EmailMessage.source_record_id == run.target_source_record_id))
        email.normalized_body = "changed"
        db_session.flush()
    with pytest.raises(AnalysisRepositoryError):
        repo.complete_run(run.id, digest, candidates, snapshot)
    assert run.status == "reserved"
    assert db_session.scalars(select(AnalysisSourceEvidence)).all() == []
    assert db_session.scalars(select(AnalysisDerivationLink)).all() == []


@pytest.mark.parametrize("prefix,state,expected", [("> ", "quoted", 0),
                                                    (" From: Alice\n", "ambiguous", 0),
                                                    ("", "new", 1)])
def test_analysis_question_quote_policy(db_session, prefix, state, expected):
    body = prefix + "Can you send a quote?\n"
    repo, run, snapshot = _completion_fixture(db_session, body)
    evidence = _span(run.target_source_record_id, body, "Can you send a quote?")
    candidates = AnalysisCandidates(questions=(QuestionCandidate(
        evidence.exact_text, evidence, state),))
    repo.complete_run(run.id, run.input_digest, candidates, snapshot)
    assert len(db_session.scalars(select(Question)).all()) == expected
    assert len(db_session.scalars(select(ExtractedFact)).all()) == 1


def test_analysis_completion_reuses_span_and_supersedes_append_only(db_session):
    repo, first, snapshot = _completion_fixture(db_session)
    body = snapshot.original_bodies[0][1]
    evidence = _span(first.target_source_record_id, body, "Can you send a quote?")
    candidates = AnalysisCandidates(
        facts=(FactCandidate("request", "quote", evidence),
               FactCandidate("request_repeat", "quote", evidence)))
    repo.complete_run(first.id, first.input_digest, candidates, snapshot)
    assert len(db_session.scalars(select(AnalysisSourceEvidence)).all()) == 1
    assert len(db_session.scalars(select(FactSourceEvidence)).all()) == 2
    second = repo.reserve_run("imap:one", first.target_source_record_id,
                              first.conversation_id, first.input_digest, 1, 1, "force").run
    repo.complete_run(second.id, second.input_digest, candidates, snapshot)
    assert second.supersedes_run_id == first.id
    assert repo.run_provenance(first.id) == "superseded_analysis_needs_review"
    assert len(db_session.scalars(select(ExtractedFact)).all()) == 4


def test_analysis_completion_caller_owns_rollback_and_no_audit(db_session, monkeypatch):
    repo, run, snapshot = _completion_fixture(db_session)
    db_session.commit()
    body = snapshot.original_bodies[0][1]
    evidence = _span(run.target_source_record_id, body, "Can you send a quote?")
    candidates = AnalysisCandidates(facts=(FactCandidate("request", "quote", evidence),))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("repository must not commit or rollback")

    with monkeypatch.context() as patcher:
        patcher.setattr(db_session, "commit", forbidden)
        patcher.setattr(db_session, "rollback", forbidden)
        repo.complete_run(run.id, run.input_digest, candidates, snapshot)
    assert db_session.scalars(select(AuditEvent)).all() == []
    assert db_session.scalars(select(Alert)).all() == []
    assert db_session.scalars(select(ApprovalDecision)).all() == []
    assert db_session.scalars(select(ExecutionResult)).all() == []
    db_session.rollback()
    assert db_session.get(AnalysisRun, run.id).status == "reserved"
    assert db_session.scalars(select(AnalysisSourceEvidence)).all() == []


def test_analysis_completion_rejects_malformed_typed_support(db_session):
    repo, run, snapshot = _completion_fixture(db_session)
    body = snapshot.original_bodies[0][1]
    evidence = _span(run.target_source_record_id, body, "Can you send a quote?")
    candidate = InferenceCandidate("intent", "follow_up", (SupportRef("fact", 0),))
    aggregate = AnalysisCandidates(
        facts=(FactCandidate("request", "quote", evidence),),
        inferences=(candidate,))
    object.__setattr__(candidate, "support_refs", (SupportRef("proposal", 0),))
    with pytest.raises(AnalysisRepositoryError) as error:
        repo.complete_run(run.id, run.input_digest, aggregate, snapshot)
    assert error.value.code == "invalid_output"
    assert db_session.scalars(select(AnalysisSourceEvidence)).all() == []


def test_analysis_completion_rejects_non_target_question_operational_creation(db_session):
    repo, run, snapshot = _completion_fixture(db_session)
    prior = SourceRecord(source_type="email_message", source_system_scope="imap:one",
                         stable_external_id=str(uuid4()), provenance="test")
    db_session.add(prior)
    db_session.flush()
    db_session.add_all((
        EmailMessage(source_record_id=prior.id, normalized_body="Any update?", provenance="test"),
        ConversationMembership(conversation_id=run.conversation_id,
                               source_record_id=prior.id, evidence_type="test",
                               evidence_reference="test"),
    ))
    db_session.flush()
    # A newly selected prior invalidates the old input, before candidate persistence.
    evidence = _span(prior.id, "Any update?", "Any update?")
    candidate = AnalysisCandidates(questions=(QuestionCandidate("Any update?", evidence, "new"),))
    with pytest.raises(AnalysisRepositoryError):
        repo.complete_run(run.id, run.input_digest, candidate, snapshot)
    assert db_session.scalars(select(Question)).all() == []


def _completion_with_prior(db_session, prior_body):
    prior = SourceRecord(source_type="email_message", source_system_scope="imap:one",
                         stable_external_id=str(uuid4()), provenance="test")
    db_session.add(prior)
    db_session.flush()
    source, conversation = _analysis_target(db_session)
    db_session.add_all((
        EmailMessage(source_record_id=prior.id, normalized_body=prior_body,
                     subject="Prior context", provenance="test"),
        ConversationMembership(conversation_id=conversation.id,
                               source_record_id=prior.id, evidence_type="test",
                               evidence_reference="test"),
    ))
    db_session.flush()
    analysis_input = select_analysis_input(db_session, "imap:one", source.id)
    snapshot = AnalysisSourceSnapshot(analysis_input, ((source.id, "body"),
                                                       (prior.id, prior_body)))
    repo = AnalysisRepository(db_session)
    run = _reserve_analysis(repo, source, conversation,
                            digest=analysis_input.input_digest).run
    return repo, run, snapshot, prior


def test_analysis_completion_accepts_metadata_only_prior_without_derived_rows(db_session):
    repo, run, snapshot, prior = _completion_with_prior(db_session, None)
    selected = snapshot.analysis_input.selected_messages
    assert [item.source_record_id for item in selected] == [run.target_source_record_id,
                                                            prior.id]
    assert selected[1].role == "prior" and selected[1].body_excerpt == ""
    assert selected[1].original_body_digest == sha256(b"").hexdigest()
    assert snapshot.original_bodies[1] == (prior.id, None)
    assert snapshot.analysis_input.input_digest == run.input_digest
    completed = repo.complete_run(run.id, run.input_digest, AnalysisCandidates(), snapshot)
    assert completed.status == "completed"
    for model in (AnalysisSourceEvidence, AnalysisDerivationLink,
                  AnalysisOperationalLink, ExtractedFact, Inference, Proposal,
                  Question, Commitment, Task, NextStep):
        assert db_session.scalars(select(model)).all() == []


def test_analysis_completion_rejects_evidence_on_metadata_only_prior(db_session):
    repo, run, snapshot, prior = _completion_with_prior(db_session, None)
    evidence = EvidenceCandidate(prior.id, 0, 1, sha256(b"x").hexdigest(), "x")
    candidates = AnalysisCandidates(facts=(FactCandidate("claim", "x", evidence),))
    with pytest.raises(AnalysisRepositoryError) as error:
        repo.complete_run(run.id, run.input_digest, candidates, snapshot)
    assert error.value.code == "invalid_evidence"
    assert run.status == "reserved"
    assert db_session.scalars(select(AnalysisSourceEvidence)).all() == []


@pytest.mark.parametrize("before,after", [(None, "new body"),
                                           ("old body", None),
                                           (None, ""),
                                           ("", None)])
def test_analysis_completion_detects_prior_body_state_change(db_session, before, after):
    repo, run, snapshot, prior = _completion_with_prior(db_session, before)
    email = db_session.scalar(select(EmailMessage).where(
        EmailMessage.source_record_id == prior.id))
    email.normalized_body = after
    db_session.flush()
    with pytest.raises(AnalysisRepositoryError) as error:
        repo.complete_run(run.id, run.input_digest, AnalysisCandidates(), snapshot)
    assert error.value.code == "input_changed"
    assert run.status == "reserved"
    assert db_session.scalars(select(AnalysisSourceEvidence)).all() == []


def test_analysis_completion_keeps_text_prior_evidence_validation(db_session):
    repo, run, snapshot, prior = _completion_with_prior(db_session, "Prior fact")
    evidence = _span(prior.id, "Prior fact", "Prior fact")
    candidates = AnalysisCandidates(facts=(FactCandidate("prior_fact", "known", evidence),))
    repo.complete_run(run.id, run.input_digest, candidates, snapshot)
    row = db_session.scalar(select(AnalysisSourceEvidence))
    assert row.source_record_id == prior.id
    assert row.body_digest == sha256(b"Prior fact").hexdigest()
    assert db_session.scalar(select(FactSourceEvidence)).source_record_id == prior.id
