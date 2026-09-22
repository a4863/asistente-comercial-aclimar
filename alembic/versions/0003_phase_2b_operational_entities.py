"""phase 2b operational entities — core operational records"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_reference", sa.String(length=255), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "state IN ('proposed', 'pending', 'completed', 'cancelled')",
            name="ck_task_state",
        ),
    )

    op.create_table(
        "commitment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_reference", sa.String(length=255), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "state IN ('detected', 'confirmed', 'fulfilled', 'overdue', 'cancelled')",
            name="ck_commitment_state",
        ),
    )
    op.create_index(
        "ix_commitment_due_state",
        "commitment",
        ["state", "due_at"],
        unique=False,
    )

    op.create_table(
        "question",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("answer_reference", sa.String(length=255), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "state IN ('detected', 'open', 'answered', 'dismissed')",
            name="ck_question_state",
        ),
    )

    op.create_table(
        "next_step",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("target_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_reference", sa.String(length=255), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "state IN ('proposed', 'planned', 'completed', 'cancelled')",
            name="ck_next_step_state",
        ),
    )

    op.create_table(
        "alert",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("alert_type", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("condition_key", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "state IN ('active', 'resolved', 'dismissed')",
            name="ck_alert_state",
        ),
    )
    op.create_index(
        "uq_alert_active_condition",
        "alert",
        ["alert_type", "target_type", "target_id", "condition_key"],
        unique=True,
        sqlite_where=sa.text("state = 'active'"),
    )

    op.create_table(
        "follow_up_preference",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("scope_reference", sa.String(length=255), nullable=True),
        sa.Column("classification", sa.String(length=50), nullable=False),
        sa.Column("inactivity_days", sa.Integer(), nullable=True),
        sa.Column("explicit_future_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "inactivity_days IS NULL OR inactivity_days >= 0",
            name="ck_follow_up_preference_inactivity_days",
        ),
    )
    op.create_index(
        "uq_follow_up_preference_scoped",
        "follow_up_preference",
        ["scope_type", "scope_reference"],
        unique=True,
        sqlite_where=sa.text("scope_reference IS NOT NULL"),
    )
    op.create_index(
        "uq_follow_up_preference_global",
        "follow_up_preference",
        ["scope_type"],
        unique=True,
        sqlite_where=sa.text("scope_reference IS NULL"),
    )
    op.create_index(
        "ix_follow_up_preference_lookup",
        "follow_up_preference",
        ["scope_type", "scope_reference"],
        unique=False,
    )

    op.create_table(
        "follow_up_preference_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "follow_up_preference_id",
            sa.Integer(),
            sa.ForeignKey("follow_up_preference.id"),
            nullable=False,
        ),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("scope_reference", sa.String(length=255), nullable=True),
        sa.Column("classification", sa.String(length=50), nullable=False),
        sa.Column("inactivity_days", sa.Integer(), nullable=True),
        sa.Column("explicit_future_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "inactivity_days IS NULL OR inactivity_days >= 0",
            name="ck_follow_up_preference_history_inactivity_days",
        ),
    )

    op.create_table(
        "action_proposal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_reference", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column(
            "idempotency_identity_id",
            sa.Integer(),
            sa.ForeignKey("idempotency_identity.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "state IN ('pending_approval', 'approved', 'rejected', 'executed', 'error')",
            name="ck_action_proposal_state",
        ),
    )

    op.create_table(
        "approval_decision",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "action_proposal_id",
            sa.Integer(),
            sa.ForeignKey("action_proposal.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_reference", sa.String(length=255), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_approval_decision_value",
        ),
    )

    op.create_table(
        "execution_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "action_proposal_id",
            sa.Integer(),
            sa.ForeignKey("action_proposal.id"),
            nullable=False,
        ),
        sa.Column(
            "approval_decision_id",
            sa.Integer(),
            sa.ForeignKey("approval_decision.id"),
            nullable=True,
        ),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revalidation_reference", sa.String(length=255), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("external_result_reference", sa.String(length=255), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('executed', 'error')",
            name="ck_execution_result_outcome",
        ),
    )
    op.create_index(
        "ix_execution_result_action_attempt",
        "execution_result",
        ["action_proposal_id", "attempted_at"],
        unique=False,
    )

    op.create_table(
        "operational_evidence_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("operational_type", sa.String(length=30), nullable=False),
        sa.Column("operational_id", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(length=30), nullable=False),
        sa.Column("evidence_id", sa.Integer(), nullable=True),
        sa.Column("evidence_reference", sa.String(length=255), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "operational_type IN ('task', 'commitment', 'question', 'next_step', 'alert', 'action_proposal')",
            name="ck_operational_evidence_target_type",
        ),
        sa.CheckConstraint(
            "evidence_type IN ('source', 'fact', 'inference', 'proposal', 'user_confirmation')",
            name="ck_operational_evidence_type",
        ),
        sa.CheckConstraint(
            "(evidence_type = 'user_confirmation' AND evidence_id IS NULL AND evidence_reference IS NOT NULL) OR "
            "(evidence_type != 'user_confirmation' AND evidence_id IS NOT NULL)",
            name="ck_operational_evidence_shape",
        ),
        sa.UniqueConstraint(
            "operational_type",
            "operational_id",
            "evidence_type",
            "evidence_id",
            "evidence_reference",
            name="uq_operational_evidence_link",
        ),
    )


def downgrade():
    op.drop_table("operational_evidence_link")
    op.drop_index("ix_execution_result_action_attempt", table_name="execution_result")
    op.drop_table("execution_result")
    op.drop_table("approval_decision")
    op.drop_table("action_proposal")
    op.drop_table("follow_up_preference_history")
    op.drop_index("ix_follow_up_preference_lookup", table_name="follow_up_preference")
    op.drop_index("uq_follow_up_preference_global", table_name="follow_up_preference")
    op.drop_index("uq_follow_up_preference_scoped", table_name="follow_up_preference")
    op.drop_table("follow_up_preference")
    op.drop_index("uq_alert_active_condition", table_name="alert")
    op.drop_table("alert")
    op.drop_table("next_step")
    op.drop_table("question")
    op.drop_index("ix_commitment_due_state", table_name="commitment")
    op.drop_table("commitment")
    op.drop_table("task")
