from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def _model(name, table, *columns, table_args=()):
    attrs = {"__tablename__": table, "id": Column(Integer, primary_key=True), "created_at": Column(DateTime(timezone=True), default=utcnow, nullable=False)}
    attrs.update({column.name: column for column in columns})
    if table_args:
        attrs["__table_args__"] = table_args
    return type(name, (Base,), attrs)


ConfigurationReference = _model("ConfigurationReference", "configuration_reference", Column("scope", String(100), unique=True, nullable=False), Column("reference_kind", String(100), nullable=False), Column("reference_value", String(255), nullable=False))
SourceRecord = _model("SourceRecord", "source_record", Column("source_type", String(50), nullable=False), Column("source_system_scope", String(100), nullable=False), Column("stable_external_id", String(255)), Column("source_timestamp", DateTime(timezone=True)), Column("ingested_at", DateTime(timezone=True), default=utcnow, nullable=False), Column("retention_state", String(30), default="active", nullable=False), Column("deleted_or_redacted_at", DateTime(timezone=True)), Column("redaction_reason", String(255)), Column("manual_entry", Boolean, default=False, nullable=False), Column("provenance", String(255), default="system", nullable=False), table_args=(UniqueConstraint("source_system_scope", "stable_external_id"),))
SourceObservation = _model("SourceObservation", "source_observation", Column("source_record_id", Integer, ForeignKey("source_record.id"), nullable=False), Column("observed_at", DateTime(timezone=True), default=utcnow, nullable=False), Column("source_version_marker", String(255)), Column("observed_state", String(30), nullable=False), Column("outcome", String(50), nullable=False), Column("provenance", String(255), default="system", nullable=False), table_args=(UniqueConstraint("source_record_id", "source_version_marker"),))
SynchronizationCheckpoint = _model("SynchronizationCheckpoint", "synchronization_checkpoint", Column("source_system_scope", String(100), unique=True, nullable=False), Column("checkpoint_marker", String(255)), Column("last_success_at", DateTime(timezone=True)), Column("last_outcome", String(50), default="pending", nullable=False), Column("updated_at", DateTime(timezone=True), default=utcnow, nullable=False))
IdempotencyIdentity = _model("IdempotencyIdentity", "idempotency_identity", Column("operation_kind", String(100), nullable=False), Column("scope", String(100), nullable=False), Column("identity_key", String(255), nullable=False), Column("source_record_id", Integer, ForeignKey("source_record.id")), Column("target_reference", String(255)), Column("resolved_at", DateTime(timezone=True)), table_args=(UniqueConstraint("operation_kind", "scope", "identity_key"),))
_HEX64 = "length({0}) = 64 AND {0} NOT GLOB '*[^0-9a-f]*'"
Conversation = _model(
    "Conversation", "conversation",
    Column("provenance", String(255), default="system", nullable=False),
    Column("superseded_at", DateTime(timezone=True)),
    Column("account_scope", String(100)),
    Column("stable_key", String(36), nullable=False),
    Column("legacy_status", String(20), nullable=False),
    table_args=(
        CheckConstraint("(legacy_status = 'resolved' AND account_scope IS NOT NULL AND length(account_scope) BETWEEN 1 AND 100) OR (legacy_status = 'legacy_unresolved' AND account_scope IS NULL)", name="ck_conversation_scope_status"),
        CheckConstraint("length(stable_key) = 36 AND stable_key = lower(stable_key) AND substr(stable_key, 9, 1) = '-' AND substr(stable_key, 14, 1) = '-' AND substr(stable_key, 15, 1) = '4' AND substr(stable_key, 19, 1) = '-' AND substr(stable_key, 24, 1) = '-' AND stable_key NOT GLOB '*[^0-9a-f-]*'", name="ck_conversation_stable_key"),
        UniqueConstraint("account_scope", "stable_key", name="uq_conversation_scope_stable_key"),
        Index("ix_conversation_scope_status_superseded", "account_scope", "legacy_status", "superseded_at"),
    ),
)
ConversationMembership = _model("ConversationMembership", "conversation_membership", Column("conversation_id", Integer, ForeignKey("conversation.id"), nullable=False), Column("source_record_id", Integer, ForeignKey("source_record.id"), unique=True, nullable=False), Column("evidence_type", String(50), nullable=False), Column("evidence_reference", String(255), nullable=False), table_args=(Index("ix_conversation_membership_conversation_id", "conversation_id"),))

ThreadEvidence = _model(
    "ThreadEvidence", "thread_evidence",
    Column("account_scope", String(100), nullable=False),
    Column("source_record_id", Integer, ForeignKey("source_record.id", ondelete="RESTRICT"), nullable=False),
    Column("header_kind", String(20), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("parse_status", String(12), nullable=False),
    Column("canonical_token", String(998)),
    Column("token_digest", String(64), nullable=False),
    Column("normalization_version", Integer, nullable=False),
    Column("source_revision", String(64), nullable=False),
    Column("replay_key", String(64), nullable=False),
    table_args=(
        CheckConstraint("header_kind IN ('message_id', 'in_reply_to', 'references')", name="ck_thread_evidence_kind"),
        CheckConstraint("parse_status IN ('valid', 'malformed')", name="ck_thread_evidence_parse_status"),
        CheckConstraint("(parse_status = 'valid' AND canonical_token IS NOT NULL AND length(canonical_token) BETWEEN 1 AND 998) OR (parse_status = 'malformed' AND canonical_token IS NULL)", name="ck_thread_evidence_token_shape"),
        CheckConstraint("ordinal >= 0 AND normalization_version > 0", name="ck_thread_evidence_ordinal_version"),
        CheckConstraint(" AND ".join(_HEX64.format(name) for name in ("token_digest", "source_revision", "replay_key")), name="ck_thread_evidence_digests"),
        CheckConstraint("length(account_scope) BETWEEN 1 AND 100", name="ck_thread_evidence_scope"),
        UniqueConstraint("replay_key", name="uq_thread_evidence_replay"),
        UniqueConstraint("source_record_id", "source_revision", "normalization_version", "header_kind", "ordinal", name="uq_thread_evidence_source_revision_ordinal"),
        Index("ix_thread_evidence_scope_token_kind", "account_scope", "token_digest", "header_kind"),
        Index("ix_thread_evidence_source_revision", "source_record_id", "source_revision"),
    ),
)

ThreadEvidenceDecision = _model(
    "ThreadEvidenceDecision", "thread_evidence_decision",
    Column("evidence_id", Integer, ForeignKey("thread_evidence.id", ondelete="RESTRICT"), nullable=False),
    Column("target_source_record_id", Integer, ForeignKey("source_record.id", ondelete="RESTRICT")),
    Column("reconstruction_key", String(64), nullable=False),
    Column("outcome", String(32), nullable=False),
    Column("replay_key", String(64), nullable=False),
    table_args=(
        CheckConstraint("outcome IN ('identity_observed', 'accepted_direct_parent', 'accepted_ancestor', 'unresolved_external', 'duplicate_target', 'malformed', 'multiple_in_reply_to', 'self_link', 'cycle_rejected', 'conflict', 'not_linking')", name="ck_thread_decision_outcome"),
        CheckConstraint("(outcome IN ('accepted_direct_parent', 'accepted_ancestor') AND target_source_record_id IS NOT NULL) OR (outcome NOT IN ('accepted_direct_parent', 'accepted_ancestor') AND target_source_record_id IS NULL)", name="ck_thread_decision_target"),
        CheckConstraint(" AND ".join(_HEX64.format(name) for name in ("reconstruction_key", "replay_key")), name="ck_thread_decision_keys"),
        UniqueConstraint("evidence_id", "reconstruction_key", name="uq_thread_decision_evidence_reconstruction"),
        UniqueConstraint("replay_key", name="uq_thread_decision_replay"),
        Index("ix_thread_decision_target", "target_source_record_id"),
        Index("ix_thread_decision_reconstruction_outcome", "reconstruction_key", "outcome"),
    ),
)

ThreadMembershipChange = _model(
    "ThreadMembershipChange", "thread_membership_change",
    Column("source_record_id", Integer, ForeignKey("source_record.id", ondelete="RESTRICT"), nullable=False),
    Column("account_scope", String(100)),
    Column("old_conversation_id", Integer, ForeignKey("conversation.id", ondelete="RESTRICT")),
    Column("new_conversation_id", Integer, ForeignKey("conversation.id", ondelete="RESTRICT"), nullable=False),
    Column("reason", String(32), nullable=False),
    Column("evidence_decision_id", Integer, ForeignKey("thread_evidence_decision.id", ondelete="RESTRICT")),
    Column("reconstruction_key", String(64)),
    Column("replay_key", String(64), nullable=False),
    table_args=(
        CheckConstraint("reason IN ('legacy_assignment_baseline', 'initial_assignment', 'merge', 'split', 'repartition', 'correction')", name="ck_thread_membership_change_reason"),
        CheckConstraint("(reason IN ('legacy_assignment_baseline', 'initial_assignment') AND old_conversation_id IS NULL) OR (reason IN ('merge', 'split', 'repartition', 'correction') AND old_conversation_id IS NOT NULL AND old_conversation_id != new_conversation_id)", name="ck_thread_membership_change_old_new"),
        CheckConstraint("(reason = 'legacy_assignment_baseline' AND reconstruction_key IS NULL AND evidence_decision_id IS NULL) OR (reason != 'legacy_assignment_baseline' AND account_scope IS NOT NULL AND length(account_scope) BETWEEN 1 AND 100 AND reconstruction_key IS NOT NULL)", name="ck_thread_membership_change_baseline"),
        CheckConstraint(_HEX64.format("replay_key") + " AND (reconstruction_key IS NULL OR (" + _HEX64.format("reconstruction_key") + "))", name="ck_thread_membership_change_keys"),
        UniqueConstraint("replay_key", name="uq_thread_membership_change_replay"),
        Index("ix_thread_membership_change_source_time", "source_record_id", "created_at", "id"),
        Index("ix_thread_membership_change_old", "old_conversation_id"),
        Index("ix_thread_membership_change_new", "new_conversation_id"),
        Index("ix_thread_membership_change_scope_reconstruction", "account_scope", "reconstruction_key"),
    ),
)

ThreadLineageOperation = _model(
    "ThreadLineageOperation", "thread_lineage_operation",
    Column("account_scope", String(100), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("reconstruction_key", String(64), nullable=False),
    Column("replay_key", String(64), nullable=False),
    Column("provenance", String(50), nullable=False),
    table_args=(
        CheckConstraint("kind IN ('merge', 'split', 'repartition', 'correction')", name="ck_thread_lineage_operation_kind"),
        CheckConstraint(_HEX64.format("reconstruction_key") + " AND " + _HEX64.format("replay_key"), name="ck_thread_lineage_operation_keys"),
        CheckConstraint("length(account_scope) BETWEEN 1 AND 100 AND length(provenance) BETWEEN 1 AND 50", name="ck_thread_lineage_operation_scope_provenance"),
        UniqueConstraint("replay_key", name="uq_thread_lineage_operation_replay"),
        Index("ix_thread_lineage_operation_scope_time", "account_scope", "created_at", "id"),
    ),
)

ThreadLineageEdge = _model(
    "ThreadLineageEdge", "thread_lineage_edge",
    Column("operation_id", Integer, ForeignKey("thread_lineage_operation.id", ondelete="RESTRICT"), nullable=False),
    Column("predecessor_conversation_id", Integer, ForeignKey("conversation.id", ondelete="RESTRICT"), nullable=False),
    Column("successor_conversation_id", Integer, ForeignKey("conversation.id", ondelete="RESTRICT"), nullable=False),
    table_args=(
        CheckConstraint("predecessor_conversation_id != successor_conversation_id", name="ck_thread_lineage_edge_nonself"),
        UniqueConstraint("operation_id", "predecessor_conversation_id", "successor_conversation_id", name="uq_thread_lineage_edge_pair"),
        Index("ix_thread_lineage_edge_predecessor", "predecessor_conversation_id"),
        Index("ix_thread_lineage_edge_successor", "successor_conversation_id"),
    ),
)
ManualNote = _model("ManualNote", "manual_note", Column("source_record_id", Integer, ForeignKey("source_record.id"), unique=True, nullable=False), Column("original_text", Text, nullable=False), Column("entered_at", DateTime(timezone=True), default=utcnow, nullable=False), Column("provenance", String(255), default="manual", nullable=False))
WhatsAppImport = _model("WhatsAppImport", "whatsapp_import", Column("source_record_id", Integer, ForeignKey("source_record.id"), unique=True, nullable=False), Column("original_text", Text, nullable=False), Column("pasted_at", DateTime(timezone=True), default=utcnow, nullable=False), Column("provenance", String(255), default="manual", nullable=False))
CalendarEventRepresentation = _model("CalendarEventRepresentation", "calendar_event_representation", Column("source_record_id", Integer, ForeignKey("source_record.id"), unique=True, nullable=False), Column("calendar_event_id", String(255), nullable=False), Column("starts_at", DateTime(timezone=True)), Column("ends_at", DateTime(timezone=True)), Column("current_state", String(30), default="active", nullable=False), Column("updated_at", DateTime(timezone=True), default=utcnow, nullable=False))
Activity = _model("Activity", "activity", Column("activity_type", String(50), nullable=False), Column("occurred_at", DateTime(timezone=True)), Column("description_reference", String(255)), Column("provenance", String(255), default="system", nullable=False))
ActivitySourceLink = _model("ActivitySourceLink", "activity_source_link", Column("activity_id", Integer, ForeignKey("activity.id"), nullable=False), Column("source_record_id", Integer, ForeignKey("source_record.id"), nullable=False), Column("link_purpose", String(100), nullable=False), table_args=(UniqueConstraint("activity_id", "source_record_id", "link_purpose"),))
CRMReference = _model("CRMReference", "crm_reference", Column("entity_type", String(50), nullable=False), Column("external_id", String(255), nullable=False), Column("display_reference", String(255)), Column("provenance", String(255), default="system", nullable=False), table_args=(UniqueConstraint("entity_type", "external_id"),))
CRMContextLink = _model("CRMContextLink", "crm_context_link", Column("crm_reference_id", Integer, ForeignKey("crm_reference.id"), nullable=False), Column("assistant_record_type", String(50), nullable=False), Column("assistant_record_id", Integer, nullable=False), Column("relationship_purpose", String(100), nullable=False), Column("confirmation_state", String(20), default="ambiguous", nullable=False), Column("confirmed_at", DateTime(timezone=True)), Column("provenance", String(255), default="system", nullable=False), table_args=(CheckConstraint("confirmation_state IN ('ambiguous', 'proposed', 'confirmed')"), CheckConstraint("(confirmation_state = 'confirmed' AND confirmed_at IS NOT NULL) OR (confirmation_state != 'confirmed' AND confirmed_at IS NULL)")))
IdentityLink = _model("IdentityLink", "identity_link", Column("identity_type", String(50), nullable=False), Column("identity_value", String(255), nullable=False), Column("crm_reference_id", Integer, ForeignKey("crm_reference.id"), nullable=False), Column("status", String(30), default="confirmed", nullable=False), Column("confirmed_at", DateTime(timezone=True), default=utcnow, nullable=False), Column("provenance", String(255), default="user", nullable=False), Column("superseded_at", DateTime(timezone=True)), table_args=(Index("uq_identity_link_active_confirmed", "identity_type", "identity_value", unique=True, sqlite_where=text("status = 'confirmed' AND superseded_at IS NULL")),))
IdentityLinkCorrection = _model("IdentityLinkCorrection", "identity_link_correction", Column("prior_identity_link_id", Integer, ForeignKey("identity_link.id"), unique=True, nullable=False), Column("replacement_identity_link_id", Integer, ForeignKey("identity_link.id"), nullable=False), Column("corrected_at", DateTime(timezone=True), default=utcnow, nullable=False), Column("provenance", String(255), default="user", nullable=False), table_args=(CheckConstraint("prior_identity_link_id != replacement_identity_link_id"),))
ExtractedFact = _model("ExtractedFact", "extracted_fact", Column("fact_type", String(100), nullable=False), Column("value_reference", String(255), nullable=False), Column("provenance", String(255), nullable=False), Column("superseded_at", DateTime(timezone=True)))
Inference = _model("Inference", "inference", Column("inference_type", String(100), nullable=False), Column("value_reference", String(255), nullable=False), Column("provenance", String(255), nullable=False), Column("confirmed_at", DateTime(timezone=True)))
Proposal = _model("Proposal", "proposal", Column("proposal_type", String(100), nullable=False), Column("value_reference", String(255), nullable=False), Column("provenance", String(255), nullable=False), Column("status", String(30), default="proposed", nullable=False))
FactSourceEvidence = _model("FactSourceEvidence", "fact_source_evidence", Column("extracted_fact_id", Integer, ForeignKey("extracted_fact.id"), nullable=False), Column("source_record_id", Integer, ForeignKey("source_record.id"), nullable=False), Column("evidence_reference", String(255), nullable=False), table_args=(UniqueConstraint("extracted_fact_id", "source_record_id", "evidence_reference"),))
InferenceSupport = _model("InferenceSupport", "inference_support", Column("inference_id", Integer, ForeignKey("inference.id"), nullable=False), Column("support_type", String(30), nullable=False), Column("support_id", Integer, nullable=False), table_args=(UniqueConstraint("inference_id", "support_type", "support_id"), CheckConstraint("support_type IN ('source', 'fact', 'inference')")))
ProposalSupport = _model("ProposalSupport", "proposal_support", Column("proposal_id", Integer, ForeignKey("proposal.id"), nullable=False), Column("support_type", String(30), nullable=False), Column("support_id", Integer, nullable=False), table_args=(UniqueConstraint("proposal_id", "support_type", "support_id"), CheckConstraint("support_type IN ('source', 'fact', 'inference', 'proposal')")))
AuditEvent = _model("AuditEvent", "audit_event", Column("event_type", String(100), nullable=False), Column("affected_record_type", String(50), nullable=False), Column("affected_record_id", Integer, nullable=False), Column("actor_or_source", String(100), nullable=False), Column("occurred_at", DateTime(timezone=True), default=utcnow, nullable=False), Column("provenance", String(255), nullable=False), Column("outcome_reference", String(255)), Column("failure_code", String(100)))


Task = _model(
    "Task",
    "task",
    Column("title", String(255), nullable=False),
    Column("state", String(20), default="proposed", nullable=False),
    Column("due_at", DateTime(timezone=True)),
    Column("completion_reference", String(255)),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("state IN ('proposed', 'pending', 'completed', 'cancelled')"),
    ),
)

Commitment = _model(
    "Commitment",
    "commitment",
    Column("description", String(255), nullable=False),
    Column("state", String(20), default="detected", nullable=False),
    Column("due_at", DateTime(timezone=True)),
    Column("resolution_reference", String(255)),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("state IN ('detected', 'confirmed', 'fulfilled', 'overdue', 'cancelled')"),
        Index("ix_commitment_due_state", "state", "due_at"),
    ),
)

Question = _model(
    "Question",
    "question",
    Column("question_text", Text, nullable=False),
    Column("state", String(20), default="detected", nullable=False),
    Column("answer_reference", String(255)),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("state IN ('detected', 'open', 'answered', 'dismissed')"),
    ),
)

NextStep = _model(
    "NextStep",
    "next_step",
    Column("description", String(255), nullable=False),
    Column("state", String(20), default="proposed", nullable=False),
    Column("target_at", DateTime(timezone=True)),
    Column("completion_reference", String(255)),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("state IN ('proposed', 'planned', 'completed', 'cancelled')"),
    ),
)

Alert = _model(
    "Alert",
    "alert",
    Column("alert_type", String(100), nullable=False),
    Column("target_type", String(50), nullable=False),
    Column("target_id", Integer, nullable=False),
    Column("condition_key", String(255), nullable=False),
    Column("state", String(20), default="active", nullable=False),
    Column("priority", String(20)),
    Column("resolved_at", DateTime(timezone=True)),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("state IN ('active', 'resolved', 'dismissed')"),
        Index(
            "uq_alert_active_condition",
            "alert_type",
            "target_type",
            "target_id",
            "condition_key",
            unique=True,
            sqlite_where=text("state = 'active'"),
        ),
    ),
)


FollowUpPreference = _model(
    "FollowUpPreference",
    "follow_up_preference",
    Column("scope_type", String(30), nullable=False),
    Column("scope_reference", String(255)),
    Column("classification", String(50), nullable=False),
    Column("inactivity_days", Integer),
    Column("explicit_future_date", DateTime(timezone=True)),
    Column("provenance", String(255), nullable=False),
    Column("updated_at", DateTime(timezone=True), default=utcnow, nullable=False),
    table_args=(
        CheckConstraint("inactivity_days IS NULL OR inactivity_days >= 0"),
        Index(
            "uq_follow_up_preference_scoped",
            "scope_type",
            "scope_reference",
            unique=True,
            sqlite_where=text("scope_reference IS NOT NULL"),
        ),
        Index(
            "uq_follow_up_preference_global",
            "scope_type",
            unique=True,
            sqlite_where=text("scope_reference IS NULL"),
        ),
        Index("ix_follow_up_preference_lookup", "scope_type", "scope_reference"),
    ),
)

FollowUpPreferenceHistory = _model(
    "FollowUpPreferenceHistory",
    "follow_up_preference_history",
    Column("follow_up_preference_id", Integer, ForeignKey("follow_up_preference.id"), nullable=False),
    Column("scope_type", String(30), nullable=False),
    Column("scope_reference", String(255)),
    Column("classification", String(50), nullable=False),
    Column("inactivity_days", Integer),
    Column("explicit_future_date", DateTime(timezone=True)),
    Column("changed_at", DateTime(timezone=True), default=utcnow, nullable=False),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("inactivity_days IS NULL OR inactivity_days >= 0"),
    ),
)

ActionProposal = _model(
    "ActionProposal",
    "action_proposal",
    Column("action_type", String(100), nullable=False),
    Column("target_type", String(50), nullable=False),
    Column("target_reference", String(255), nullable=False),
    Column("state", String(30), default="pending_approval", nullable=False),
    Column("idempotency_identity_id", Integer, ForeignKey("idempotency_identity.id"), unique=True, nullable=False),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("state IN ('pending_approval', 'approved', 'rejected', 'executed', 'error')"),
    ),
)

ApprovalDecision = _model(
    "ApprovalDecision",
    "approval_decision",
    Column("action_proposal_id", Integer, ForeignKey("action_proposal.id"), unique=True, nullable=False),
    Column("decision", String(20), nullable=False),
    Column("decided_at", DateTime(timezone=True), default=utcnow, nullable=False),
    Column("actor_reference", String(255), nullable=False),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("decision IN ('approved', 'rejected')"),
    ),
)

ExecutionResult = _model(
    "ExecutionResult",
    "execution_result",
    Column("action_proposal_id", Integer, ForeignKey("action_proposal.id"), nullable=False),
    Column("approval_decision_id", Integer, ForeignKey("approval_decision.id")),
    Column("attempted_at", DateTime(timezone=True), default=utcnow, nullable=False),
    Column("revalidation_reference", String(255), nullable=False),
    Column("outcome", String(30), nullable=False),
    Column("external_result_reference", String(255)),
    Column("failure_code", String(100)),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("outcome IN ('executed', 'error')"),
        Index("ix_execution_result_action_attempt", "action_proposal_id", "attempted_at"),
    ),
)

OperationalEvidenceLink = _model(
    "OperationalEvidenceLink",
    "operational_evidence_link",
    Column("operational_type", String(30), nullable=False),
    Column("operational_id", Integer, nullable=False),
    Column("evidence_type", String(30), nullable=False),
    Column("evidence_id", Integer),
    Column("evidence_reference", String(255)),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("operational_type IN ('task', 'commitment', 'question', 'next_step', 'alert', 'action_proposal')"),
        CheckConstraint("evidence_type IN ('source', 'fact', 'inference', 'proposal', 'user_confirmation')"),
        CheckConstraint("(evidence_type = 'user_confirmation' AND evidence_id IS NULL AND evidence_reference IS NOT NULL) OR (evidence_type != 'user_confirmation' AND evidence_id IS NOT NULL)"),
        UniqueConstraint("operational_type", "operational_id", "evidence_type", "evidence_id", "evidence_reference"),
    ),
)

EmailMessage = _model(
    "EmailMessage",
    "email_message",
    Column("source_record_id", Integer, ForeignKey("source_record.id"), unique=True, nullable=False),
    Column("normalized_message_id", String(998)),
    Column("sender_address", String(320)),
    Column("recipient_addresses", Text),
    Column("subject", String(998)),
    Column("sent_at", DateTime(timezone=True)),
    Column("received_at", DateTime(timezone=True)),
    Column("in_reply_to", String(998)),
    Column("references_header", Text),
    Column("normalized_body", Text),
    Column("body_size_bytes", Integer),
    Column("content_truncated", Boolean, default=False, nullable=False),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("body_size_bytes IS NULL OR body_size_bytes >= 0"),
    ),
)

IMAPMessageLocation = _model(
    "IMAPMessageLocation",
    "imap_message_location",
    Column("email_message_id", Integer, ForeignKey("email_message.id"), nullable=False),
    Column("account_scope", String(100), nullable=False),
    Column("folder_name", String(255), nullable=False),
    Column("uidvalidity", Integer, nullable=False),
    Column("uid", Integer, nullable=False),
    Column("location_state", String(20), default="active", nullable=False),
    Column("last_observed_at", DateTime(timezone=True), nullable=False),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("location_state IN ('active', 'unavailable')"),
        CheckConstraint("uidvalidity >= 0"),
        CheckConstraint("uid > 0"),
        UniqueConstraint("account_scope", "folder_name", "uidvalidity", "uid"),
        Index("ix_imap_message_location_lookup", "account_scope", "folder_name", "uidvalidity", "uid"),
    ),
)

EmailAttachmentMetadata = _model(
    "EmailAttachmentMetadata",
    "email_attachment_metadata",
    Column("email_message_id", Integer, ForeignKey("email_message.id"), nullable=False),
    Column("part_index", Integer, nullable=False),
    Column("filename", String(255)),
    Column("media_type", String(255)),
    Column("byte_size", Integer),
    Column("content_id", String(998)),
    Column("disposition", String(100)),
    Column("provenance", String(255), nullable=False),
    table_args=(
        CheckConstraint("part_index >= 0"),
        CheckConstraint("byte_size IS NULL OR byte_size >= 0"),
        UniqueConstraint("email_message_id", "part_index"),
    ),
)
