from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import (
    Activity,
    ActivitySourceLink,
    AuditEvent,
    CRMContextLink,
    CRMReference,
    Conversation,
    ConversationMembership,
    ExtractedFact,
    FactSourceEvidence,
    IdempotencyIdentity,
    IdentityLink,
    IdentityLinkCorrection,
    Inference,
    InferenceSupport,
    ManualNote,
    Proposal,
    ProposalSupport,
    SourceObservation,
    SourceRecord,
    SynchronizationCheckpoint,
    WhatsAppImport,
)


CRM_CONTEXT_RECORD_TYPES = {
    "source_record",
    "conversation",
    "activity",
    "manual_note",
    "whatsapp_import",
    "calendar_event_representation",
    "extracted_fact",
    "inference",
    "proposal",
}
INFERENCE_SUPPORT_TYPES = {"source", "fact", "inference"}
PROPOSAL_SUPPORT_TYPES = {"source", "fact", "inference", "proposal"}
AUDIT_FIELDS = {
    "event_type",
    "affected_record_type",
    "affected_record_id",
    "actor_or_source",
    "occurred_at",
    "provenance",
    "outcome_reference",
    "failure_code",
}
UNSAFE_AUDIT_FIELDS = {"payload", "secret", "token", "password", "body", "raw_content"}


class SourceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_source(self, **values):
        external_id = values.get("stable_external_id")
        if external_id is not None:
            existing = self.session.scalar(
                select(SourceRecord).where(
                    SourceRecord.source_system_scope == values["source_system_scope"],
                    SourceRecord.stable_external_id == external_id,
                )
            )
            if existing:
                return existing
        record = SourceRecord(**values)
        self.session.add(record)
        return record

    def append_observation(self, **values):
        record = SourceObservation(**values)
        self.session.add(record)
        return record

    def mark_retention(self, record: SourceRecord, state: str, at: datetime):
        record.retention_state = state
        record.deleted_or_redacted_at = at
        observation = SourceObservation(
            source_record_id=record.id,
            observed_at=at,
            source_version_marker=f"retention:{at.isoformat()}",
            observed_state=state,
            outcome="retention_transition",
            provenance="repository",
        )
        self.session.add(observation)
        return observation

    def get_checkpoint(self, scope: str):
        return self.session.scalar(
            select(SynchronizationCheckpoint).where(
                SynchronizationCheckpoint.source_system_scope == scope
            )
        )

    def upsert_checkpoint(
        self,
        scope: str,
        checkpoint_marker: str | None,
        last_success_at: datetime | None,
        last_outcome: str,
        updated_at: datetime | None = None,
    ):
        checkpoint = self.get_checkpoint(scope)
        when = updated_at or datetime.now(timezone.utc)
        if checkpoint is None:
            checkpoint = SynchronizationCheckpoint(
                source_system_scope=scope,
                checkpoint_marker=checkpoint_marker,
                last_success_at=last_success_at,
                last_outcome=last_outcome,
                updated_at=when,
            )
            self.session.add(checkpoint)
            return checkpoint
        checkpoint.checkpoint_marker = checkpoint_marker
        checkpoint.last_success_at = last_success_at
        checkpoint.last_outcome = last_outcome
        checkpoint.updated_at = when
        return checkpoint

    def reserve_idempotency(self, **values):
        existing = self.get_idempotency(
            values["operation_kind"],
            values["scope"],
            values["identity_key"],
        )
        if existing:
            return existing
        record = IdempotencyIdentity(**values)
        self.session.add(record)
        return record

    def get_idempotency(self, operation_kind: str, scope: str, identity_key: str):
        return self.session.scalar(
            select(IdempotencyIdentity).where(
                IdempotencyIdentity.operation_kind == operation_kind,
                IdempotencyIdentity.scope == scope,
                IdempotencyIdentity.identity_key == identity_key,
            )
        )


class ProvenanceRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_conversation(self, provenance: str):
        record = Conversation(provenance=provenance)
        self.session.add(record)
        return record

    def add_conversation_membership(
        self,
        conversation_id: int,
        source_record_id: int,
        evidence_type: str,
        evidence_reference: str,
    ):
        record = ConversationMembership(
            conversation_id=conversation_id,
            source_record_id=source_record_id,
            evidence_type=evidence_type,
            evidence_reference=evidence_reference,
        )
        self.session.add(record)
        return record

    def create_manual_note(
        self,
        source_record_id: int,
        original_text: str,
        entered_at: datetime | None = None,
        provenance: str = "manual",
    ):
        record = ManualNote(
            source_record_id=source_record_id,
            original_text=original_text,
            entered_at=entered_at or datetime.now(timezone.utc),
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def create_whatsapp_import(
        self,
        source_record_id: int,
        original_text: str,
        pasted_at: datetime | None = None,
        provenance: str = "manual",
    ):
        record = WhatsAppImport(
            source_record_id=source_record_id,
            original_text=original_text,
            pasted_at=pasted_at or datetime.now(timezone.utc),
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def create_activity(
        self,
        activity_type: str,
        occurred_at: datetime | None,
        description_reference: str | None,
        provenance: str,
    ):
        record = Activity(
            activity_type=activity_type,
            occurred_at=occurred_at,
            description_reference=description_reference,
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def add_activity_source_link(
        self,
        activity_id: int,
        source_record_id: int,
        link_purpose: str,
    ):
        record = ActivitySourceLink(
            activity_id=activity_id,
            source_record_id=source_record_id,
            link_purpose=link_purpose,
        )
        self.session.add(record)
        return record

    def get_or_create_crm_reference(
        self,
        entity_type: str,
        external_id: str,
        display_reference: str | None = None,
        provenance: str = "system",
    ):
        existing = self.session.scalar(
            select(CRMReference).where(
                CRMReference.entity_type == entity_type,
                CRMReference.external_id == external_id,
            )
        )
        if existing:
            return existing
        record = CRMReference(
            entity_type=entity_type,
            external_id=external_id,
            display_reference=display_reference,
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def create_crm_context_link(
        self,
        crm_reference_id: int,
        assistant_record_type: str,
        assistant_record_id: int,
        relationship_purpose: str,
        confirmation_state: str,
        confirmed_at: datetime | None = None,
        provenance: str = "system",
    ):
        if assistant_record_type not in CRM_CONTEXT_RECORD_TYPES:
            raise ValueError("unsupported assistant_record_type")
        if confirmation_state == "confirmed" and confirmed_at is None:
            raise ValueError("confirmed context requires confirmed_at")
        if confirmation_state in {"ambiguous", "proposed"} and confirmed_at is not None:
            raise ValueError("non-confirmed context cannot have confirmed_at")
        if confirmation_state not in {"ambiguous", "proposed", "confirmed"}:
            raise ValueError("unsupported confirmation_state")
        record = CRMContextLink(
            crm_reference_id=crm_reference_id,
            assistant_record_type=assistant_record_type,
            assistant_record_id=assistant_record_id,
            relationship_purpose=relationship_purpose,
            confirmation_state=confirmation_state,
            confirmed_at=confirmed_at,
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def create_identity_link(
        self,
        identity_type: str,
        identity_value: str,
        crm_reference_id: int,
        status: str = "confirmed",
        confirmed_at: datetime | None = None,
        provenance: str = "user",
    ):
        record = IdentityLink(
            identity_type=identity_type,
            identity_value=identity_value,
            crm_reference_id=crm_reference_id,
            status=status,
            confirmed_at=confirmed_at or datetime.now(timezone.utc),
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def append_identity_correction(
        self,
        prior_identity_link_id: int,
        replacement_identity_link_id: int,
        corrected_at: datetime | None = None,
        provenance: str = "user",
    ):
        if prior_identity_link_id == replacement_identity_link_id:
            raise ValueError("identity correction requires distinct links")
        prior = self.session.get(IdentityLink, prior_identity_link_id)
        replacement = self.session.get(IdentityLink, replacement_identity_link_id)
        if prior is None or replacement is None:
            raise ValueError("identity link not found")
        when = corrected_at or datetime.now(timezone.utc)
        prior.superseded_at = when
        record = IdentityLinkCorrection(
            prior_identity_link_id=prior_identity_link_id,
            replacement_identity_link_id=replacement_identity_link_id,
            corrected_at=when,
            provenance=provenance,
        )
        self.session.add(record)
        return record


class DerivationRepository:
    def __init__(self, session: Session):
        self.session = session

    def append_fact(self, fact_type: str, value_reference: str, provenance: str):
        record = ExtractedFact(
            fact_type=fact_type,
            value_reference=value_reference,
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def add_fact_evidence(
        self,
        extracted_fact_id: int,
        source_record_id: int,
        evidence_reference: str,
    ):
        record = FactSourceEvidence(
            extracted_fact_id=extracted_fact_id,
            source_record_id=source_record_id,
            evidence_reference=evidence_reference,
        )
        self.session.add(record)
        return record

    def append_inference(
        self,
        inference_type: str,
        value_reference: str,
        provenance: str,
    ):
        record = Inference(
            inference_type=inference_type,
            value_reference=value_reference,
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def add_inference_support(
        self,
        inference_id: int,
        support_type: str,
        support_id: int,
    ):
        if support_type not in INFERENCE_SUPPORT_TYPES:
            raise ValueError("unsupported inference support type")
        record = InferenceSupport(
            inference_id=inference_id,
            support_type=support_type,
            support_id=support_id,
        )
        self.session.add(record)
        return record

    def append_proposal(
        self,
        proposal_type: str,
        value_reference: str,
        provenance: str,
        status: str = "proposed",
    ):
        record = Proposal(
            proposal_type=proposal_type,
            value_reference=value_reference,
            provenance=provenance,
            status=status,
        )
        self.session.add(record)
        return record

    def add_proposal_support(
        self,
        proposal_id: int,
        support_type: str,
        support_id: int,
    ):
        if support_type not in PROPOSAL_SUPPORT_TYPES:
            raise ValueError("unsupported proposal support type")
        record = ProposalSupport(
            proposal_id=proposal_id,
            support_type=support_type,
            support_id=support_id,
        )
        self.session.add(record)
        return record


class AuditRepository:
    def __init__(self, session: Session):
        self.session = session

    def append(self, **values):
        keys = set(values)
        if keys & UNSAFE_AUDIT_FIELDS:
            raise ValueError("unsafe audit fields")
        unexpected = keys - AUDIT_FIELDS
        if unexpected:
            raise ValueError("unsupported audit fields")
        event = AuditEvent(**values)
        self.session.add(event)
        return event

    def list_for(self, record_type: str, record_id: int):
        return list(
            self.session.scalars(
                select(AuditEvent).where(
                    AuditEvent.affected_record_type == record_type,
                    AuditEvent.affected_record_id == record_id,
                )
            )
        )
