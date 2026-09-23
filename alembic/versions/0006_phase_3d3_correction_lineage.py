"""Permit one-to-one correction lineage without losing existing history."""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


_OP_COLUMNS = "id, created_at, account_scope, kind, reconstruction_key, replay_key, provenance"
_EDGE_COLUMNS = "id, created_at, operation_id, predecessor_conversation_id, successor_conversation_id"


def _hex64(column):
    return f"length({column}) = 64 AND {column} NOT GLOB '*[^0-9a-f]*'"


def _operation_table(name, *, correction):
    kinds = "'merge', 'split', 'repartition', 'correction'" if correction else "'merge', 'split', 'repartition'"
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_scope", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("reconstruction_key", sa.String(64), nullable=False),
        sa.Column("replay_key", sa.String(64), nullable=False),
        sa.Column("provenance", sa.String(50), nullable=False),
        sa.CheckConstraint(f"kind IN ({kinds})", name="ck_thread_lineage_operation_kind"),
        sa.CheckConstraint(_hex64("reconstruction_key") + " AND " + _hex64("replay_key"),
                           name="ck_thread_lineage_operation_keys"),
        sa.CheckConstraint("length(account_scope) BETWEEN 1 AND 100 AND length(provenance) BETWEEN 1 AND 50",
                           name="ck_thread_lineage_operation_scope_provenance"),
        sa.UniqueConstraint("replay_key", name="uq_thread_lineage_operation_replay"),
    )


def _edge_table():
    op.create_table(
        "thread_lineage_edge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("operation_id", sa.Integer(), sa.ForeignKey("thread_lineage_operation.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("predecessor_conversation_id", sa.Integer(), sa.ForeignKey("conversation.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("successor_conversation_id", sa.Integer(), sa.ForeignKey("conversation.id", ondelete="RESTRICT"), nullable=False),
        sa.CheckConstraint("predecessor_conversation_id != successor_conversation_id",
                           name="ck_thread_lineage_edge_nonself"),
        sa.UniqueConstraint("operation_id", "predecessor_conversation_id", "successor_conversation_id",
                            name="uq_thread_lineage_edge_pair"),
    )
    op.create_index("ix_thread_lineage_edge_predecessor", "thread_lineage_edge", ["predecessor_conversation_id"])
    op.create_index("ix_thread_lineage_edge_successor", "thread_lineage_edge", ["successor_conversation_id"])


def _rebuild(*, correction):
    connection = op.get_bind()
    if connection.dialect.name != "sqlite":
        raise RuntimeError("Phase 3D3 correction lineage migration requires SQLite")
    # sqlite3's legacy transaction mode does not begin a transaction for DDL.
    # Join an already active migration transaction, or reserve one before DDL.
    if not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")

    op.create_table(
        "_thread_lineage_edge_0006_backup",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("operation_id", sa.Integer(), nullable=False),
        sa.Column("predecessor_conversation_id", sa.Integer(), nullable=False),
        sa.Column("successor_conversation_id", sa.Integer(), nullable=False),
    )
    connection.exec_driver_sql(
        f"INSERT INTO _thread_lineage_edge_0006_backup ({_EDGE_COLUMNS}) "
        f"SELECT {_EDGE_COLUMNS} FROM thread_lineage_edge"
    )
    op.drop_index("ix_thread_lineage_edge_predecessor", table_name="thread_lineage_edge")
    op.drop_index("ix_thread_lineage_edge_successor", table_name="thread_lineage_edge")
    op.drop_table("thread_lineage_edge")

    _operation_table("_thread_lineage_operation_0006_new", correction=correction)
    connection.exec_driver_sql(
        f"INSERT INTO _thread_lineage_operation_0006_new ({_OP_COLUMNS}) "
        f"SELECT {_OP_COLUMNS} FROM thread_lineage_operation"
    )
    op.drop_index("ix_thread_lineage_operation_scope_time", table_name="thread_lineage_operation")
    op.drop_table("thread_lineage_operation")
    op.rename_table("_thread_lineage_operation_0006_new", "thread_lineage_operation")
    op.create_index("ix_thread_lineage_operation_scope_time", "thread_lineage_operation",
                    ["account_scope", "created_at", "id"])

    _edge_table()
    connection.exec_driver_sql(
        f"INSERT INTO thread_lineage_edge ({_EDGE_COLUMNS}) "
        f"SELECT {_EDGE_COLUMNS} FROM _thread_lineage_edge_0006_backup"
    )
    op.drop_table("_thread_lineage_edge_0006_backup")
    if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Phase 3D3 correction lineage migration failed foreign_key_check")


def upgrade():
    _rebuild(correction=True)


def downgrade():
    connection = op.get_bind()
    if connection.exec_driver_sql(
        "SELECT 1 FROM thread_lineage_operation WHERE kind='correction' LIMIT 1"
    ).first() is not None:
        raise RuntimeError("Phase 3D3 downgrade refused: correction lineage exists")
    _rebuild(correction=False)
