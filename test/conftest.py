from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def isolated_tmp_path():
    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        yield Path(directory)


@pytest.fixture
def client():
    with TestClient(create_app()) as value:
        yield value
