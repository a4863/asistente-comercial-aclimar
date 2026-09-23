from datetime import datetime, timezone
from dataclasses import dataclass
from hashlib import sha256
import re
from uuid import UUID, uuid4

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
    ThreadEvidence,
    ThreadEvidenceDecision,
    ThreadLineageEdge,
    ThreadLineageOperation,
    ThreadMembershipChange,
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


@dataclass(frozen=True, slots=True)
class AccountThreadMember:
    source_record_id: int
    source_type: str
    account_scope: str


@dataclass(frozen=True, slots=True)
class AccountThreadSource:
    source_record_id: int
    account_scope: str
    retention_state: str
    deleted_or_redacted_at: datetime | None
    eligible: bool
    normalized_message_id: str | None
    in_reply_to: str | None
    references_header: str | None
    subject: str | None
    current_conversation_id: int | None
    conversation_account_scope: str | None
    conversation_legacy_status: str | None
    conversation_superseded_at: datetime | None
    full_current_member_ids: tuple[int, ...]
    full_current_members: tuple[AccountThreadMember, ...]


@dataclass(frozen=True, slots=True)
class AccountThreadSnapshot:
    account_scope: str
    sources: tuple[AccountThreadSource, ...]


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

    def create_conversation(self, provenance: str, account_scope: str):
        return ThreadPersistenceRepository(self.session).create_resolved_conversation(account_scope, provenance)

    def add_conversation_membership(
        self,
        conversation_id: int,
        source_record_id: int,
        evidence_type: str,
        evidence_reference: str,
        *,
        account_scope: str,
        reconstruction_key: str,
    ):
        return ThreadPersistenceRepository(self.session).assign_current_membership(
            account_scope=account_scope,
            source_record_id=source_record_id,
            new_conversation_id=conversation_id,
            reason="initial_assignment",
            reconstruction_key=reconstruction_key,
            evidence_type=evidence_type,
            evidence_reference=evidence_reference,
        )

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

    def list_account_locations(self, account_scope: str):
        """Return technical locations and their owning email/source for one account."""
        if not account_scope:
            raise ValueError("IMAP account scope is required")
        return tuple(self.session.execute(
            select(IMAPMessageLocation, EmailMessage, SourceRecord)
            .join(EmailMessage, IMAPMessageLocation.email_message_id == EmailMessage.id)
            .join(SourceRecord, EmailMessage.source_record_id == SourceRecord.id)
            .where(
                IMAPMessageLocation.account_scope == account_scope,
                SourceRecord.source_system_scope == account_scope,
                SourceRecord.source_type == "email_message",
            )
            .order_by(IMAPMessageLocation.id)
        ))

    def email_attachment_values(self, email: EmailMessage):
        """Read only approved metadata, never attachment bytes."""
        return tuple({
            "part_index": part.part_index,
            "filename": part.filename,
            "media_type": part.media_type,
            "byte_size": part.byte_size,
            "content_id": part.content_id,
            "disposition": part.disposition,
            "provenance": part.provenance,
        } for part in self.session.scalars(
            select(EmailAttachmentMetadata)
            .where(EmailAttachmentMetadata.email_message_id == email.id)
            .order_by(EmailAttachmentMetadata.part_index)
        ))


class ThreadPersistenceRepository:
    """Guarded, local-only 3D1 storage primitives. The caller owns commit/rollback."""

    _HEX = re.compile(r"[0-9a-f]{64}\Z")
    _KINDS = {"message_id", "in_reply_to", "references"}
    _OUTCOMES = {
        "identity_observed", "accepted_direct_parent", "accepted_ancestor",
        "unresolved_external", "duplicate_target", "malformed",
        "multiple_in_reply_to", "self_link", "cycle_rejected", "conflict", "not_linking",
    }
    _REASONS = {"initial_assignment", "merge", "split", "repartition", "correction"}

    def __init__(self, session: Session):
        self.session = session
        connection = session.connection()
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 1:
                raise RuntimeError("thread persistence requires SQLite foreign keys")

    @staticmethod
    def _digest(domain: str, *fields):
        payload = domain.encode("utf-8")
        for field in fields:
            if field is None:
                payload += b"-1:"
            else:
                encoded = str(field).encode("utf-8")
                payload += str(len(encoded)).encode("ascii") + b":" + encoded
        return sha256(payload).hexdigest()

    @classmethod
    def _require_hex(cls, value, name):
        if not isinstance(value, str) or not cls._HEX.fullmatch(value):
            raise ValueError(f"{name} must be lowercase SHA-256 hex")

    @staticmethod
    def _require_scope(scope):
        if not isinstance(scope, str) or not 1 <= len(scope) <= 100 or not scope.strip():
            raise ValueError("nonempty account scope is required")

    def _email(self, source_record_id: int, account_scope: str):
        source = self.session.get(SourceRecord, source_record_id)
        if (source is None or source.source_type != "email_message"
                or source.source_system_scope != account_scope
                or self.session.scalar(select(EmailMessage.id).where(EmailMessage.source_record_id == source_record_id)) is None):
            raise ValueError("source must be a logical email in the same account")
        return source

    def _conversation(self, conversation_id: int, account_scope: str, *, active=False):
        record = self.session.get(Conversation, conversation_id)
        if (record is None or record.legacy_status != "resolved"
                or record.account_scope != account_scope):
            raise ValueError("conversation must be resolved in the same account")
        try:
            key = UUID(record.stable_key)
            if key.version != 4 or str(key) != record.stable_key:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise ValueError("conversation has invalid stable key") from None
        if active and record.superseded_at is not None:
            raise ValueError("conversation is already superseded")
        return record

    def current_membership(self, account_scope: str, source_record_id: int):
        self._require_scope(account_scope)
        self._email(source_record_id, account_scope)
        return self.session.scalar(select(ConversationMembership).where(ConversationMembership.source_record_id == source_record_id))

    def conversations_for_account(self, account_scope: str):
        self._require_scope(account_scope)
        return tuple(self.session.scalars(select(Conversation).where(
            Conversation.account_scope == account_scope, Conversation.legacy_status == "resolved"
        ).order_by(Conversation.id)))

    def load_account_thread_snapshot(self, account_scope: str) -> AccountThreadSnapshot:
        """Read the account's logical email corpus in the caller-owned transaction."""
        self._require_scope(account_scope)
        sources = self.session.scalars(select(SourceRecord).where(
            SourceRecord.source_type == "email_message",
            SourceRecord.source_system_scope == account_scope,
        ).order_by(SourceRecord.id)).all()
        if not sources:
            return AccountThreadSnapshot(account_scope, ())

        source_ids = tuple(source.id for source in sources)
        emails = self.session.scalars(select(EmailMessage).where(
            EmailMessage.source_record_id.in_(source_ids)
        ).order_by(EmailMessage.source_record_id, EmailMessage.id)).all()
        email_by_source = {}
        for email in emails:
            if email.source_record_id in email_by_source:
                raise ValueError("duplicate logical EmailMessage representation")
            email_by_source[email.source_record_id] = email

        eligible_ids = set()
        for source in sources:
            state, timestamp = source.retention_state, source.deleted_or_redacted_at
            if not ((state == "active" and timestamp is None)
                    or (state in {"deleted", "redacted"} and timestamp is not None)):
                raise ValueError("invalid email source retention state")
            if source.id not in email_by_source:
                raise ValueError("email source missing EmailMessage representation")
            if state == "active":
                eligible_ids.add(source.id)

        memberships = {}
        if eligible_ids:
            rows = self.session.scalars(select(ConversationMembership).where(
                ConversationMembership.source_record_id.in_(eligible_ids)
            ).order_by(ConversationMembership.source_record_id, ConversationMembership.id)).all()
            for membership in rows:
                if membership.source_record_id in memberships:
                    raise ValueError("duplicate current email membership")
                memberships[membership.source_record_id] = membership

        touched_ids = tuple(sorted({row.conversation_id for row in memberships.values()}))
        conversations = {}
        member_sets = {}
        member_details = {}
        if touched_ids:
            conversations = {row.id: row for row in self.session.scalars(
                select(Conversation).where(Conversation.id.in_(touched_ids)).order_by(Conversation.id)
            )}
            if len(conversations) != len(touched_ids):
                raise ValueError("current membership points to missing conversation")
            members = self.session.scalars(select(ConversationMembership).where(
                ConversationMembership.conversation_id.in_(touched_ids)
            ).order_by(ConversationMembership.conversation_id,
                       ConversationMembership.source_record_id, ConversationMembership.id)).all()
            member_source_ids = tuple(sorted({member.source_record_id for member in members}))
            member_sources = {row.id: row for row in self.session.scalars(
                select(SourceRecord).where(SourceRecord.id.in_(member_source_ids)).order_by(SourceRecord.id)
            )} if member_source_ids else {}
            if len(member_sources) != len(member_source_ids):
                raise ValueError("current membership points to missing source")
            for member in members:
                member_sets.setdefault(member.conversation_id, []).append(member.source_record_id)
                source_row = member_sources[member.source_record_id]
                member_details.setdefault(member.conversation_id, []).append(AccountThreadMember(
                    source_record_id=source_row.id,
                    source_type=source_row.source_type,
                    account_scope=source_row.source_system_scope,
                ))
            for conversation_id in touched_ids:
                ids = member_sets.get(conversation_id, [])
                if len(ids) != len(set(ids)) or not ids:
                    raise ValueError("inconsistent current conversation membership")
                member_sets[conversation_id] = tuple(ids)
                member_details[conversation_id] = tuple(member_details[conversation_id])
            for source_id, membership in memberships.items():
                if source_id not in member_sets[membership.conversation_id]:
                    raise ValueError("inconsistent current conversation membership")

        result = []
        for source in sources:
            eligible = source.id in eligible_ids
            email = email_by_source[source.id]
            membership = memberships.get(source.id)
            conversation = conversations[membership.conversation_id] if membership else None
            result.append(AccountThreadSource(
                source_record_id=source.id,
                account_scope=account_scope,
                retention_state=source.retention_state,
                deleted_or_redacted_at=source.deleted_or_redacted_at,
                eligible=eligible,
                normalized_message_id=email.normalized_message_id if eligible else None,
                in_reply_to=email.in_reply_to if eligible else None,
                references_header=email.references_header if eligible else None,
                subject=email.subject if eligible else None,
                current_conversation_id=membership.conversation_id if membership else None,
                conversation_account_scope=conversation.account_scope if conversation else None,
                conversation_legacy_status=conversation.legacy_status if conversation else None,
                conversation_superseded_at=conversation.superseded_at if conversation else None,
                full_current_member_ids=member_sets[membership.conversation_id] if membership else (),
                full_current_members=member_details[membership.conversation_id] if membership else (),
            ))
        return AccountThreadSnapshot(account_scope, tuple(result))

    def create_resolved_conversation(self, account_scope: str, provenance: str):
        self._require_scope(account_scope)
        if not isinstance(provenance, str) or not 1 <= len(provenance) <= 255:
            raise ValueError("bounded provenance is required")
        stable_key = str(uuid4())
        while self.session.scalar(select(Conversation.id).where(Conversation.stable_key == stable_key)) is not None:
            stable_key = str(uuid4())
        record = Conversation(account_scope=account_scope, stable_key=stable_key,
                              legacy_status="resolved", provenance=provenance)
        self.session.add(record)
        self.session.flush()
        return record

    def append_evidence(self, *, account_scope, source_record_id, header_kind, ordinal,
                        parse_status, canonical_token, token_digest, normalization_version,
                        source_revision, replay_key=None):
        self._require_scope(account_scope)
        self._email(source_record_id, account_scope)
        self._require_hex(token_digest, "token_digest")
        self._require_hex(source_revision, "source_revision")
        if header_kind not in self._KINDS or not isinstance(ordinal, int) or ordinal < 0:
            raise ValueError("invalid header kind or ordinal")
        if not isinstance(normalization_version, int) or normalization_version <= 0:
            raise ValueError("invalid normalization version")
        if not ((parse_status == "valid" and isinstance(canonical_token, str)
                 and 1 <= len(canonical_token) <= 998 and canonical_token == canonical_token.lower())
                or (parse_status == "malformed" and canonical_token is None)):
            raise ValueError("invalid bounded canonical token/parse status")
        if parse_status == "valid" and sha256(canonical_token.encode("utf-8")).hexdigest() != token_digest:
            raise ValueError("canonical token digest mismatch")
        email = self.session.scalar(select(EmailMessage).where(EmailMessage.source_record_id == source_record_id))
        current_revision = self._digest("3d1/source-revision/v1", source_record_id,
            email.normalized_message_id, email.in_reply_to, email.references_header)
        if source_revision != current_revision:
            raise ValueError("source headers changed since evidence snapshot")
        computed = self._digest("3d1/evidence/v1", account_scope, source_record_id,
                                source_revision, normalization_version, header_kind,
                                ordinal, parse_status, token_digest)
        if replay_key is not None and replay_key != computed:
            raise ValueError("evidence replay key mismatch")
        existing = self.session.scalar(select(ThreadEvidence).where(ThreadEvidence.replay_key == computed))
        values = dict(account_scope=account_scope, source_record_id=source_record_id,
                      header_kind=header_kind, ordinal=ordinal, parse_status=parse_status,
                      canonical_token=canonical_token, token_digest=token_digest,
                      normalization_version=normalization_version, source_revision=source_revision)
        if existing is not None:
            if any(getattr(existing, name) != value for name, value in values.items()):
                raise ValueError("evidence replay key payload conflict")
            return existing
        if self.session.scalar(select(ThreadEvidence.id).where(
            ThreadEvidence.source_record_id == source_record_id,
            ThreadEvidence.source_revision == source_revision,
            ThreadEvidence.normalization_version == normalization_version,
            ThreadEvidence.header_kind == header_kind, ThreadEvidence.ordinal == ordinal
        )) is not None:
            raise ValueError("different evidence already occupies this header position")
        record = ThreadEvidence(**values, replay_key=computed)
        self.session.add(record)
        self.session.flush()
        return record

    def evidence_for_source(self, account_scope, source_record_id):
        self._email(source_record_id, account_scope)
        return tuple(self.session.scalars(select(ThreadEvidence).where(
            ThreadEvidence.account_scope == account_scope,
            ThreadEvidence.source_record_id == source_record_id
        ).order_by(ThreadEvidence.created_at, ThreadEvidence.id)))

    def append_decision(self, *, evidence_id, reconstruction_key, outcome,
                        target_source_record_id=None, replay_key=None):
        evidence = self.session.get(ThreadEvidence, evidence_id)
        if evidence is None or outcome not in self._OUTCOMES:
            raise ValueError("unknown evidence or decision outcome")
        self._require_hex(reconstruction_key, "reconstruction_key")
        accepted = outcome in {"accepted_direct_parent", "accepted_ancestor"}
        if accepted != (target_source_record_id is not None):
            raise ValueError("target is required only for accepted edges")
        if accepted:
            self._email(target_source_record_id, evidence.account_scope)
            if target_source_record_id == evidence.source_record_id:
                raise ValueError("self parent edge is prohibited")
            edges = self.session.execute(
                select(ThreadEvidence.source_record_id, ThreadEvidenceDecision.target_source_record_id)
                .join(ThreadEvidenceDecision, ThreadEvidenceDecision.evidence_id == ThreadEvidence.id)
                .where(ThreadEvidence.account_scope == evidence.account_scope,
                       ThreadEvidenceDecision.reconstruction_key == reconstruction_key,
                       ThreadEvidenceDecision.outcome.in_(("accepted_direct_parent", "accepted_ancestor")))
            ).all()
            graph = {}
            for source_id, target_id in edges:
                graph.setdefault(source_id, set()).add(target_id)
            pending = [target_source_record_id]
            seen = set()
            while pending:
                current = pending.pop()
                if current == evidence.source_record_id:
                    raise ValueError("parent cycle is prohibited")
                if current not in seen:
                    seen.add(current)
                    pending.extend(graph.get(current, ()))
        computed = self._digest("3d1/decision/v1", evidence.replay_key, reconstruction_key,
                                outcome, target_source_record_id)
        if replay_key is not None and replay_key != computed:
            raise ValueError("decision replay key mismatch")
        existing = self.session.scalar(select(ThreadEvidenceDecision).where(ThreadEvidenceDecision.replay_key == computed))
        if existing is not None:
            if (existing.evidence_id, existing.reconstruction_key, existing.outcome,
                existing.target_source_record_id) != (evidence_id, reconstruction_key, outcome, target_source_record_id):
                raise ValueError("decision replay key payload conflict")
            return existing
        if self.session.scalar(select(ThreadEvidenceDecision.id).where(
            ThreadEvidenceDecision.evidence_id == evidence_id,
            ThreadEvidenceDecision.reconstruction_key == reconstruction_key
        )) is not None:
            raise ValueError("evidence already has a decision in this reconstruction")
        record = ThreadEvidenceDecision(evidence_id=evidence_id, reconstruction_key=reconstruction_key,
                                        outcome=outcome, target_source_record_id=target_source_record_id,
                                        replay_key=computed)
        self.session.add(record)
        self.session.flush()
        return record

    def decisions_for_reconstruction(self, reconstruction_key):
        self._require_hex(reconstruction_key, "reconstruction_key")
        return tuple(self.session.scalars(select(ThreadEvidenceDecision).where(
            ThreadEvidenceDecision.reconstruction_key == reconstruction_key
        ).order_by(ThreadEvidenceDecision.id)))

    def assign_current_membership(self, *, account_scope, source_record_id, new_conversation_id,
                                  reason, reconstruction_key, evidence_type, evidence_reference,
                                  expected_old_conversation_id=None, evidence_decision_id=None,
                                  replay_key=None):
        self._require_scope(account_scope)
        self._email(source_record_id, account_scope)
        new = self._conversation(new_conversation_id, account_scope)
        self._require_hex(reconstruction_key, "reconstruction_key")
        if reason not in self._REASONS:
            raise ValueError("invalid assignment reason")
        if evidence_type not in {"singleton", "thread_decision", "legacy_assignment"}:
            raise ValueError("invalid bounded membership evidence summary")
        if (not isinstance(evidence_reference, str) or len(evidence_reference) > 255
                or not re.fullmatch(r"(?:source|decision):[0-9]+", evidence_reference)):
            raise ValueError("membership evidence must be a local bounded reference")
        old = (self._conversation(expected_old_conversation_id, account_scope)
               if expected_old_conversation_id is not None else None)
        if (reason == "initial_assignment") != (old is None) or (old is not None and old.id == new.id):
            raise ValueError("old/new assignment reason mismatch")
        if evidence_decision_id is not None:
            decision = self.session.get(ThreadEvidenceDecision, evidence_decision_id)
            evidence = self.session.get(ThreadEvidence, decision.evidence_id) if decision else None
            if (decision is None or evidence.account_scope != account_scope
                    or evidence.source_record_id != source_record_id
                    or decision.reconstruction_key != reconstruction_key):
                raise ValueError("membership decision is not scoped to source/reconstruction")
        computed = self._digest("3d1/membership/v1", account_scope, source_record_id,
                                old.stable_key if old else None, new.stable_key, reason, reconstruction_key)
        if replay_key is not None and replay_key != computed:
            raise ValueError("membership replay key mismatch")
        current = self.session.scalar(select(ConversationMembership).where(
            ConversationMembership.source_record_id == source_record_id))
        history = self.session.scalar(select(ThreadMembershipChange).where(ThreadMembershipChange.replay_key == computed))
        if history is not None:
            if ((history.source_record_id, history.account_scope, history.old_conversation_id,
                 history.new_conversation_id, history.reason, history.reconstruction_key,
                 history.evidence_decision_id)
                != (source_record_id, account_scope, old.id if old else None, new.id,
                    reason, reconstruction_key, evidence_decision_id)
                    or current is None
                    or (current.conversation_id == new.id and
                        (current.evidence_type != evidence_type or current.evidence_reference != evidence_reference))):
                raise ValueError("membership replay key payload conflict")
            return current
        if new.superseded_at is not None:
            raise ValueError("cannot assign to an already superseded conversation")
        if (current.conversation_id if current else None) != expected_old_conversation_id:
            raise ValueError("stale current membership")
        if current is None:
            current = ConversationMembership(source_record_id=source_record_id,
                                             conversation_id=new.id, evidence_type=evidence_type,
                                             evidence_reference=evidence_reference)
            self.session.add(current)
        else:
            current.conversation_id = new.id
            current.evidence_type = evidence_type
            current.evidence_reference = evidence_reference
        self.session.add(ThreadMembershipChange(source_record_id=source_record_id,
                         account_scope=account_scope, old_conversation_id=old.id if old else None,
                         new_conversation_id=new.id, reason=reason,
                         evidence_decision_id=evidence_decision_id,
                         reconstruction_key=reconstruction_key, replay_key=computed))
        self.session.flush()
        return current

    def membership_history(self, account_scope, source_record_id):
        self._email(source_record_id, account_scope)
        return tuple(self.session.scalars(select(ThreadMembershipChange).where(
            ThreadMembershipChange.source_record_id == source_record_id,
            ThreadMembershipChange.account_scope == account_scope
        ).order_by(ThreadMembershipChange.created_at, ThreadMembershipChange.id)))

    def record_lineage_operation(self, *, account_scope, kind, predecessor_ids,
                                 successor_ids, reconstruction_key, provenance="thread_reconstruction",
                                 replay_key=None):
        self._require_scope(account_scope)
        self._require_hex(reconstruction_key, "reconstruction_key")
        predecessors = set(predecessor_ids)
        successors = set(successor_ids)
        required = {"merge": (2, 1), "split": (1, 2), "repartition": (2, 2), "correction": (1, 1)}
        if (kind not in required or len(predecessors) != len(predecessor_ids)
                or len(successors) != len(successor_ids) or predecessors & successors
                or len(predecessors) < required[kind][0] or len(successors) < required[kind][1]
                or (kind == "merge" and len(successors) != 1)
                or (kind == "split" and len(predecessors) != 1)
                or (kind == "correction" and (len(predecessors) != 1 or len(successors) != 1))):
            raise ValueError("invalid lineage operation shape")
        if not isinstance(provenance, str) or not 1 <= len(provenance) <= 50:
            raise ValueError("bounded lineage provenance required")
        old = {id_: self._conversation(id_, account_scope) for id_ in predecessors}
        new = {id_: self._conversation(id_, account_scope, active=True) for id_ in successors}
        computed = self._digest("3d1/lineage/v1", account_scope, reconstruction_key, kind,
                                len(old), *sorted(record.stable_key for record in old.values()),
                                len(new), *sorted(record.stable_key for record in new.values()))
        if replay_key is not None and replay_key != computed:
            raise ValueError("lineage replay key mismatch")
        existing = self.session.scalar(select(ThreadLineageOperation).where(ThreadLineageOperation.replay_key == computed))
        if existing is not None:
            edges = set(self.session.execute(select(ThreadLineageEdge.predecessor_conversation_id,
                ThreadLineageEdge.successor_conversation_id).where(ThreadLineageEdge.operation_id == existing.id)))
            if (existing.account_scope, existing.kind, existing.reconstruction_key, existing.provenance) != (account_scope, kind, reconstruction_key, provenance) or edges != {(p, s) for p in predecessors for s in successors}:
                raise ValueError("lineage replay key payload conflict")
            return existing
        if any(record.superseded_at is not None for record in old.values()):
            raise ValueError("predecessor already superseded")
        graph = {}
        for p, s in self.session.execute(select(ThreadLineageEdge.predecessor_conversation_id,
                                                ThreadLineageEdge.successor_conversation_id)):
            graph.setdefault(p, set()).add(s)
        for p in predecessors:
            for s in successors:
                pending = [s]
                seen = set()
                while pending:
                    current = pending.pop()
                    if current == p:
                        raise ValueError("lineage cycle is prohibited")
                    if current not in seen:
                        seen.add(current)
                        pending.extend(graph.get(current, ()))
                graph.setdefault(p, set()).add(s)
        record = ThreadLineageOperation(account_scope=account_scope, kind=kind,
                reconstruction_key=reconstruction_key, replay_key=computed, provenance=provenance)
        self.session.add(record)
        self.session.flush()
        for p in predecessors:
            for s in successors:
                self.session.add(ThreadLineageEdge(operation_id=record.id,
                    predecessor_conversation_id=p, successor_conversation_id=s))
        when = datetime.now(timezone.utc)
        for predecessor in old.values():
            predecessor.superseded_at = when
        self.session.flush()
        return record

    def lineage_from(self, conversation_id):
        return tuple(self.session.scalars(select(ThreadLineageEdge).where(
            ThreadLineageEdge.predecessor_conversation_id == conversation_id
        ).order_by(ThreadLineageEdge.id)))

    def lineage_to(self, conversation_id):
        return tuple(self.session.scalars(select(ThreadLineageEdge).where(
            ThreadLineageEdge.successor_conversation_id == conversation_id
        ).order_by(ThreadLineageEdge.id)))
