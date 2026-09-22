from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.persistence.models import (
    Alert,
    CRMContextLink,
    CRMReference,
    Commitment,
    Conversation,
    ConversationMembership,
    ExtractedFact,
    Inference,
    InferenceSupport,
    IdentityLink,
    IdentityLinkCorrection,
    ManualNote,
    NextStep,
    Proposal,
    ProposalSupport,
    Question,
    SourceObservation,
    Task,
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


def _crm_reference(db_session, external_id):
    reference = CRMReference(
        entity_type="contact",
        external_id=external_id,
        provenance="test",
    )
    db_session.add(reference)
    db_session.flush()
    return reference


def test_identity_link_allows_only_one_active_confirmed_mapping(db_session):
    first_crm = _crm_reference(db_session, "contact-1")
    second_crm = _crm_reference(db_session, "contact-2")
    first = IdentityLink(
        identity_type="email",
        identity_value="person@example.com",
        crm_reference_id=first_crm.id,
        status="confirmed",
        provenance="test",
    )
    db_session.add(first)
    db_session.flush()

    duplicate = IdentityLink(
        identity_type="email",
        identity_value="person@example.com",
        crm_reference_id=second_crm.id,
        status="confirmed",
        provenance="test",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_identity_link_superseded_mapping_allows_replacement(db_session):
    first_crm = _crm_reference(db_session, "contact-3")
    second_crm = _crm_reference(db_session, "contact-4")
    first = IdentityLink(
        identity_type="email",
        identity_value="replace@example.com",
        crm_reference_id=first_crm.id,
        status="confirmed",
        superseded_at=datetime.now(timezone.utc),
        provenance="test",
    )
    second = IdentityLink(
        identity_type="email",
        identity_value="replace@example.com",
        crm_reference_id=second_crm.id,
        status="confirmed",
        provenance="test",
    )
    db_session.add_all([first, second])
    db_session.flush()


def test_identity_link_correction_rejects_self_reference(db_session):
    crm = _crm_reference(db_session, "contact-5")
    link = IdentityLink(
        identity_type="email",
        identity_value="self@example.com",
        crm_reference_id=crm.id,
        status="confirmed",
        provenance="test",
    )
    db_session.add(link)
    db_session.flush()
    db_session.add(
        IdentityLinkCorrection(
            prior_identity_link_id=link.id,
            replacement_identity_link_id=link.id,
            provenance="test",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()



@pytest.mark.parametrize(
    ("model", "values"),
    [
        (Task, {"title": "t", "state": "invalid", "provenance": "test"}),
        (Commitment, {"description": "c", "state": "invalid", "provenance": "test"}),
        (Question, {"question_text": "q", "state": "invalid", "provenance": "test"}),
        (NextStep, {"description": "n", "state": "invalid", "provenance": "test"}),
        (
            Alert,
            {
                "alert_type": "followup",
                "target_type": "crm_reference",
                "target_id": 1,
                "condition_key": "k",
                "state": "invalid",
                "provenance": "test",
            },
        ),
    ],
)
def test_phase2b_core_state_constraints(db_session, model, values):
    db_session.add(model(**values))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_alert_deduplicates_only_active_condition(db_session):
    base = dict(
        alert_type="followup",
        target_type="crm_reference",
        target_id=7,
        condition_key="stale",
        provenance="test",
    )
    first = Alert(**base, state="active")
    db_session.add(first)
    db_session.flush()

    duplicate = Alert(**base, state="active")
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_alert_recurrence_allowed_after_resolution(db_session):
    base = dict(
        alert_type="followup",
        target_type="crm_reference",
        target_id=8,
        condition_key="stale",
        provenance="test",
    )
    closed = Alert(**base, state="resolved")
    current = Alert(**base, state="active")
    db_session.add_all([closed, current])
    db_session.flush()
