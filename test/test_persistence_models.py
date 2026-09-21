import pytest
from sqlalchemy.exc import IntegrityError

from app.persistence.models import (Conversation, ConversationMembership, ExtractedFact, Inference, ManualNote, Proposal, SourceObservation, SourceRecord, WhatsAppImport)


def source(scope="manual", external_id=None):
    return SourceRecord(source_type="manual_note", source_system_scope=scope, stable_external_id=external_id, manual_entry=True, provenance="test")


def test_source_identity_and_observation_history(db_session):
    first, second = source(external_id="same"), source(external_id="same")
    db_session.add(first); db_session.flush(); db_session.add(SourceObservation(source_record_id=first.id, observed_state="active", outcome="ok", provenance="test")); db_session.add(second)
    with pytest.raises(IntegrityError): db_session.flush()


def test_manual_source_and_conversation_constraints(db_session):
    one, two = source(), source(); db_session.add_all([one, two]); db_session.flush()
    db_session.add_all([ManualNote(source_record_id=one.id, original_text="note"), WhatsAppImport(source_record_id=two.id, original_text="chat")])
    conversation = Conversation(provenance="test"); db_session.add(conversation); db_session.flush()
    db_session.add(ConversationMembership(conversation_id=conversation.id, source_record_id=one.id, evidence_type="message_id", evidence_reference="x")); db_session.flush()
    other = Conversation(provenance="test"); db_session.add(other); db_session.flush(); db_session.add(ConversationMembership(conversation_id=other.id, source_record_id=one.id, evidence_type="message_id", evidence_reference="x"))
    with pytest.raises(IntegrityError): db_session.flush()


def test_derived_types_are_physical_separate_models(db_session):
    db_session.add_all([ExtractedFact(fact_type="fact", value_reference="x", provenance="test"), Inference(inference_type="inference", value_reference="x", provenance="test"), Proposal(proposal_type="proposal", value_reference="x", provenance="test")])
    db_session.flush()
