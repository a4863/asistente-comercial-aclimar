from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.persistence.models import (
    ActionProposal,
    Alert,
    ApprovalDecision,
    CRMContextLink,
    CRMReference,
    Commitment,
    Conversation,
    ConversationMembership,
    EmailAttachmentMetadata,
    EmailMessage,
    ExecutionResult,
    ExtractedFact,
    FollowUpPreference,
    FollowUpPreferenceHistory,
    Inference,
    InferenceSupport,
    IMAPMessageLocation,
    IdentityLink,
    IdentityLinkCorrection,
    IdempotencyIdentity,
    ManualNote,
    NextStep,
    OperationalEvidenceLink,
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



def test_follow_up_preference_allows_one_current_per_scope(db_session):
    first = FollowUpPreference(
        scope_type="company",
        scope_reference="crm-1",
        classification="manual",
        inactivity_days=7,
        provenance="test",
    )
    db_session.add(first)
    db_session.flush()
    duplicate = FollowUpPreference(
        scope_type="company",
        scope_reference="crm-1",
        classification="manual",
        inactivity_days=5,
        provenance="test",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_follow_up_global_scope_is_unique(db_session):
    first = FollowUpPreference(
        scope_type="global",
        scope_reference=None,
        classification="default",
        inactivity_days=7,
        provenance="test",
    )
    db_session.add(first)
    db_session.flush()
    duplicate = FollowUpPreference(
        scope_type="global",
        scope_reference=None,
        classification="default",
        inactivity_days=5,
        provenance="test",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_follow_up_history_is_separate_append_only_table(db_session):
    preference = FollowUpPreference(
        scope_type="contact",
        scope_reference="crm-2",
        classification="manual",
        inactivity_days=7,
        provenance="test",
    )
    db_session.add(preference)
    db_session.flush()
    history = FollowUpPreferenceHistory(
        follow_up_preference_id=preference.id,
        scope_type=preference.scope_type,
        scope_reference=preference.scope_reference,
        classification=preference.classification,
        inactivity_days=preference.inactivity_days,
        explicit_future_date=None,
        provenance="test",
    )
    db_session.add(history)
    db_session.flush()
    assert history.follow_up_preference_id == preference.id


def _idempotency(db_session, key):
    record = IdempotencyIdentity(
        operation_kind="action",
        scope="test",
        identity_key=key,
    )
    db_session.add(record)
    db_session.flush()
    return record


def test_action_proposal_state_and_idempotency_identity_constraints(db_session):
    identity = _idempotency(db_session, "action-1")
    proposal = ActionProposal(
        action_type="create_draft",
        target_type="email",
        target_reference="msg-1",
        state="pending_approval",
        idempotency_identity_id=identity.id,
        provenance="test",
    )
    db_session.add(proposal)
    db_session.flush()

    invalid_identity = _idempotency(db_session, "action-2")
    db_session.add(
        ActionProposal(
            action_type="create_draft",
            target_type="email",
            target_reference="msg-2",
            state="invalid",
            idempotency_identity_id=invalid_identity.id,
            provenance="test",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_approval_decision_is_one_per_action_proposal(db_session):
    identity = _idempotency(db_session, "decision-1")
    proposal = ActionProposal(
        action_type="move_email",
        target_type="email",
        target_reference="msg-3",
        idempotency_identity_id=identity.id,
        provenance="test",
    )
    db_session.add(proposal)
    db_session.flush()
    first = ApprovalDecision(
        action_proposal_id=proposal.id,
        decision="approved",
        actor_reference="user",
        provenance="test",
    )
    db_session.add(first)
    db_session.flush()
    db_session.add(
        ApprovalDecision(
            action_proposal_id=proposal.id,
            decision="rejected",
            actor_reference="user",
            provenance="test",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_execution_result_requires_valid_outcome_and_revalidation(db_session):
    identity = _idempotency(db_session, "exec-1")
    proposal = ActionProposal(
        action_type="crm_write",
        target_type="crm",
        target_reference="opportunity-1",
        idempotency_identity_id=identity.id,
        provenance="test",
    )
    db_session.add(proposal)
    db_session.flush()
    decision = ApprovalDecision(
        action_proposal_id=proposal.id,
        decision="approved",
        actor_reference="user",
        provenance="test",
    )
    db_session.add(decision)
    db_session.flush()
    result = ExecutionResult(
        action_proposal_id=proposal.id,
        approval_decision_id=decision.id,
        revalidation_reference="snapshot-1",
        outcome="executed",
        provenance="test",
    )
    db_session.add(result)
    db_session.flush()

    db_session.add(
        ExecutionResult(
            action_proposal_id=proposal.id,
            approval_decision_id=decision.id,
            revalidation_reference="snapshot-2",
            outcome="invalid",
            provenance="test",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize(
    ("evidence_type", "evidence_id", "evidence_reference", "valid"),
    [
        ("source", 1, None, True),
        ("fact", 1, "fact:1", True),
        ("user_confirmation", None, "confirmed-by-user", True),
        ("user_confirmation", 1, "confirmed-by-user", False),
        ("source", None, None, False),
        ("unknown", 1, None, False),
    ],
)
def test_operational_evidence_shape_constraints(
    db_session, evidence_type, evidence_id, evidence_reference, valid
):
    link = OperationalEvidenceLink(
        operational_type="task",
        operational_id=1,
        evidence_type=evidence_type,
        evidence_id=evidence_id,
        evidence_reference=evidence_reference,
        provenance="test",
    )
    db_session.add(link)
    if valid:
        db_session.flush()
    else:
        with pytest.raises(IntegrityError):
            db_session.flush()


def _email_source(db_session, key):
    record = SourceRecord(
        source_type="email_message",
        source_system_scope="imap:account",
        stable_external_id=key,
        manual_entry=False,
        provenance="test",
    )
    db_session.add(record)
    db_session.flush()
    return record


def _email_message(db_session, key="message"):
    record = EmailMessage(
        source_record_id=_email_source(db_session, key).id,
        normalized_message_id="<same@example.com>",
        normalized_body="body",
        body_size_bytes=4,
        provenance="test",
    )
    db_session.add(record)
    db_session.flush()
    return record


def test_email_message_is_one_to_one_with_source_and_message_id_is_not_global(db_session):
    source = _email_source(db_session, "email-1")
    first = EmailMessage(
        source_record_id=source.id,
        normalized_message_id="<duplicate@example.com>",
        provenance="test",
    )
    second = EmailMessage(
        source_record_id=_email_source(db_session, "email-2").id,
        normalized_message_id="<duplicate@example.com>",
        provenance="test",
    )
    db_session.add_all([first, second])
    db_session.flush()

    db_session.add(EmailMessage(source_record_id=source.id, provenance="test"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_email_message_rejects_negative_body_size(db_session):
    db_session.add(
        EmailMessage(
            source_record_id=_email_source(db_session, "negative-body").id,
            body_size_bytes=-1,
            provenance="test",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_imap_location_constraints_and_multiple_locations(db_session):
    message = _email_message(db_session, "locations")
    first = IMAPMessageLocation(
        email_message_id=message.id,
        account_scope="imap:account",
        folder_name="INBOX",
        uidvalidity=1,
        uid=10,
        last_observed_at=datetime.now(timezone.utc),
        provenance="test",
    )
    second = IMAPMessageLocation(
        email_message_id=message.id,
        account_scope="imap:account",
        folder_name="Sent",
        uidvalidity=1,
        uid=10,
        last_observed_at=datetime.now(timezone.utc),
        provenance="test",
    )
    db_session.add_all([first, second])
    db_session.flush()

    db_session.add(
        IMAPMessageLocation(
            email_message_id=message.id,
            account_scope="imap:account",
            folder_name="INBOX",
            uidvalidity=1,
            uid=10,
            last_observed_at=datetime.now(timezone.utc),
            provenance="test",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize(
    ("uidvalidity", "uid", "location_state"),
    [(-1, 1, "active"), (0, 0, "active"), (0, 1, "invalid")],
)
def test_imap_location_rejects_invalid_state_or_uid(db_session, uidvalidity, uid, location_state):
    message = _email_message(db_session, f"invalid-location-{uidvalidity}-{uid}-{location_state}")
    db_session.add(
        IMAPMessageLocation(
            email_message_id=message.id,
            account_scope="imap:account",
            folder_name="INBOX",
            uidvalidity=uidvalidity,
            uid=uid,
            location_state=location_state,
            last_observed_at=datetime.now(timezone.utc),
            provenance="test",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_attachment_metadata_constraints_and_no_raw_content_fields(db_session):
    message = _email_message(db_session, "attachments")
    db_session.add(EmailAttachmentMetadata(email_message_id=message.id, part_index=0, filename="a.pdf", byte_size=1, provenance="test"))
    db_session.flush()
    db_session.add(EmailAttachmentMetadata(email_message_id=message.id, part_index=0, provenance="test"))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize(
    ("part_index", "byte_size"),
    [(-1, None), (1, -1)],
)
def test_attachment_metadata_rejects_negative_values(db_session, part_index, byte_size):
    message = _email_message(db_session, f"attachment-{part_index}-{byte_size}")
    db_session.add(
        EmailAttachmentMetadata(
            email_message_id=message.id,
            part_index=part_index,
            byte_size=byte_size,
            provenance="test",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_email_schema_contains_no_raw_mime_or_attachment_bytes():
    email_columns = set(EmailMessage.__table__.columns.keys())
    attachment_columns = set(EmailAttachmentMetadata.__table__.columns.keys())
    prohibited = {"raw_mime", "raw_html", "attachment_bytes", "content_bytes", "blob"}
    assert prohibited.isdisjoint(email_columns)
    assert prohibited.isdisjoint(attachment_columns)
