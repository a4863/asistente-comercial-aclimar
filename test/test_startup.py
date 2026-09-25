import subprocess
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app as direct_uvicorn_app, create_app, run
from app.security.single_instance import SingleInstanceError, SingleInstanceLock


def test_app_starts_with_validated_settings():
    settings = Settings(host="127.0.0.1", port=8123, database_url="sqlite:///isolated.db")
    app = create_app(settings)
    assert app.title == "Asistente Comercial ACLIMAR"
    assert app.state.settings is settings
    assert app.state.settings.host == "127.0.0.1"
    assert app.state.operational_lock is None


def test_app_rejects_non_loopback_settings():
    with pytest.raises(ValueError):
        create_app(Settings(host="0.0.0.0"))


def test_controlled_launcher_uses_validated_loopback_settings(monkeypatch):
    calls = []
    monkeypatch.setattr("app.main.uvicorn.run", lambda *args, **kwargs: calls.append((args, kwargs)))
    settings = Settings(host="127.0.0.1", port=8123, database_url="sqlite:///isolated.db")

    run(settings)

    assert len(calls) == 1
    arguments, keywords = calls[0]
    assert arguments[0].state.settings is settings
    assert arguments[0].state.operational_lock is None
    assert keywords == {"host": "127.0.0.1", "port": 8123, "reload": False,
                        "workers": 1, "lifespan": "on"}


def test_controlled_launcher_rejects_non_loopback_settings(monkeypatch):
    monkeypatch.setattr("app.main.uvicorn.run", lambda *args, **kwargs: pytest.fail("must not run"))

    with pytest.raises(ValueError):
        run(Settings(host="0.0.0.0"))


def test_import_and_default_create_app_do_not_acquire_lock(monkeypatch):
    code = (
        "import app.security.single_instance as lock\n"
        "def forbidden(*args, **kwargs): raise AssertionError('lock on import')\n"
        "lock.SingleInstanceLock = forbidden\n"
        "import app.main\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                            text=True, timeout=10)
    assert result.returncode == 0, result.stderr[-500:]

    def forbidden(*_args, **_kwargs):
        pytest.fail("lock acquired by inert app")

    monkeypatch.setattr("app.main.SingleInstanceLock", forbidden)
    inert = create_app()
    assert inert.state.operational_lock is None
    with TestClient(inert) as client:
        assert client.get("/health").json() == {"status": "ok"}
    with TestClient(direct_uvicorn_app) as client:
        assert client.get("/health").json() == {"status": "ok"}
    assert direct_uvicorn_app.state.operational_lock is None


def test_worker_lifespan_holds_one_lock_and_releases_on_shutdown(isolated_tmp_path, monkeypatch):
    database = isolated_tmp_path / "future.db"
    settings = Settings(database_url=f"sqlite:///{database}")
    original = SingleInstanceLock
    created = []

    class TrackingLock:
        def __init__(self, url):
            self.lock = original(url)
            self.acquisitions = 0
            self.closes = 0
            created.append(self)

        def acquire(self):
            self.acquisitions += 1
            self.lock.acquire()

        def close(self):
            self.closes += 1
            self.lock.close()

        @property
        def is_owner(self):
            return self.lock.is_owner

    monkeypatch.setattr("app.main.SingleInstanceLock", TrackingLock)
    app = create_app(settings, _operational=True)
    assert not created and app.state.operational_lock is None
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert len(created) == 1
        assert created[0].acquisitions == 1
        assert app.state.operational_lock is created[0]
        assert app.state.operational_lock.is_owner
        assert not database.exists()
    assert app.state.operational_lock is None
    assert created[0].closes == 1
    assert not created[0].is_owner


def test_second_worker_fails_closed_then_restart_reacquires(isolated_tmp_path):
    database = isolated_tmp_path / "future.db"
    settings = Settings(database_url=f"sqlite:///{database}")
    first = create_app(settings, _operational=True)
    second = create_app(settings, _operational=True)
    with TestClient(first):
        assert first.state.operational_lock.is_owner
        with pytest.raises(SingleInstanceError, match="already_locked"):
            with TestClient(second):
                pytest.fail("second worker became ready")
        assert second.state.operational_lock is None
        assert first.state.operational_lock.is_owner
    assert first.state.operational_lock is None
    with TestClient(create_app(settings, _operational=True)) as restarted:
        assert restarted.app.state.operational_lock.is_owner
    assert not database.exists()


def test_lifespan_has_no_provider_keyring_or_network_side_effects(isolated_tmp_path, monkeypatch):
    import socket

    def forbidden(*_args, **_kwargs):
        pytest.fail("unexpected external access")

    fake_keyring = ModuleType("keyring")
    fake_keyring.get_password = forbidden
    fake_openai = ModuleType("openai")
    fake_openai.OpenAI = forbidden
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    database = isolated_tmp_path / "future.db"
    app = create_app(Settings(database_url=f"sqlite:///{database}"), _operational=True)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
    assert not database.exists()
