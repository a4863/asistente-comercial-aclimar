from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.persistence.models import (
    Alert,
    ApprovalDecision,
    AuditEvent,
    Commitment,
    ExecutionResult,
    CRMContextLink,
    FactSourceEvidence,
    FollowUpPreferenceHistory,
    IdentityLink,
    IdentityLinkCorrection,
    InferenceSupport,
    OperationalEvidenceLink,
    ProposalSupport,
    SourceObservation,
    SourceRecord,
    Task,
)
from app.persistence.repositories import (
    ActionRepository,
    AuditRepository,
    DerivationRepository,
    OperationalRepository,
    ProvenanceRepository,
    SourceRepository,
)


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
    provenance = ProvenanceRepository(db_session)
    source = _source(db_session, "prov-1")

    conversation = provenance.create_conversation("test")
    db_session.flush()
    membership = provenance.add_conversation_membership(
        conversation.id,
        source.id,
        "message_id",
        "m-1",
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
    assert date_resolution["inactivity_days"] == 7
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
