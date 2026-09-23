from alembic.config import Config
from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text


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
