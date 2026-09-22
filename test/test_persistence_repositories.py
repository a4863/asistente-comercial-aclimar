from datetime import datetime, timezone

import pytest

from app.persistence.models import (
    AuditEvent,
    CRMContextLink,
    FactSourceEvidence,
    IdentityLink,
    IdentityLinkCorrection,
    InferenceSupport,
    ProposalSupport,
    SourceObservation,
    SourceRecord,
)
from app.persistence.repositories import (
    AuditRepository,
    DerivationRepository,
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
