from alembic.config import Config
from alembic import command


def test_upgrade_empty_database(isolated_tmp_path):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{isolated_tmp_path / 'test.db'}")
    command.upgrade(cfg, "head")
