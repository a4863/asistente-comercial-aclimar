"""phase 2a persistent foundation"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _created_at():
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)


def upgrade():
    op.create_table(
        "configuration_reference",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("scope", sa.String(length=100), nullable=False),
        sa.Column("reference_kind", sa.String(length=100), nullable=False),
        sa.Column("reference_value", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("scope", name="uq_configuration_reference_scope"),
    )

    op.create_table(
        "source_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_system_scope", sa.String(length=100), nullable=False),
        sa.Column("stable_external_id", sa.String(length=255), nullable=True),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_state", sa.String(length=30), nullable=False),
        sa.Column("deleted_or_redacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redaction_reason", sa.String(length=255), nullable=True),
        sa.Column("manual_entry", sa.Boolean(), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "source_system_scope",
            "stable_external_id",
            name="uq_source_record_scope_external_id",
        ),
    )

    op.create_table(
        "synchronization_checkpoint",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("source_system_scope", sa.String(length=100), nullable=False),
        sa.Column("checkpoint_marker", sa.String(length=255), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_outcome", sa.String(length=50), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_system_scope",
            name="uq_synchronization_checkpoint_scope",
        ),
    )

    op.create_table(
        "conversation",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description_reference", sa.String(length=255), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
    )

    op.create_table(
        "crm_reference",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("display_reference", sa.String(length=255), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "entity_type",
            "external_id",
            name="uq_crm_reference_entity_external_id",
        ),
    )

    op.create_table(
        "extracted_fact",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("fact_type", sa.String(length=100), nullable=False),
        sa.Column("value_reference", sa.String(length=255), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "inference",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("inference_type", sa.String(length=100), nullable=False),
        sa.Column("value_reference", sa.String(length=255), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "proposal",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("proposal_type", sa.String(length=100), nullable=False),
        sa.Column("value_reference", sa.String(length=255), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
    )

    op.create_table(
        "audit_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("affected_record_type", sa.String(length=50), nullable=False),
        sa.Column("affected_record_id", sa.Integer(), nullable=False),
        sa.Column("actor_or_source", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.Column("outcome_reference", sa.String(length=255), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
    )

    op.create_table(
        "source_observation",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_version_marker", sa.String(length=255), nullable=True),
        sa.Column("observed_state", sa.String(length=30), nullable=False),
        sa.Column("outcome", sa.String(length=50), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "source_record_id",
            "source_version_marker",
            name="uq_source_observation_source_version",
        ),
    )

    op.create_table(
        "idempotency_identity",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("operation_kind", sa.String(length=100), nullable=False),
        sa.Column("scope", sa.String(length=100), nullable=False),
        sa.Column("identity_key", sa.String(length=255), nullable=False),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=True,
        ),
        sa.Column("target_reference", sa.String(length=255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "operation_kind",
            "scope",
            "identity_key",
            name="uq_idempotency_identity_key",
        ),
    )

    op.create_table(
        "conversation_membership",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversation.id"),
            nullable=False,
        ),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("evidence_reference", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "source_record_id",
            name="uq_conversation_membership_source_record",
        ),
    )

    op.create_table(
        "manual_note",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=False,
        ),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "source_record_id",
            name="uq_manual_note_source_record",
        ),
    )

    op.create_table(
        "whatsapp_import",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=False,
        ),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("pasted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "source_record_id",
            name="uq_whatsapp_import_source_record",
        ),
    )

    op.create_table(
        "calendar_event_representation",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=False,
        ),
        sa.Column("calendar_event_id", sa.String(length=255), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_state", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_record_id",
            name="uq_calendar_event_representation_source_record",
        ),
    )

    op.create_table(
        "activity_source_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "activity_id",
            sa.Integer(),
            sa.ForeignKey("activity.id"),
            nullable=False,
        ),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=False,
        ),
        sa.Column("link_purpose", sa.String(length=100), nullable=False),
        sa.UniqueConstraint(
            "activity_id",
            "source_record_id",
            "link_purpose",
            name="uq_activity_source_link",
        ),
    )

    op.create_table(
        "crm_context_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "crm_reference_id",
            sa.Integer(),
            sa.ForeignKey("crm_reference.id"),
            nullable=False,
        ),
        sa.Column("assistant_record_type", sa.String(length=50), nullable=False),
        sa.Column("assistant_record_id", sa.Integer(), nullable=False),
        sa.Column("relationship_purpose", sa.String(length=100), nullable=False),
        sa.Column("confirmation_state", sa.String(length=20), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "confirmation_state != 'confirmed' OR confirmed_at IS NOT NULL",
            name="ck_crm_context_link_confirmed_at",
        ),
    )

    op.create_table(
        "identity_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column("identity_type", sa.String(length=50), nullable=False),
        sa.Column("identity_value", sa.String(length=255), nullable=False),
        sa.Column(
            "crm_reference_id",
            sa.Integer(),
            sa.ForeignKey("crm_reference.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "fact_source_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "extracted_fact_id",
            sa.Integer(),
            sa.ForeignKey("extracted_fact.id"),
            nullable=False,
        ),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=False,
        ),
        sa.Column("evidence_reference", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "extracted_fact_id",
            "source_record_id",
            "evidence_reference",
            name="uq_fact_source_evidence",
        ),
    )

    op.create_table(
        "inference_support",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "inference_id",
            sa.Integer(),
            sa.ForeignKey("inference.id"),
            nullable=False,
        ),
        sa.Column("support_type", sa.String(length=30), nullable=False),
        sa.Column("support_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "inference_id",
            "support_type",
            "support_id",
            name="uq_inference_support",
        ),
    )

    op.create_table(
        "proposal_support",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "proposal_id",
            sa.Integer(),
            sa.ForeignKey("proposal.id"),
            nullable=False,
        ),
        sa.Column("support_type", sa.String(length=30), nullable=False),
        sa.Column("support_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "proposal_id",
            "support_type",
            "support_id",
            name="uq_proposal_support",
        ),
    )

    op.create_table(
        "identity_link_correction",
        sa.Column("id", sa.Integer(), primary_key=True),
        _created_at(),
        sa.Column(
            "prior_identity_link_id",
            sa.Integer(),
            sa.ForeignKey("identity_link.id"),
            nullable=False,
        ),
        sa.Column(
            "replacement_identity_link_id",
            sa.Integer(),
            sa.ForeignKey("identity_link.id"),
            nullable=False,
        ),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "prior_identity_link_id",
            name="uq_identity_link_correction_prior",
        ),
    )


def downgrade():
    op.drop_table("identity_link_correction")
    op.drop_table("proposal_support")
    op.drop_table("inference_support")
    op.drop_table("fact_source_evidence")
    op.drop_table("identity_link")
    op.drop_table("crm_context_link")
    op.drop_table("activity_source_link")
    op.drop_table("calendar_event_representation")
    op.drop_table("whatsapp_import")
    op.drop_table("manual_note")
    op.drop_table("conversation_membership")
    op.drop_table("idempotency_identity")
    op.drop_table("source_observation")
    op.drop_table("audit_event")
    op.drop_table("proposal")
    op.drop_table("inference")
    op.drop_table("extracted_fact")
    op.drop_table("crm_reference")
    op.drop_table("activity")
    op.drop_table("conversation")
    op.drop_table("synchronization_checkpoint")
    op.drop_table("source_record")
    op.drop_table("configuration_reference")
