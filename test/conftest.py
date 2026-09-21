from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.database import make_session_factory


@pytest.fixture
def isolated_tmp_path():
    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        yield Path(directory)


@pytest.fixture
def client():
    with TestClient(create_app()) as value:
        yield value


@pytest.fixture
def db_session(isolated_tmp_path):
    factory = make_session_factory(f"sqlite:///{isolated_tmp_path / 'phase2a.db'}")
    from app.persistence.models import Base
    engine = factory.kw["bind"]
    Base.metadata.create_all(engine)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()
