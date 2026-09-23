"""Add the Phase 4 analysis foundation without rewriting legacy commitments."""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


_LEGACY_COMMITMENT_COLUMNS = (
    "id, created_at, description, state, due_at, resolution_reference, provenance"
)
_PHASE4_TABLES = (
    "analysis_run",
    "analysis_source_evidence",
    "analysis_derivation_link",
    "analysis_summary",
    "analysis_operational_link",
)


def _hex64(column):
    return f"length({column}) = 64 AND {column} NOT GLOB '*[^0-9a-f]*'"


def _sqlite_transaction():
    connection = op.get_bind()
    if connection.dialect.name != "sqlite":
        raise RuntimeError("Phase 4 analysis migration requires SQLite")
    # sqlite3 legacy mode does not start a transaction for DDL by itself.
    if not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    return connection


def _commitment_table(name, *, phase4):
    columns = [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
    ]
    if phase4:
        columns.extend((
            sa.Column("responsible_party", sa.String(16)),
            sa.Column("date_certainty", sa.String(20)),
            sa.Column("date_expression", sa.String(255)),
        ))
    columns.extend((
        sa.Column("resolution_reference", sa.String(255)),
        sa.Column("provenance", sa.String(255), nullable=False),
        sa.CheckConstraint(
            "state IN ('detected', 'confirmed', 'fulfilled', 'overdue', 'cancelled')",
            name="ck_commitment_state",
        ),
    ))
    if phase4:
        columns.extend((
            sa.CheckConstraint("responsible_party IS NULL OR responsible_party IN ('self', 'counterparty', 'unknown')", name="ck_commitment_responsible_party"),
            sa.CheckConstraint("date_certainty IS NULL OR date_certainty IN ('exact', 'resolved_relative', 'uncertain', 'none')", name="ck_commitment_date_certainty"),
            sa.CheckConstraint("date_expression IS NULL OR length(date_expression) <= 255", name="ck_commitment_date_expression"),
            sa.CheckConstraint("(responsible_party IS NULL AND date_certainty IS NULL AND date_expression IS NULL) OR (responsible_party IS NOT NULL AND date_certainty IS NOT NULL)", name="ck_commitment_phase4_fields"),
            sa.CheckConstraint("date_certainty IS NULL OR date_certainty NOT IN ('exact', 'resolved_relative') OR due_at IS NOT NULL", name="ck_commitment_dated_due"),
            sa.CheckConstraint("date_certainty != 'resolved_relative' OR date_expression IS NOT NULL", name="ck_commitment_relative_expression"),
            sa.CheckConstraint("date_certainty IS NULL OR date_certainty NOT IN ('uncertain', 'none') OR due_at IS NULL", name="ck_commitment_undated_due"),
        ))
    op.create_table(name, *columns)


def _rebuild_commitment(connection, *, phase4):
    replacement = "_commitment_0007_new"
    _commitment_table(replacement, phase4=phase4)
    connection.exec_driver_sql(
        f"INSERT INTO {replacement} ({_LEGACY_COMMITMENT_COLUMNS}) "
        f"SELECT {_LEGACY_COMMITMENT_COLUMNS} FROM commitment"
    )
    op.drop_index("ix_commitment_due_state", table_name="commitment")
    op.drop_table("commitment")
    op.rename_table(replacement, "commitment")
    op.create_index("ix_commitment_due_state", "commitment", ["state", "due_at"])


def upgrade():
    connection = _sqlite_transaction()
    op.create_table(
        "analysis_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_scope", sa.String(100), nullable=False),
        sa.Column("target_source_record_id", sa.Integer(), sa.ForeignKey("source_record.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversation.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("run_version", sa.Integer(), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("contract_version", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("request_mode", sa.String(12), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("failure_code", sa.String(32)),
        sa.Column("supersedes_run_id", sa.Integer(), sa.ForeignKey("analysis_run.id", ondelete="RESTRICT")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(account_scope) BETWEEN 1 AND 100", name="ck_analysis_run_scope"),
        sa.CheckConstraint("run_version > 0 AND contract_version > 0 AND policy_version > 0", name="ck_analysis_run_versions"),
        sa.CheckConstraint(_hex64("input_digest"), name="ck_analysis_run_digest"),
        sa.CheckConstraint("request_mode IN ('automatic', 'manual', 'force')", name="ck_analysis_run_request_mode"),
        sa.CheckConstraint("status IN ('reserved', 'completed', 'stale_retryable', 'failed_retryable')", name="ck_analysis_run_status"),
        sa.CheckConstraint("failure_code IS NULL OR failure_code IN ('input_changed', 'provider_failure', 'invalid_output', 'persistence_failure', 'interrupted')", name="ck_analysis_run_failure_code"),
        sa.CheckConstraint("(status = 'completed' AND completed_at IS NOT NULL AND failure_code IS NULL) OR (status = 'reserved' AND completed_at IS NULL AND failure_code IS NULL) OR (status IN ('stale_retryable', 'failed_retryable') AND completed_at IS NULL AND failure_code IS NOT NULL)", name="ck_analysis_run_lifecycle"),
        sa.CheckConstraint("supersedes_run_id IS NULL OR supersedes_run_id != id", name="ck_analysis_run_nonself"),
        sa.UniqueConstraint("account_scope", "target_source_record_id", "run_version", name="uq_analysis_run_target_version"),
        sa.UniqueConstraint("supersedes_run_id", name="uq_analysis_run_supersedes"),
    )
    op.create_index("ix_analysis_run_target_status_version", "analysis_run", ["account_scope", "target_source_record_id", "status", "run_version"])
    op.create_index("ix_analysis_run_replay", "analysis_run", ["target_source_record_id", "input_digest", "contract_version", "policy_version", "status"])

    op.create_table(
        "analysis_source_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysis_run_id", sa.Integer(), sa.ForeignKey("analysis_run.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_record_id", sa.Integer(), sa.ForeignKey("source_record.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("body_digest", sa.String(64), nullable=False),
        sa.Column("span_digest", sa.String(64), nullable=False),
        sa.Column("quote_state", sa.String(12), nullable=False),
        sa.CheckConstraint("start_offset >= 0 AND end_offset > start_offset", name="ck_analysis_evidence_offsets"),
        sa.CheckConstraint(_hex64("body_digest") + " AND " + _hex64("span_digest"), name="ck_analysis_evidence_digests"),
        sa.CheckConstraint("quote_state IN ('new', 'quoted', 'ambiguous')", name="ck_analysis_evidence_quote_state"),
        sa.UniqueConstraint("analysis_run_id", "source_record_id", "start_offset", "end_offset", "span_digest", name="uq_analysis_evidence_span"),
    )
    op.create_index("ix_analysis_evidence_source_body", "analysis_source_evidence", ["source_record_id", "body_digest"])

    op.create_table(
        "analysis_derivation_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysis_run_id", sa.Integer(), sa.ForeignKey("analysis_run.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("extracted_fact_id", sa.Integer(), sa.ForeignKey("extracted_fact.id", ondelete="RESTRICT")),
        sa.Column("inference_id", sa.Integer(), sa.ForeignKey("inference.id", ondelete="RESTRICT")),
        sa.Column("proposal_id", sa.Integer(), sa.ForeignKey("proposal.id", ondelete="RESTRICT")),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("analysis_source_evidence.id", ondelete="RESTRICT")),
        sa.CheckConstraint("(extracted_fact_id IS NOT NULL) + (inference_id IS NOT NULL) + (proposal_id IS NOT NULL) = 1", name="ck_analysis_derivation_exactly_one"),
    )
    for name, column in (
        ("uq_analysis_derivation_fact", "extracted_fact_id"),
        ("uq_analysis_derivation_inference", "inference_id"),
        ("uq_analysis_derivation_proposal", "proposal_id"),
    ):
        op.create_index(name, "analysis_derivation_link", ["analysis_run_id", column], unique=True, sqlite_where=sa.text(f"{column} IS NOT NULL"))
    op.create_index("ix_analysis_derivation_run", "analysis_derivation_link", ["analysis_run_id", "id"])

    op.create_table(
        "analysis_summary",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysis_run_id", sa.Integer(), sa.ForeignKey("analysis_run.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("summary_digest", sa.String(64), nullable=False),
        sa.CheckConstraint("length(summary_text) BETWEEN 1 AND 4000", name="ck_analysis_summary_length"),
        sa.CheckConstraint(_hex64("summary_digest"), name="ck_analysis_summary_digest"),
    )

    _rebuild_commitment(connection, phase4=True)

    op.create_table(
        "analysis_operational_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysis_run_id", sa.Integer(), sa.ForeignKey("analysis_run.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("derivation_link_id", sa.Integer(), sa.ForeignKey("analysis_derivation_link.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operational_type", sa.String(20), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("question.id", ondelete="RESTRICT")),
        sa.Column("commitment_id", sa.Integer(), sa.ForeignKey("commitment.id", ondelete="RESTRICT")),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("task.id", ondelete="RESTRICT")),
        sa.Column("next_step_id", sa.Integer(), sa.ForeignKey("next_step.id", ondelete="RESTRICT")),
        sa.CheckConstraint("(operational_type = 'question' AND question_id IS NOT NULL AND commitment_id IS NULL AND task_id IS NULL AND next_step_id IS NULL) OR (operational_type = 'commitment' AND question_id IS NULL AND commitment_id IS NOT NULL AND task_id IS NULL AND next_step_id IS NULL) OR (operational_type = 'task' AND question_id IS NULL AND commitment_id IS NULL AND task_id IS NOT NULL AND next_step_id IS NULL) OR (operational_type = 'next_step' AND question_id IS NULL AND commitment_id IS NULL AND task_id IS NULL AND next_step_id IS NOT NULL)", name="ck_analysis_operational_type_target"),
    )
    for name, column in (
        ("uq_analysis_operational_question", "question_id"),
        ("uq_analysis_operational_commitment", "commitment_id"),
        ("uq_analysis_operational_task", "task_id"),
        ("uq_analysis_operational_next_step", "next_step_id"),
    ):
        op.create_index(name, "analysis_operational_link", [column], unique=True, sqlite_where=sa.text(f"{column} IS NOT NULL"))
    op.create_index("ix_analysis_operational_run_type", "analysis_operational_link", ["analysis_run_id", "operational_type"])
    if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Phase 4 analysis upgrade failed foreign_key_check")


def downgrade():
    connection = _sqlite_transaction()
    for table in _PHASE4_TABLES:
        if connection.exec_driver_sql(f"SELECT 1 FROM {table} LIMIT 1").first() is not None:
            raise RuntimeError("Phase 4 analysis downgrade refused: analysis data exists")
    if connection.exec_driver_sql(
        "SELECT 1 FROM commitment WHERE responsible_party IS NOT NULL "
        "OR date_certainty IS NOT NULL OR date_expression IS NOT NULL LIMIT 1"
    ).first() is not None:
        raise RuntimeError("Phase 4 analysis downgrade refused: commitment data exists")
    for table in reversed(_PHASE4_TABLES):
        op.drop_table(table)
    _rebuild_commitment(connection, phase4=False)
    if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Phase 4 analysis downgrade failed foreign_key_check")
