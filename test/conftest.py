import gc
import os
import shutil
import stat
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.database import make_session_factory


_RUNTIME_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test-runtime"


def _remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


@pytest.fixture
def isolated_tmp_path():
    _RUNTIME_TMP_ROOT.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="case-", dir=_RUNTIME_TMP_ROOT))
    try:
        yield directory
    finally:
        gc.collect()
        if directory.exists():
            shutil.rmtree(directory, onerror=_remove_readonly)
        try:
            _RUNTIME_TMP_ROOT.rmdir()
        except OSError:
            pass


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
        gc.collect()
