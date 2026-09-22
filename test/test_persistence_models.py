from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.persistence.models import (
    CRMContextLink,
    CRMReference,
    Conversation,
    ConversationMembership,
    ExtractedFact,
    Inference,
    InferenceSupport,
    ManualNote,
    Proposal,
    ProposalSupport,
    SourceObservation,
    SourceRecord,
    WhatsAppImport,
)


def source(scope="manual", external_id=None):
    return SourceRecord(
        source_type="manual_note",
        source_system_scope=scope,
        stable_external_id=external_id,
        manual_entry=True,
        provenance="test",
    )


def test_source_identity_and_observation_history(db_session):
    first, second = source(external_id="same"), source(external_id="same")
    db_session.add(first)
    db_session.flush()
    db_session.add(
        SourceObservation(
            source_record_id=first.id,
            observed_state="active",
            outcome="ok",
            provenance="test",
        )
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_manual_source_and_conversation_constraints(db_session):
    one, two = source(), source()
    db_session.add_all([one, two])
    db_session.flush()
    db_session.add_all(
        [
            ManualNote(source_record_id=one.id, original_text="note"),
            WhatsAppImport(source_record_id=two.id, original_text="chat"),
        ]
    )
    conversation = Conversation(provenance="test")
    db_session.add(conversation)
    db_session.flush()
    db_session.add(
        ConversationMembership(
            conversation_id=conversation.id,
            source_record_id=one.id,
            evidence_type="message_id",
            evidence_reference="x",
        )
    )
    db_session.flush()
    other = Conversation(provenance="test")
    db_session.add(other)
    db_session.flush()
    db_session.add(
        ConversationMembership(
            conversation_id=other.id,
            source_record_id=one.id,
            evidence_type="message_id",
            evidence_reference="x",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_derived_types_are_physical_separate_models(db_session):
    db_session.add_all(
        [
            ExtractedFact(fact_type="fact", value_reference="x", provenance="test"),
            Inference(inference_type="inference", value_reference="x", provenance="test"),
            Proposal(proposal_type="proposal", value_reference="x", provenance="test"),
        ]
    )
    db_session.flush()


@pytest.mark.parametrize(
    ("state", "confirmed_at", "should_pass"),
    [
        ("confirmed", datetime.now(timezone.utc), True),
        ("confirmed", None, False),
        ("ambiguous", None, True),
        ("ambiguous", datetime.now(timezone.utc), False),
        ("proposed", None, True),
        ("proposed", datetime.now(timezone.utc), False),
        ("unknown", None, False),
    ],
)
def test_crm_context_confirmation_constraints(db_session, state, confirmed_at, should_pass):
    reference = CRMReference(
        entity_type="company",
        external_id=f"crm-{state}-{confirmed_at is not None}",
        provenance="test",
    )
    db_session.add(reference)
    db_session.flush()
    link = CRMContextLink(
        crm_reference_id=reference.id,
        assistant_record_type="source_record",
        assistant_record_id=1,
        relationship_purpose="context",
        confirmation_state=state,
        confirmed_at=confirmed_at,
        provenance="test",
    )
    db_session.add(link)
    if should_pass:
        db_session.flush()
    else:
        with pytest.raises(IntegrityError):
            db_session.flush()


def test_inference_support_rejects_unknown_type(db_session):
    inference = Inference(
        inference_type="signal",
        value_reference="x",
        provenance="test",
    )
    db_session.add(inference)
    db_session.flush()
    db_session.add(
        InferenceSupport(
            inference_id=inference.id,
            support_type="unknown",
            support_id=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_proposal_support_rejects_unknown_type(db_session):
    proposal = Proposal(
        proposal_type="reply",
        value_reference="x",
        provenance="test",
    )
    db_session.add(proposal)
    db_session.flush()
    db_session.add(
        ProposalSupport(
            proposal_id=proposal.id,
            support_type="unknown",
            support_id=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
