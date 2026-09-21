from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


def test_upgrade_empty_database(isolated_tmp_path):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{isolated_tmp_path / 'test.db'}")
    command.upgrade(cfg, "head")
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        assert "source_record" in inspect(engine).get_table_names()
        command.downgrade(cfg, "0001")
        command.upgrade(cfg, "head")
    finally:
        engine.dispose()
