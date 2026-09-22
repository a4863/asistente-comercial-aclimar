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


def downgrade():
    op.drop_index("uq_alert_active_condition", table_name="alert")
    op.drop_table("alert")
    op.drop_table("next_step")
    op.drop_table("question")
    op.drop_index("ix_commitment_due_state", table_name="commitment")
    op.drop_table("commitment")
    op.drop_table("task")
