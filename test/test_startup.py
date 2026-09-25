import subprocess
import sys
from types import ModuleType
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from app.config import Settings
from app.main import app as direct_uvicorn_app, create_app, run
from app.persistence.database import make_session_factory
from app.persistence.models import (
    AnalysisRun, Base, ConfigurationReference, Conversation, SourceRecord,
)
from app.security.single_instance import SingleInstanceError, SingleInstanceLock


def _synthetic_settings(isolated_tmp_path):
    database = isolated_tmp_path / "future.db"
    settings = Settings(database_url=f"sqlite:///{database}")
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return database, settings


def _marker_and_runs(settings):
    factory = make_session_factory(settings.database_url)
    try:
        with factory() as session:
            marker = session.scalar(select(ConfigurationReference).where(
                ConfigurationReference.scope == "phase6_lock_cutover"))
            runs = session.scalars(select(AnalysisRun).order_by(AnalysisRun.id)).all()
            return marker, [(run.id, run.status, run.failure_code) for run in runs]
    finally:
        factory.kw["bind"].dispose()


def _seed_reserved(settings):
    factory = make_session_factory(settings.database_url)
    try:
        with factory.begin() as session:
            source = SourceRecord(source_type="email_message", source_system_scope="imap:one",
                                  stable_external_id=str(uuid4()), provenance="test")
            conversation = Conversation(account_scope="imap:one", stable_key=str(uuid4()),
                                        legacy_status="resolved", provenance="test")
            session.add_all((source, conversation))
            session.flush()
            run = AnalysisRun(account_scope="imap:one", target_source_record_id=source.id,
                              conversation_id=conversation.id, run_version=1,
                              input_digest="a" * 64, contract_version=1, policy_version=1,
                              request_mode="automatic", status="reserved")
            session.add(run)
            session.flush()
            return run.id
    finally:
        factory.kw["bind"].dispose()


def test_app_starts_with_validated_settings():
    settings = Settings(host="127.0.0.1", port=8123, database_url="sqlite:///isolated.db")
    app = create_app(settings)
    assert app.title == "Asistente Comercial ACLIMAR"
    assert app.state.settings is settings
    assert app.state.settings.host == "127.0.0.1"
    assert app.state.operational_lock is None
    assert app.state.operational_ready is False


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
    assert arguments[0].state.operational_ready is False
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
    monkeypatch.setattr("app.main.AnalysisRepository", forbidden)
    inert = create_app()
    assert inert.state.operational_lock is None
    assert inert.state.operational_ready is False
    with TestClient(inert) as client:
        assert client.get("/health").json() == {"status": "ok"}
    with TestClient(direct_uvicorn_app) as client:
        assert client.get("/health").json() == {"status": "ok"}
    assert direct_uvicorn_app.state.operational_lock is None


def test_worker_lifespan_holds_one_lock_and_releases_on_shutdown(isolated_tmp_path, monkeypatch):
    database, settings = _synthetic_settings(isolated_tmp_path)
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
            assert app.state.operational_ready is False
            assert app.state.operational_lock is None
            self.closes += 1
            self.lock.close()

        @property
        def is_owner(self):
            return self.lock.is_owner

    monkeypatch.setattr("app.main.SingleInstanceLock", TrackingLock)
    app = create_app(settings, _operational=True)
    assert not created and app.state.operational_lock is None
    assert app.state.operational_ready is False
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert len(created) == 1
        assert created[0].acquisitions == 1
        assert app.state.operational_lock is created[0]
        assert app.state.operational_lock.is_owner
        assert app.state.operational_ready is True
        marker, runs = _marker_and_runs(settings)
        assert (marker.reference_kind, marker.reference_value) == ("operational_ownership", "v1")
        assert runs == []
        assert database.exists()
    assert app.state.operational_lock is None
    assert app.state.operational_ready is False
    assert created[0].closes == 1
    assert not created[0].is_owner


def test_second_worker_fails_closed_then_restart_reacquires(isolated_tmp_path):
    database, settings = _synthetic_settings(isolated_tmp_path)
    first = create_app(settings, _operational=True)
    second = create_app(settings, _operational=True)
    with TestClient(first):
        assert first.state.operational_lock.is_owner
        with pytest.raises(SingleInstanceError, match="already_locked"):
            with TestClient(second):
                pytest.fail("second worker became ready")
        assert second.state.operational_lock is None
        assert second.state.operational_ready is False
        assert first.state.operational_lock.is_owner
    assert first.state.operational_lock is None
    with TestClient(create_app(settings, _operational=True)) as restarted:
        assert restarted.app.state.operational_lock.is_owner
        assert restarted.app.state.operational_ready is True
    assert database.exists()


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
    database, settings = _synthetic_settings(isolated_tmp_path)
    app = create_app(settings, _operational=True)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
    assert database.exists()


def test_cutover_work_starts_only_after_lock_acquisition(isolated_tmp_path, monkeypatch):
    _, settings = _synthetic_settings(isolated_tmp_path)
    app = create_app(settings, _operational=True)
    original = __import__("app.main", fromlist=["AnalysisRepository"]).AnalysisRepository

    class CheckingRepository(original):
        def establish_cutover_or_recover(self):
            assert app.state.operational_lock.is_owner
            assert app.state.operational_ready is False
            return super().establish_cutover_or_recover()

    monkeypatch.setattr("app.main.AnalysisRepository", CheckingRepository)
    with TestClient(app):
        assert app.state.operational_ready is True
    assert _marker_and_runs(settings)[0] is not None


def test_absent_marker_with_reserved_fails_closed_and_releases_lock(isolated_tmp_path):
    _, settings = _synthetic_settings(isolated_tmp_path)
    run_id = _seed_reserved(settings)
    app = create_app(settings, _operational=True)
    with pytest.raises(RuntimeError, match="startup_recovery_failed"):
        with TestClient(app):
            pytest.fail("legacy reserved run reached readiness")
    assert app.state.operational_ready is False
    assert app.state.operational_lock is None
    assert _marker_and_runs(settings) == (None, [(run_id, "reserved", None)])
    with SingleInstanceLock(settings.database_url) as lock:
        assert lock.is_owner


def test_later_startup_recovers_reserved_once(isolated_tmp_path):
    _, settings = _synthetic_settings(isolated_tmp_path)
    with TestClient(create_app(settings, _operational=True)):
        pass
    run_id = _seed_reserved(settings)
    app = create_app(settings, _operational=True)
    with TestClient(app):
        assert app.state.operational_ready is True
        assert _marker_and_runs(settings)[1] == [(run_id, "failed_retryable", "interrupted")]
    with TestClient(create_app(settings, _operational=True)):
        assert _marker_and_runs(settings)[1] == [(run_id, "failed_retryable", "interrupted")]


def test_recovery_failure_rolls_back_and_releases_lock(isolated_tmp_path, monkeypatch):
    _, settings = _synthetic_settings(isolated_tmp_path)
    with TestClient(create_app(settings, _operational=True)):
        pass
    run_id = _seed_reserved(settings)
    original = __import__("app.main", fromlist=["AnalysisRepository"]).AnalysisRepository

    class FailingRepository(original):
        def establish_cutover_or_recover(self):
            super().establish_cutover_or_recover()
            raise RuntimeError("injected failure before commit")

    monkeypatch.setattr("app.main.AnalysisRepository", FailingRepository)
    app = create_app(settings, _operational=True)
    with pytest.raises(RuntimeError, match="startup_recovery_failed"):
        with TestClient(app):
            pytest.fail("failed recovery reached readiness")
    assert app.state.operational_ready is False
    assert app.state.operational_lock is None
    assert _marker_and_runs(settings)[1] == [(run_id, "reserved", None)]
    with SingleInstanceLock(settings.database_url) as lock:
        assert lock.is_owner
