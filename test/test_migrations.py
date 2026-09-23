from alembic.config import Config
from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text
from uuid import uuid4


PHASE2B_TABLES = {
    "task",
    "commitment",
    "question",
    "next_step",
    "alert",
    "follow_up_preference",
    "follow_up_preference_history",
    "action_proposal",
    "approval_decision",
    "execution_result",
    "operational_evidence_link",
}
PHASE3A_TABLES = {
    "email_message",
    "imap_message_location",
    "email_attachment_metadata",
}
PHASE3D1_TABLES = {
    "thread_evidence", "thread_evidence_decision", "thread_membership_change",
    "thread_lineage_operation", "thread_lineage_edge",
}


def _config(isolated_tmp_path):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{isolated_tmp_path / 'test.db'}")
    return cfg


def test_upgrade_empty_database(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "head")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        tables = set(inspect(engine).get_table_names())
        assert "source_record" in tables
        assert PHASE2B_TABLES <= tables
        assert PHASE3A_TABLES <= tables
        assert PHASE3D1_TABLES <= tables
        assert {"account_scope", "stable_key", "legacy_status"} <= {
            column["name"] for column in inspect(engine).get_columns("conversation")
        }

        command.downgrade(cfg, "0004")
        assert PHASE3D1_TABLES.isdisjoint(inspect(engine).get_table_names())
        command.upgrade(cfg, "head")
        assert PHASE3D1_TABLES <= set(inspect(engine).get_table_names())

        command.downgrade(cfg, "0003")
        tables_after_downgrade = set(inspect(engine).get_table_names())
        assert "source_record" in tables_after_downgrade
        assert PHASE2B_TABLES <= tables_after_downgrade
        assert PHASE3A_TABLES.isdisjoint(tables_after_downgrade)

        command.upgrade(cfg, "head")
        tables_after_reupgrade = set(inspect(engine).get_table_names())
        assert PHASE2B_TABLES <= tables_after_reupgrade
        assert PHASE3A_TABLES <= tables_after_reupgrade
    finally:
        engine.dispose()


def _legacy_source(connection, scope, *, source_type="email_message", email=True):
    result = connection.execute(text("""
        INSERT INTO source_record
        (created_at, source_type, source_system_scope, ingested_at, retention_state, manual_entry, provenance)
        VALUES ('2026-01-01', :source_type, :scope, '2026-01-01', 'active', 0, 'test')
    """), {"source_type": source_type, "scope": scope})
    source_id = result.lastrowid
    if email:
        connection.execute(text("""
            INSERT INTO email_message
            (created_at, source_record_id, content_truncated, provenance)
            VALUES ('2026-01-01', :source_id, 0, 'test')
        """), {"source_id": source_id})
    return source_id


def _legacy_conversation(connection, members, *, superseded=False):
    result = connection.execute(text("""
        INSERT INTO conversation (created_at, provenance, superseded_at)
        VALUES ('2026-01-01', 'old', :superseded)
    """), {"superseded": "2026-02-01" if superseded else None})
    conversation_id = result.lastrowid
    for source_id in members:
        connection.execute(text("""
            INSERT INTO conversation_membership
            (created_at, conversation_id, source_record_id, evidence_type, evidence_reference)
            VALUES ('2026-01-01', :conversation_id, :source_id, 'old-proof', 'legacy-ref')
        """), {"conversation_id": conversation_id, "source_id": source_id})
    return conversation_id


def test_phase3d1_legacy_classification_history_and_downgrade_guard(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0004")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        valid = _legacy_conversation(connection, [_legacy_source(connection, "imap:one")])
        orphan = _legacy_conversation(connection, [])
        mixed = _legacy_conversation(connection, [
            _legacy_source(connection, "imap:one"), _legacy_source(connection, "imap:two")])
        non_email = _legacy_conversation(connection, [
            _legacy_source(connection, "manual", source_type="manual_note", email=False)])
        missing_email = _legacy_conversation(connection, [_legacy_source(connection, "imap:one", email=False)])
        empty_scope = _legacy_conversation(connection, [_legacy_source(connection, "")])
        superseded = _legacy_conversation(connection, [_legacy_source(connection, "imap:one")], superseded=True)
    engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        rows = {row.id: row for row in connection.execute(text(
            "SELECT id, account_scope, stable_key, legacy_status FROM conversation"
        )).all()}
        assert rows[valid].account_scope == "imap:one"
        assert rows[valid].legacy_status == "resolved"
        for identifier in (orphan, mixed, non_email, missing_email, empty_scope, superseded):
            assert rows[identifier].account_scope is None
            assert rows[identifier].legacy_status == "legacy_unresolved"
        assert len({row.stable_key for row in rows.values()}) == len(rows)
        assert all(len(row.stable_key) == 36 for row in rows.values())
        membership_count = connection.execute(text("SELECT count(*) FROM conversation_membership")).scalar_one()
        baseline_count = connection.execute(text("""
            SELECT count(*) FROM thread_membership_change
            WHERE reason='legacy_assignment_baseline' AND old_conversation_id IS NULL
              AND evidence_decision_id IS NULL AND reconstruction_key IS NULL
        """)).scalar_one()
        assert baseline_count == membership_count == 7
        assert connection.execute(text("SELECT count(*) FROM conversation_membership WHERE evidence_type='old-proof' AND evidence_reference='legacy-ref'")).scalar_one() == 7
        assert connection.execute(text("SELECT count(*) FROM thread_membership_change WHERE account_scope IS NULL")).scalar_one() == 6
        indexes = {entry["name"] for entry in inspect(engine).get_indexes("thread_evidence")}
        assert {"ix_thread_evidence_scope_token_kind", "ix_thread_evidence_source_revision"} <= indexes
        checks = {entry["name"] for entry in inspect(engine).get_check_constraints("thread_evidence")}
        assert "ck_thread_evidence_token_shape" in checks
    engine.dispose()

    with pytest.raises(RuntimeError, match="downgrade refused"):
        command.downgrade(cfg, "0004")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM thread_membership_change")).scalar_one() == 7
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0005"
    finally:
        engine.dispose()


def _lineage_rows(connection):
    operations = tuple(tuple(row) for row in connection.execute(text("""
        SELECT id, created_at, account_scope, kind, reconstruction_key, replay_key, provenance
        FROM thread_lineage_operation ORDER BY id
    """)))
    edges = tuple(tuple(row) for row in connection.execute(text("""
        SELECT id, created_at, operation_id, predecessor_conversation_id, successor_conversation_id
        FROM thread_lineage_edge ORDER BY id
    """)))
    return operations, edges


def _lineage_conversations(connection, count):
    result = []
    for _ in range(count):
        row = connection.execute(text("""
            INSERT INTO conversation
            (created_at, provenance, account_scope, stable_key, legacy_status)
            VALUES ('2026-01-01', 'test', 'imap:one', :stable_key, 'resolved')
        """), {"stable_key": str(uuid4())})
        result.append(row.lastrowid)
    return result


def _lineage_operation(connection, kind, key, predecessor_ids, successor_ids):
    row = connection.execute(text("""
        INSERT INTO thread_lineage_operation
        (created_at, account_scope, kind, reconstruction_key, replay_key, provenance)
        VALUES ('2026-01-01', 'imap:one', :kind, :reconstruction_key, :replay_key, 'test')
    """), {"kind": kind, "reconstruction_key": "d" * 64, "replay_key": key * 64})
    for predecessor_id in predecessor_ids:
        for successor_id in successor_ids:
            connection.execute(text("""
                INSERT INTO thread_lineage_edge
                (created_at, operation_id, predecessor_conversation_id, successor_conversation_id)
                VALUES ('2026-01-01', :operation_id, :predecessor_id, :successor_id)
            """), {"operation_id": row.lastrowid, "predecessor_id": predecessor_id,
                   "successor_id": successor_id})
    return row.lastrowid


def test_phase3d3a_lineage_migration_roundtrip_preserves_rows(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0005")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        ids = _lineage_conversations(connection, 10)
        _lineage_operation(connection, "merge", "a", ids[:2], [ids[2]])
        _lineage_operation(connection, "split", "b", [ids[3]], ids[4:6])
        _lineage_operation(connection, "repartition", "c", ids[6:8], ids[8:10])
        before = _lineage_rows(connection)
    engine.dispose()

    for target in ("0006", "0005", "0006"):
        if target == "0006":
            command.upgrade(cfg, target)
        else:
            command.downgrade(cfg, target)
        engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
        try:
            with engine.connect() as connection:
                assert _lineage_rows(connection) == before
                assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == target
            inspector = inspect(engine)
            assert "ck_thread_lineage_operation_kind" in {
                item["name"] for item in inspector.get_check_constraints("thread_lineage_operation")}
            assert "ix_thread_lineage_operation_scope_time" in {
                item["name"] for item in inspector.get_indexes("thread_lineage_operation")}
            assert {"ix_thread_lineage_edge_predecessor", "ix_thread_lineage_edge_successor"} <= {
                item["name"] for item in inspector.get_indexes("thread_lineage_edge")}
        finally:
            engine.dispose()


def test_phase3d3a_downgrade_refuses_correction_without_data_loss(isolated_tmp_path):
    cfg = _config(isolated_tmp_path)
    command.upgrade(cfg, "0006")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        first, second = _lineage_conversations(connection, 2)
        _lineage_operation(connection, "correction", "a", [first], [second])
        before = _lineage_rows(connection)
    engine.dispose()

    with pytest.raises(RuntimeError, match="downgrade refused"):
        command.downgrade(cfg, "0005")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.connect() as connection:
            assert _lineage_rows(connection) == before
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0006"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()
