from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


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
