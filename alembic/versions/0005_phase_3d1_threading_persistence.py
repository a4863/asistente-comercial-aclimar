"""Phase 3D1 threading persistence and legacy quarantine."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _hex64(column):
    return f"length({column}) = 64 AND {column} NOT GLOB '*[^0-9a-f]*'"


def _base():
    return sa.Column("id", sa.Integer(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)


def _fk(name, table, *, nullable=False):
    return sa.Column(name, sa.Integer(), sa.ForeignKey(f"{table}.id", ondelete="RESTRICT"), nullable=nullable)


def _create_thread_tables():
    op.create_table(
        "thread_evidence", *_base(),
        sa.Column("account_scope", sa.String(100), nullable=False),
        _fk("source_record_id", "source_record"),
        sa.Column("header_kind", sa.String(20), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("parse_status", sa.String(12), nullable=False),
        sa.Column("canonical_token", sa.String(998)),
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("normalization_version", sa.Integer(), nullable=False),
        sa.Column("source_revision", sa.String(64), nullable=False),
        sa.Column("replay_key", sa.String(64), nullable=False),
        sa.CheckConstraint("header_kind IN ('message_id', 'in_reply_to', 'references')", name="ck_thread_evidence_kind"),
        sa.CheckConstraint("parse_status IN ('valid', 'malformed')", name="ck_thread_evidence_parse_status"),
        sa.CheckConstraint("(parse_status = 'valid' AND canonical_token IS NOT NULL AND length(canonical_token) BETWEEN 1 AND 998) OR (parse_status = 'malformed' AND canonical_token IS NULL)", name="ck_thread_evidence_token_shape"),
        sa.CheckConstraint("ordinal >= 0 AND normalization_version > 0", name="ck_thread_evidence_ordinal_version"),
        sa.CheckConstraint(" AND ".join(_hex64(name) for name in ("token_digest", "source_revision", "replay_key")), name="ck_thread_evidence_digests"),
        sa.CheckConstraint("length(account_scope) BETWEEN 1 AND 100", name="ck_thread_evidence_scope"),
        sa.UniqueConstraint("replay_key", name="uq_thread_evidence_replay"),
        sa.UniqueConstraint("source_record_id", "source_revision", "normalization_version", "header_kind", "ordinal", name="uq_thread_evidence_source_revision_ordinal"),
    )
    op.create_index("ix_thread_evidence_scope_token_kind", "thread_evidence", ["account_scope", "token_digest", "header_kind"])
    op.create_index("ix_thread_evidence_source_revision", "thread_evidence", ["source_record_id", "source_revision"])

    op.create_table(
        "thread_evidence_decision", *_base(),
        _fk("evidence_id", "thread_evidence"),
        _fk("target_source_record_id", "source_record", nullable=True),
        sa.Column("reconstruction_key", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("replay_key", sa.String(64), nullable=False),
        sa.CheckConstraint("outcome IN ('identity_observed', 'accepted_direct_parent', 'accepted_ancestor', 'unresolved_external', 'duplicate_target', 'malformed', 'multiple_in_reply_to', 'self_link', 'cycle_rejected', 'conflict', 'not_linking')", name="ck_thread_decision_outcome"),
        sa.CheckConstraint("(outcome IN ('accepted_direct_parent', 'accepted_ancestor') AND target_source_record_id IS NOT NULL) OR (outcome NOT IN ('accepted_direct_parent', 'accepted_ancestor') AND target_source_record_id IS NULL)", name="ck_thread_decision_target"),
        sa.CheckConstraint(_hex64("reconstruction_key") + " AND " + _hex64("replay_key"), name="ck_thread_decision_keys"),
        sa.UniqueConstraint("evidence_id", "reconstruction_key", name="uq_thread_decision_evidence_reconstruction"),
        sa.UniqueConstraint("replay_key", name="uq_thread_decision_replay"),
    )
    op.create_index("ix_thread_decision_target", "thread_evidence_decision", ["target_source_record_id"])
    op.create_index("ix_thread_decision_reconstruction_outcome", "thread_evidence_decision", ["reconstruction_key", "outcome"])

    op.create_table(
        "thread_membership_change", *_base(),
        _fk("source_record_id", "source_record"),
        sa.Column("account_scope", sa.String(100)),
        _fk("old_conversation_id", "conversation", nullable=True),
        _fk("new_conversation_id", "conversation"),
        sa.Column("reason", sa.String(32), nullable=False),
        _fk("evidence_decision_id", "thread_evidence_decision", nullable=True),
        sa.Column("reconstruction_key", sa.String(64)),
        sa.Column("replay_key", sa.String(64), nullable=False),
        sa.CheckConstraint("reason IN ('legacy_assignment_baseline', 'initial_assignment', 'merge', 'split', 'repartition', 'correction')", name="ck_thread_membership_change_reason"),
        sa.CheckConstraint("(reason IN ('legacy_assignment_baseline', 'initial_assignment') AND old_conversation_id IS NULL) OR (reason IN ('merge', 'split', 'repartition', 'correction') AND old_conversation_id IS NOT NULL AND old_conversation_id != new_conversation_id)", name="ck_thread_membership_change_old_new"),
        sa.CheckConstraint("(reason = 'legacy_assignment_baseline' AND reconstruction_key IS NULL AND evidence_decision_id IS NULL) OR (reason != 'legacy_assignment_baseline' AND account_scope IS NOT NULL AND length(account_scope) BETWEEN 1 AND 100 AND reconstruction_key IS NOT NULL)", name="ck_thread_membership_change_baseline"),
        sa.CheckConstraint(_hex64("replay_key") + " AND (reconstruction_key IS NULL OR (" + _hex64("reconstruction_key") + "))", name="ck_thread_membership_change_keys"),
        sa.UniqueConstraint("replay_key", name="uq_thread_membership_change_replay"),
    )
    op.create_index("ix_thread_membership_change_source_time", "thread_membership_change", ["source_record_id", "created_at", "id"])
    op.create_index("ix_thread_membership_change_old", "thread_membership_change", ["old_conversation_id"])
    op.create_index("ix_thread_membership_change_new", "thread_membership_change", ["new_conversation_id"])
    op.create_index("ix_thread_membership_change_scope_reconstruction", "thread_membership_change", ["account_scope", "reconstruction_key"])

    op.create_table(
        "thread_lineage_operation", *_base(),
        sa.Column("account_scope", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("reconstruction_key", sa.String(64), nullable=False),
        sa.Column("replay_key", sa.String(64), nullable=False),
        sa.Column("provenance", sa.String(50), nullable=False),
        sa.CheckConstraint("kind IN ('merge', 'split', 'repartition')", name="ck_thread_lineage_operation_kind"),
        sa.CheckConstraint(_hex64("reconstruction_key") + " AND " + _hex64("replay_key"), name="ck_thread_lineage_operation_keys"),
        sa.CheckConstraint("length(account_scope) BETWEEN 1 AND 100 AND length(provenance) BETWEEN 1 AND 50", name="ck_thread_lineage_operation_scope_provenance"),
        sa.UniqueConstraint("replay_key", name="uq_thread_lineage_operation_replay"),
    )
    op.create_index("ix_thread_lineage_operation_scope_time", "thread_lineage_operation", ["account_scope", "created_at", "id"])

    op.create_table(
        "thread_lineage_edge", *_base(),
        _fk("operation_id", "thread_lineage_operation"),
        _fk("predecessor_conversation_id", "conversation"),
        _fk("successor_conversation_id", "conversation"),
        sa.CheckConstraint("predecessor_conversation_id != successor_conversation_id", name="ck_thread_lineage_edge_nonself"),
        sa.UniqueConstraint("operation_id", "predecessor_conversation_id", "successor_conversation_id", name="uq_thread_lineage_edge_pair"),
    )
    op.create_index("ix_thread_lineage_edge_predecessor", "thread_lineage_edge", ["predecessor_conversation_id"])
    op.create_index("ix_thread_lineage_edge_successor", "thread_lineage_edge", ["successor_conversation_id"])


def upgrade():
    connection = op.get_bind()
    op.add_column("conversation", sa.Column("account_scope", sa.String(100)))
    op.add_column("conversation", sa.Column("stable_key", sa.String(36)))
    op.add_column("conversation", sa.Column("legacy_status", sa.String(20)))
    _create_thread_tables()
    op.create_index("ix_conversation_membership_conversation_id", "conversation_membership", ["conversation_id"])

    conversations = connection.execute(sa.text("SELECT id, superseded_at FROM conversation ORDER BY id")).all()
    used_keys = set()
    scopes = {}
    for conversation_id, superseded_at in conversations:
        members = connection.execute(sa.text("""
            SELECT sr.source_type, sr.source_system_scope, em.id AS email_id
            FROM conversation_membership cm
            LEFT JOIN source_record sr ON sr.id = cm.source_record_id
            LEFT JOIN email_message em ON em.source_record_id = sr.id
            WHERE cm.conversation_id = :conversation_id
        """), {"conversation_id": conversation_id}).mappings().all()
        valid = bool(members) and superseded_at is None and all(
            row["source_type"] == "email_message" and row["email_id"] is not None
            and row["source_system_scope"] and len(row["source_system_scope"]) <= 100
            for row in members
        )
        member_scopes = {row["source_system_scope"] for row in members} if valid else set()
        scope = next(iter(member_scopes)) if len(member_scopes) == 1 else None
        stable_key = str(uuid4())
        while stable_key in used_keys:
            stable_key = str(uuid4())
        used_keys.add(stable_key)
        scopes[conversation_id] = scope
        connection.execute(sa.text("""
            UPDATE conversation SET account_scope=:scope, stable_key=:stable_key, legacy_status=:status
            WHERE id=:conversation_id
        """), {"scope": scope, "stable_key": stable_key,
               "status": "resolved" if scope else "legacy_unresolved", "conversation_id": conversation_id})

    memberships = connection.execute(sa.text("SELECT id, source_record_id, conversation_id FROM conversation_membership ORDER BY id")).mappings().all()
    for member in memberships:
        digest = sha256(b"3d1/legacy-baseline/v1" + str(len(str(member["id"]).encode("utf-8"))).encode("ascii") + b":" + str(member["id"]).encode("utf-8")).hexdigest()
        connection.execute(sa.text("""
            INSERT INTO thread_membership_change
            (created_at, source_record_id, account_scope, old_conversation_id, new_conversation_id,
             reason, evidence_decision_id, reconstruction_key, replay_key)
            VALUES (:created_at, :source_record_id, :scope, NULL, :conversation_id,
                    'legacy_assignment_baseline', NULL, NULL, :replay_key)
        """), {"created_at": datetime.now(timezone.utc), "source_record_id": member["source_record_id"],
                "scope": scopes[member["conversation_id"]], "conversation_id": member["conversation_id"], "replay_key": digest})

    with op.batch_alter_table("conversation") as batch:
        batch.alter_column("stable_key", existing_type=sa.String(36), nullable=False)
        batch.alter_column("legacy_status", existing_type=sa.String(20), nullable=False)
        batch.create_check_constraint("ck_conversation_scope_status", "(legacy_status = 'resolved' AND account_scope IS NOT NULL AND length(account_scope) BETWEEN 1 AND 100) OR (legacy_status = 'legacy_unresolved' AND account_scope IS NULL)")
        batch.create_check_constraint("ck_conversation_stable_key", "length(stable_key) = 36 AND stable_key = lower(stable_key) AND substr(stable_key, 9, 1) = '-' AND substr(stable_key, 14, 1) = '-' AND substr(stable_key, 15, 1) = '4' AND substr(stable_key, 19, 1) = '-' AND substr(stable_key, 24, 1) = '-' AND stable_key NOT GLOB '*[^0-9a-f-]*'")
        batch.create_unique_constraint("uq_conversation_scope_stable_key", ["account_scope", "stable_key"])
    op.create_index("ix_conversation_scope_status_superseded", "conversation", ["account_scope", "legacy_status", "superseded_at"])
    migrated_conversations = connection.execute(sa.text("SELECT count(*) FROM conversation")).scalar_one()
    baseline_count = connection.execute(sa.text("SELECT count(*) FROM thread_membership_change WHERE reason='legacy_assignment_baseline'")).scalar_one()
    if migrated_conversations != len(conversations) or baseline_count != len(memberships):
        raise RuntimeError("Phase 3D1 backfill count mismatch")
    if connection.exec_driver_sql("PRAGMA foreign_key_check").first() is not None:
        raise RuntimeError("Phase 3D1 backfill foreign-key violation")


def downgrade():
    connection = op.get_bind()
    guarded = ("conversation", "conversation_membership", "thread_evidence", "thread_evidence_decision",
               "thread_membership_change", "thread_lineage_operation", "thread_lineage_edge")
    if any(connection.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() for table in guarded):
        raise RuntimeError("Phase 3D1 downgrade refused: populated conversation/thread data would be lost")
    op.drop_index("ix_thread_lineage_edge_successor", table_name="thread_lineage_edge")
    op.drop_index("ix_thread_lineage_edge_predecessor", table_name="thread_lineage_edge")
    op.drop_table("thread_lineage_edge")
    op.drop_index("ix_thread_lineage_operation_scope_time", table_name="thread_lineage_operation")
    op.drop_table("thread_lineage_operation")
    for name in ("ix_thread_membership_change_scope_reconstruction", "ix_thread_membership_change_new",
                 "ix_thread_membership_change_old", "ix_thread_membership_change_source_time"):
        op.drop_index(name, table_name="thread_membership_change")
    op.drop_table("thread_membership_change")
    op.drop_index("ix_thread_decision_reconstruction_outcome", table_name="thread_evidence_decision")
    op.drop_index("ix_thread_decision_target", table_name="thread_evidence_decision")
    op.drop_table("thread_evidence_decision")
    op.drop_index("ix_thread_evidence_source_revision", table_name="thread_evidence")
    op.drop_index("ix_thread_evidence_scope_token_kind", table_name="thread_evidence")
    op.drop_table("thread_evidence")
    op.drop_index("ix_conversation_membership_conversation_id", table_name="conversation_membership")
    op.drop_index("ix_conversation_scope_status_superseded", table_name="conversation")
    with op.batch_alter_table("conversation") as batch:
        batch.drop_constraint("ck_conversation_scope_status", type_="check")
        batch.drop_constraint("ck_conversation_stable_key", type_="check")
        batch.drop_constraint("uq_conversation_scope_stable_key", type_="unique")
        batch.drop_column("legacy_status")
        batch.drop_column("stable_key")
        batch.drop_column("account_scope")
