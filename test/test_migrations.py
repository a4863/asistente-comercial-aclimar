from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


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
        assert {"task", "commitment", "question", "next_step", "alert"} <= tables
        command.downgrade(cfg, "0002")
        tables_after_downgrade = set(inspect(engine).get_table_names())
        assert "source_record" in tables_after_downgrade
        assert {"task", "commitment", "question", "next_step", "alert"}.isdisjoint(
            tables_after_downgrade
        )
        command.upgrade(cfg, "head")
        tables_after_reupgrade = set(inspect(engine).get_table_names())
        assert {"task", "commitment", "question", "next_step", "alert"} <= tables_after_reupgrade
    finally:
        engine.dispose()
