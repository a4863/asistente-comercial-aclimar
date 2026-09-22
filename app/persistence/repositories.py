from datetime import datetime, timezone
from hashlib import sha256
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import (
    ActionProposal,
    Activity,
    ActivitySourceLink,
    Alert,
    ApprovalDecision,
    AuditEvent,
    Commitment,
    CRMContextLink,
    CRMReference,
    Conversation,
    ConversationMembership,
    EmailAttachmentMetadata,
    EmailMessage,
    ExtractedFact,
    FactSourceEvidence,
    ExecutionResult,
    FollowUpPreference,
    FollowUpPreferenceHistory,
    IdempotencyIdentity,
    IdentityLink,
    IdentityLinkCorrection,
    IMAPMessageLocation,
    Inference,
    InferenceSupport,
    ManualNote,
    NextStep,
    OperationalEvidenceLink,
    Proposal,
    ProposalSupport,
    Question,
    SourceObservation,
    SourceRecord,
    SynchronizationCheckpoint,
    Task,
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
OPERATIONAL_MODELS = {
    "task": Task,
    "commitment": Commitment,
    "question": Question,
    "next_step": NextStep,
    "alert": Alert,
    "action_proposal": ActionProposal,
}
OPERATIONAL_EVIDENCE_TYPES = {"source", "fact", "inference", "proposal", "user_confirmation"}
FOLLOW_UP_DEFAULTS = {
    "new_or_qualified_opportunity": 7,
    "sent_offer": 5,
    "homologation_docs": 7,
    "negotiation_review": 5,
}
FOLLOW_UP_SCOPE_RANK = {
    "opportunity": 0,
    "offer": 0,
    "work": 0,
    "company": 1,
    "contact": 1,
    "global": 2,
}


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


class OperationalRepository:
    def __init__(self, session: Session):
        self.session = session
        self.audit = AuditRepository(session)

    def _transition(self, model, record_type, record_id, target_state, allowed, evidence_reference, required_evidence, reference_field):
        record = self.session.get(model, record_id)
        if record is None:
            raise ValueError(f"{record_type} not found")
        if target_state not in allowed.get(record.state, set()):
            raise ValueError("invalid state transition")
        if target_state in required_evidence and not evidence_reference:
            raise ValueError("transition requires evidence or user confirmation")
        record.state = target_state
        if target_state in required_evidence:
            setattr(record, reference_field, evidence_reference)
        self.audit.append(
            event_type=f"{record_type}_transitioned",
            affected_record_type=record_type,
            affected_record_id=record.id,
            actor_or_source="repository",
            provenance=record.provenance,
            outcome_reference=target_state,
        )
        return record

    def create_task(self, title: str, provenance: str, due_at: datetime | None = None):
        record = Task(title=title, due_at=due_at, provenance=provenance)
        self.session.add(record)
        return record

    def transition_task(self, task_id: int, target_state: str, evidence_reference: str | None = None):
        return self._transition(
            Task,
            "task",
            task_id,
            target_state,
            {"proposed": {"pending", "cancelled"}, "pending": {"completed", "cancelled"}},
            evidence_reference,
            {"completed"},
            "completion_reference",
        )

    def create_commitment(self, description: str, provenance: str, due_at: datetime | None = None):
        record = Commitment(description=description, due_at=due_at, provenance=provenance)
        self.session.add(record)
        return record

    def transition_commitment(self, commitment_id: int, target_state: str, evidence_reference: str | None = None):
        return self._transition(
            Commitment,
            "commitment",
            commitment_id,
            target_state,
            {"detected": {"confirmed", "cancelled"}, "confirmed": {"fulfilled", "overdue", "cancelled"}},
            evidence_reference,
            {"fulfilled"},
            "resolution_reference",
        )

    def evaluate_overdue(self, now: datetime):
        records = list(
            self.session.scalars(
                select(Commitment).where(
                    Commitment.state == "confirmed",
                    Commitment.due_at.is_not(None),
                    Commitment.due_at < now,
                )
            )
        )
        for record in records:
            record.state = "overdue"
            self.audit.append(
                event_type="commitment_overdue_evaluated",
                affected_record_type="commitment",
                affected_record_id=record.id,
                actor_or_source="controlled_clock",
                provenance=record.provenance,
                outcome_reference=now.isoformat(),
            )
        return records

    def create_question(self, question_text: str, provenance: str):
        record = Question(question_text=question_text, provenance=provenance)
        self.session.add(record)
        return record

    def transition_question(self, question_id: int, target_state: str, evidence_reference: str | None = None):
        return self._transition(
            Question,
            "question",
            question_id,
            target_state,
            {"detected": {"open", "dismissed"}, "open": {"answered", "dismissed"}},
            evidence_reference,
            {"answered"},
            "answer_reference",
        )

    def create_next_step(self, description: str, provenance: str, target_at: datetime | None = None):
        record = NextStep(description=description, target_at=target_at, provenance=provenance)
        self.session.add(record)
        return record

    def transition_next_step(self, next_step_id: int, target_state: str, evidence_reference: str | None = None):
        return self._transition(
            NextStep,
            "next_step",
            next_step_id,
            target_state,
            {"proposed": {"planned", "cancelled"}, "planned": {"completed", "cancelled"}},
            evidence_reference,
            {"completed"},
            "completion_reference",
        )

    def get_or_create_alert(self, alert_type: str, target_type: str, target_id: int, condition_key: str, provenance: str, priority: str | None = None):
        existing = self.session.scalar(
            select(Alert).where(
                Alert.alert_type == alert_type,
                Alert.target_type == target_type,
                Alert.target_id == target_id,
                Alert.condition_key == condition_key,
                Alert.state == "active",
            )
        )
        if existing:
            return existing
        record = Alert(alert_type=alert_type, target_type=target_type, target_id=target_id, condition_key=condition_key, priority=priority, provenance=provenance)
        self.session.add(record)
        return record

    def _close_alert(self, alert_id: int, state: str, actor_or_source: str):
        record = self.session.get(Alert, alert_id)
        if record is None:
            raise ValueError("alert not found")
        if record.state != "active":
            raise ValueError("alert is not active")
        record.state = state
        record.resolved_at = datetime.now(timezone.utc)
        self.audit.append(
            event_type=f"alert_{state}",
            affected_record_type="alert",
            affected_record_id=record.id,
            actor_or_source=actor_or_source,
            provenance=record.provenance,
        )
        return record

    def resolve_alert(self, alert_id: int, actor_or_source: str = "system"):
        return self._close_alert(alert_id, "resolved", actor_or_source)

    def dismiss_alert(self, alert_id: int, actor_reference: str):
        if not actor_reference:
            raise ValueError("dismissal requires explicit actor confirmation")
        return self._close_alert(alert_id, "dismissed", actor_reference)

    def get_follow_up_preference(self, scope_type: str, scope_reference: str | None = None):
        return self.session.scalar(
            select(FollowUpPreference).where(
                FollowUpPreference.scope_type == scope_type,
                FollowUpPreference.scope_reference == scope_reference,
            )
        )

    def set_follow_up_preference(self, scope_type: str, scope_reference: str | None, classification: str, inactivity_days: int | None = None, explicit_future_date: datetime | None = None, provenance: str = "user"):
        if scope_type not in FOLLOW_UP_SCOPE_RANK:
            raise ValueError("unsupported follow-up scope")
        if scope_type == "global" and scope_reference is not None:
            raise ValueError("global preference cannot have a scope reference")
        if scope_type != "global" and not scope_reference:
            raise ValueError("scoped preference requires a scope reference")
        if inactivity_days is not None and inactivity_days < 0:
            raise ValueError("inactivity_days must be non-negative")
        record = self.get_follow_up_preference(scope_type, scope_reference)
        if record is None:
            record = FollowUpPreference(
                scope_type=scope_type,
                scope_reference=scope_reference,
                classification=classification,
                inactivity_days=inactivity_days,
                explicit_future_date=explicit_future_date,
                provenance=provenance,
                updated_at=datetime.now(timezone.utc),
            )
            self.session.add(record)
            self.session.flush()
        else:
            record.classification = classification
            record.inactivity_days = inactivity_days
            record.explicit_future_date = explicit_future_date
            record.provenance = provenance
            record.updated_at = datetime.now(timezone.utc)
        self.session.add(
            FollowUpPreferenceHistory(
                follow_up_preference_id=record.id,
                scope_type=record.scope_type,
                scope_reference=record.scope_reference,
                classification=record.classification,
                inactivity_days=record.inactivity_days,
                explicit_future_date=record.explicit_future_date,
                provenance=provenance,
            )
        )
        return record

    def resolve_follow_up_preference(self, classification: str, crm_scopes=(), manual_scope: tuple[str, str] | None = None):
        scopes = sorted(crm_scopes, key=lambda scope: FOLLOW_UP_SCOPE_RANK[scope[0]])
        if manual_scope is not None:
            scopes.append(manual_scope)
        scopes.append(("global", None))
        preference = None
        for scope_type, scope_reference in scopes:
            preference = self.get_follow_up_preference(scope_type, scope_reference)
            if preference is not None and preference.classification == classification:
                break
        else:
            preference = None
        explicit_future_date = preference.explicit_future_date if preference else None
        inactivity_days = (
            None
            if explicit_future_date is not None
            else (
                preference.inactivity_days
                if preference and preference.inactivity_days is not None
                else FOLLOW_UP_DEFAULTS.get(classification)
            )
        )
        return {
            "preference": preference,
            "explicit_future_date": explicit_future_date,
            "inactivity_days": inactivity_days,
        }

    def add_operational_evidence(self, operational_type: str, operational_id: int, evidence_type: str, evidence_id: int | None = None, evidence_reference: str | None = None, provenance: str = "system"):
        model = OPERATIONAL_MODELS.get(operational_type)
        if model is None or self.session.get(model, operational_id) is None:
            raise ValueError("unsupported or missing operational target")
        if evidence_type not in OPERATIONAL_EVIDENCE_TYPES:
            raise ValueError("unsupported evidence type")
        if evidence_type == "user_confirmation":
            if evidence_id is not None or not evidence_reference:
                raise ValueError("user confirmation requires reference without evidence id")
        elif evidence_id is None:
            raise ValueError("evidence type requires evidence id")
        record = OperationalEvidenceLink(
            operational_type=operational_type,
            operational_id=operational_id,
            evidence_type=evidence_type,
            evidence_id=evidence_id,
            evidence_reference=evidence_reference,
            provenance=provenance,
        )
        self.session.add(record)
        return record


class ActionRepository:
    def __init__(self, session: Session):
        self.session = session
        self.audit = AuditRepository(session)

    def _get_or_reserve_identity(self, operation_kind: str, scope: str, identity_key: str):
        identity = self.session.scalar(
            select(IdempotencyIdentity).where(
                IdempotencyIdentity.operation_kind == operation_kind,
                IdempotencyIdentity.scope == scope,
                IdempotencyIdentity.identity_key == identity_key,
            )
        )
        if identity is None:
            identity = IdempotencyIdentity(operation_kind=operation_kind, scope=scope, identity_key=identity_key)
            self.session.add(identity)
            self.session.flush()
        return identity

    def create_action_proposal(self, action_type: str, target_type: str, target_reference: str, operation_kind: str, scope: str, identity_key: str, provenance: str):
        identity = self._get_or_reserve_identity(operation_kind, scope, identity_key)
        existing = self.session.scalar(
            select(ActionProposal).where(ActionProposal.idempotency_identity_id == identity.id)
        )
        if existing:
            return existing
        record = ActionProposal(
            action_type=action_type,
            target_type=target_type,
            target_reference=target_reference,
            idempotency_identity_id=identity.id,
            provenance=provenance,
        )
        self.session.add(record)
        return record

    def decide_action(self, action_proposal_id: int, decision: str, actor_reference: str, provenance: str):
        proposal = self.session.get(ActionProposal, action_proposal_id)
        if proposal is None:
            raise ValueError("action proposal not found")
        if decision not in {"approved", "rejected"} or proposal.state != "pending_approval":
            raise ValueError("proposal cannot be decided")
        if self.session.scalar(select(ApprovalDecision).where(ApprovalDecision.action_proposal_id == proposal.id)):
            raise ValueError("proposal already has a decision")
        record = ApprovalDecision(action_proposal_id=proposal.id, decision=decision, actor_reference=actor_reference, provenance=provenance)
        proposal.state = decision
        self.session.add(record)
        self.audit.append(event_type="action_proposal_decided", affected_record_type="action_proposal", affected_record_id=proposal.id, actor_or_source=actor_reference, provenance=provenance, outcome_reference=decision)
        return record

    def append_execution_result(self, action_proposal_id: int, outcome: str, revalidation_reference: str, provenance: str, external_result_reference: str | None = None, failure_code: str | None = None):
        proposal = self.session.get(ActionProposal, action_proposal_id)
        if proposal is None or proposal.state not in {"approved", "error"}:
            raise ValueError("proposal is not approved")
        if not revalidation_reference:
            raise ValueError("execution requires revalidation reference")
        if outcome not in {"executed", "error"}:
            raise ValueError("unsupported execution outcome")
        decision = self.session.scalar(select(ApprovalDecision).where(ApprovalDecision.action_proposal_id == proposal.id, ApprovalDecision.decision == "approved"))
        if decision is None:
            raise ValueError("approved decision is required")
        result = ExecutionResult(action_proposal_id=proposal.id, approval_decision_id=decision.id, revalidation_reference=revalidation_reference, outcome=outcome, external_result_reference=external_result_reference, failure_code=failure_code, provenance=provenance)
        proposal.state = outcome
        self.session.add(result)
        self.audit.append(event_type="action_proposal_execution_recorded", affected_record_type="action_proposal", affected_record_id=proposal.id, actor_or_source="repository", provenance=provenance, outcome_reference=outcome, failure_code=failure_code)
        return result


_EMAIL_FIELDS = frozenset({
    "normalized_message_id", "sender_address", "recipient_addresses", "subject",
    "sent_at", "received_at", "in_reply_to", "references_header",
    "normalized_body", "body_size_bytes", "content_truncated", "provenance",
})
_ATTACHMENT_FIELDS = frozenset({
    "filename", "media_type", "byte_size", "content_id", "disposition", "provenance",
})
_OBSERVATION_EVENTS = frozenset({"ingested", "updated", "moved", "unavailable", "reactivated", "reconciled"})
_CHECKPOINT_RE = re.compile(r"v1:([1-9][0-9]*):(0|[1-9][0-9]*)\Z", re.ASCII)
_HEX_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


def _imap_digest(*components: object) -> str:
    digest = sha256()
    for component in components:
        encoded = str(component).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


class IMAPSyncRepository:
    """Session-scoped, non-committing persistence for read-only IMAP ingestion."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def location_key(account_scope: str, folder_name: str, uidvalidity: int, uid: int) -> str:
        if not account_scope or not folder_name or not isinstance(uidvalidity, int) or uidvalidity <= 0 or not isinstance(uid, int) or uid <= 0:
            raise ValueError("invalid IMAP location identity")
        return _imap_digest(account_scope, folder_name, uidvalidity, uid)

    @staticmethod
    def checkpoint_scope(account_scope: str, folder_name: str) -> str:
        if not account_scope or not folder_name:
            raise ValueError("invalid IMAP checkpoint scope")
        return "imap-folder:v1:" + _imap_digest(account_scope, folder_name)

    def find_location(self, account_scope: str, folder_name: str, uidvalidity: int, uid: int):
        self.location_key(account_scope, folder_name, uidvalidity, uid)
        location = self.session.scalar(select(IMAPMessageLocation).where(
            IMAPMessageLocation.account_scope == account_scope,
            IMAPMessageLocation.folder_name == folder_name,
            IMAPMessageLocation.uidvalidity == uidvalidity,
            IMAPMessageLocation.uid == uid,
        ))
        if location is None:
            return None
        email = self.session.get(EmailMessage, location.email_message_id)
        source = self.session.get(SourceRecord, email.source_record_id)
        return location, email, source

    def find_message_id_candidates(self, account_scope: str, normalized_message_id: str):
        if not normalized_message_id or not normalized_message_id.strip():
            return ()
        return tuple(self.session.scalars(
            select(EmailMessage).join(SourceRecord, EmailMessage.source_record_id == SourceRecord.id).where(
                SourceRecord.source_system_scope == account_scope,
                SourceRecord.source_type == "email_message",
                EmailMessage.normalized_message_id == normalized_message_id,
            ).order_by(EmailMessage.id)
        ))

    def create_independent_occurrence(self, account_scope: str, folder_name: str, uidvalidity: int, uid: int, observed_at: datetime, email_values: dict, provenance: str = "imap_sync"):
        key = self.location_key(account_scope, folder_name, uidvalidity, uid)
        if self.find_location(account_scope, folder_name, uidvalidity, uid) is not None:
            raise ValueError("IMAP location already exists")
        if not set(email_values) <= _EMAIL_FIELDS or "provenance" in email_values or any(isinstance(value, (bytes, bytearray, memoryview)) for value in email_values.values()):
            raise ValueError("unsupported email field")
        source = SourceRecord(source_type="email_message", source_system_scope=account_scope, stable_external_id="imap-occ:v1:" + key, manual_entry=False, provenance=provenance)
        self.session.add(source)
        self.session.flush()
        email = EmailMessage(source_record_id=source.id, provenance=provenance, **email_values)
        self.session.add(email)
        self.session.flush()
        location = self.link_location(email, account_scope, folder_name, uidvalidity, uid, observed_at, provenance)
        return source, email, location

    def link_location(self, email: EmailMessage, account_scope: str, folder_name: str, uidvalidity: int, uid: int, observed_at: datetime, provenance: str = "imap_sync"):
        self.location_key(account_scope, folder_name, uidvalidity, uid)
        source = self.session.get(SourceRecord, email.source_record_id)
        if source is None or source.source_system_scope != account_scope or source.source_type != "email_message":
            raise ValueError("IMAP email account scope mismatch")
        existing = self.find_location(account_scope, folder_name, uidvalidity, uid)
        if existing is not None:
            if existing[1].id != email.id:
                raise ValueError("IMAP location belongs to another email")
            return existing[0]
        location = IMAPMessageLocation(email_message_id=email.id, account_scope=account_scope, folder_name=folder_name, uidvalidity=uidvalidity, uid=uid, location_state="active", last_observed_at=observed_at, provenance=provenance)
        self.session.add(location)
        return location

    def reserve_occurrence_identity(self, source: SourceRecord, account_scope: str, folder_name: str, uidvalidity: int, uid: int):
        key = self.location_key(account_scope, folder_name, uidvalidity, uid)
        if source.source_system_scope != account_scope or source.source_type != "email_message":
            raise ValueError("IMAP occurrence account scope mismatch")
        scope = "imap-account:v1:" + _imap_digest(account_scope)
        identity_key = "v1:" + key
        identity = self.session.scalar(select(IdempotencyIdentity).where(
            IdempotencyIdentity.operation_kind == "imap_occurrence",
            IdempotencyIdentity.scope == scope,
            IdempotencyIdentity.identity_key == identity_key,
        ))
        if identity is not None:
            if identity.source_record_id != source.id:
                raise ValueError("IMAP occurrence identity disagrees with source")
            return identity
        identity = IdempotencyIdentity(operation_kind="imap_occurrence", scope=scope, identity_key=identity_key, source_record_id=source.id)
        self.session.add(identity)
        return identity

    def set_location_state(self, location: IMAPMessageLocation, state: str, observed_at: datetime) -> bool:
        if state not in {"active", "unavailable"}:
            raise ValueError("invalid IMAP location state")
        changed = location.location_state != state
        location.location_state = state
        location.last_observed_at = observed_at
        return changed

    def update_email(self, email: EmailMessage, values: dict) -> bool:
        if not set(values) <= _EMAIL_FIELDS or any(isinstance(value, (bytes, bytearray, memoryview)) for value in values.values()):
            raise ValueError("unsupported email field")
        changed = False
        for field, value in values.items():
            if getattr(email, field) != value:
                setattr(email, field, value)
                changed = True
        return changed

    def replace_attachments(self, email: EmailMessage, attachments: list[dict]) -> bool:
        desired = {}
        for item in attachments:
            if set(item) - (_ATTACHMENT_FIELDS | {"part_index"}) or "part_index" not in item or not isinstance(item["part_index"], int) or item["part_index"] < 0 or any(isinstance(value, (bytes, bytearray, memoryview)) for value in item.values()):
                raise ValueError("invalid attachment metadata")
            if item["part_index"] in desired:
                raise ValueError("duplicate attachment part")
            desired[item["part_index"]] = {field: item.get(field) for field in _ATTACHMENT_FIELDS}
        existing = {part.part_index: part for part in self.session.scalars(select(EmailAttachmentMetadata).where(EmailAttachmentMetadata.email_message_id == email.id))}
        changed = False
        for index, part in existing.items():
            if index not in desired:
                self.session.delete(part)
                changed = True
        for index, values in desired.items():
            part = existing.get(index)
            if part is None:
                if not values["provenance"]:
                    raise ValueError("attachment provenance is required")
                self.session.add(EmailAttachmentMetadata(email_message_id=email.id, part_index=index, **values))
                changed = True
            else:
                for field, value in values.items():
                    if field == "provenance" and value is None:
                        continue
                    if getattr(part, field) != value:
                        setattr(part, field, value)
                        changed = True
        return changed

    def append_observation(self, source: SourceRecord, location: IMAPMessageLocation, event_kind: str, content_digest: str, observed_at: datetime):
        if event_kind not in _OBSERVATION_EVENTS or not _HEX_DIGEST_RE.fullmatch(content_digest):
            raise ValueError("invalid IMAP observation metadata")
        key = self.location_key(location.account_scope, location.folder_name, location.uidvalidity, location.uid)
        prefix = f"imap:v1:{key}:{event_kind}:"
        prior = tuple(self.session.scalars(select(SourceObservation).where(
            SourceObservation.source_record_id == source.id,
            SourceObservation.source_version_marker.startswith(prefix),
        ).order_by(SourceObservation.id)))
        location_prefix = f"imap:v1:{key}:"
        latest_location_observation = self.session.scalars(
            select(SourceObservation).where(
                SourceObservation.source_record_id == source.id,
                SourceObservation.source_version_marker.startswith(location_prefix),
            ).order_by(SourceObservation.id.desc())
        ).first()
        if (
            latest_location_observation is not None
            and latest_location_observation.source_version_marker.startswith(prefix)
            and latest_location_observation.source_version_marker.endswith(":" + content_digest)
            and latest_location_observation.observed_state == location.location_state
        ):
            return latest_location_observation, False
        marker = f"{prefix}{len(prior) + 1}:{content_digest}"
        observation = SourceObservation(source_record_id=source.id, observed_at=observed_at, source_version_marker=marker, observed_state=location.location_state, outcome=event_kind, provenance="imap_sync")
        self.session.add(observation)
        return observation, True

    def append_audit(self, event_type: str, affected_record_type: str, affected_record_id: int, outcome: str, occurred_at: datetime):
        if event_type not in {"imap_source_ingested", "imap_source_updated", "imap_location_transitioned", "imap_reconciled"} or affected_record_type not in {"source_record", "imap_message_location", "synchronization_checkpoint"} or not isinstance(affected_record_id, int) or affected_record_id <= 0 or outcome not in _OBSERVATION_EVENTS:
            raise ValueError("invalid IMAP audit metadata")
        return AuditRepository(self.session).append(event_type=event_type, affected_record_type=affected_record_type, affected_record_id=affected_record_id, actor_or_source="imap_sync", occurred_at=occurred_at, provenance="imap_sync", outcome_reference=outcome)

    def read_folder_checkpoint(self, account_scope: str, folder_name: str):
        row = SourceRepository(self.session).get_checkpoint(self.checkpoint_scope(account_scope, folder_name))
        if row is None:
            return None
        match = _CHECKPOINT_RE.fullmatch(row.checkpoint_marker or "")
        if match is None:
            raise ValueError("invalid IMAP checkpoint marker")
        return row, int(match.group(1)), int(match.group(2))

    def upsert_folder_checkpoint(self, account_scope: str, folder_name: str, uidvalidity: int, highest_committed_uid: int, last_success_at: datetime, last_outcome: str = "ok"):
        if not isinstance(uidvalidity, int) or uidvalidity <= 0 or not isinstance(highest_committed_uid, int) or highest_committed_uid < 0 or last_outcome not in {"ok", "degraded"}:
            raise ValueError("invalid IMAP checkpoint")
        prior = self.read_folder_checkpoint(account_scope, folder_name)
        if prior and prior[1] == uidvalidity and highest_committed_uid < prior[2]:
            raise ValueError("IMAP checkpoint cannot go backwards")
        marker = f"v1:{uidvalidity}:{highest_committed_uid}"
        return SourceRepository(self.session).upsert_checkpoint(self.checkpoint_scope(account_scope, folder_name), marker, last_success_at, last_outcome)

    def list_active_locations(self, account_scope: str, folder_name: str, uidvalidity: int):
        return tuple(self.session.scalars(select(IMAPMessageLocation).where(
            IMAPMessageLocation.account_scope == account_scope,
            IMAPMessageLocation.folder_name == folder_name,
            IMAPMessageLocation.uidvalidity == uidvalidity,
            IMAPMessageLocation.location_state == "active",
        ).order_by(IMAPMessageLocation.uid)))

    def list_source_locations(self, source: SourceRecord):
        return tuple(self.session.scalars(select(IMAPMessageLocation).join(EmailMessage, IMAPMessageLocation.email_message_id == EmailMessage.id).where(EmailMessage.source_record_id == source.id).order_by(IMAPMessageLocation.id)))
