import logging
import socket
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit import AuditCode, record
from app.config import AISettings, Settings
from app.main import create_app
from app.persistence.database import make_session_factory
from app.security.session import issue_csrf_token, validate_csrf_token


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_get_routes_reject_foreign_host_without_exposing_status():
    app = create_app(Settings())
    app.state.credential_store = SimpleNamespace(
        credential_presence=lambda *_args: pytest.fail("foreign Host reached status"))
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        assert client.get("/health").status_code == 200
        for path in ("/health", "/"):
            response = client.get(path, headers={"Host": "evil.example:8000"})
            assert response.status_code == 400


def test_status_does_not_expose_session_or_csrf_material():
    app = create_app(Settings())
    app.state.credential_store = SimpleNamespace(credential_presence=lambda *_args: "missing")
    secret = app.user_middleware[0].kwargs["secret_key"]
    with TestClient(app) as client:
        response = client.get("/")
        assert client.post("/").status_code == 405
    assert response.status_code == 200
    assert secret not in response.text
    assert "csrf_token" not in response.text and "aclimar_session" not in response.text


def test_status_page(client):
    client.app.state.credential_store = SimpleNamespace(
        credential_presence=lambda service, account: "missing")
    assert "Status: ok" in client.get("/").text


@pytest.mark.parametrize("url,expected", [
    ("https://api.openai.com/v1", "global"),
    ("https://eu.api.openai.com/v1", "eu"),
    (None, "unknown"),
    ("https://other.example/v1", "unknown"),
])
def test_status_shows_bounded_local_ai_state_and_endpoint_class(url, expected):
    settings = Settings(ai=AISettings(enabled=True, provider="openai", model="gpt-6-sol",
                                     base_url=url))
    app = create_app(settings)
    app.state.credential_store = SimpleNamespace(
        credential_presence=lambda service, account: "present")
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "AI</dt><dd>enabled" in response.text
    assert "Provider</dt><dd>openai" in response.text
    assert "Model</dt><dd>gpt-6-sol" in response.text
    assert f"Endpoint class</dt><dd>{expected}" in response.text
    assert "Credential</dt><dd>present" in response.text
    assert "Commercial authorization</dt><dd>blocked" in response.text
    assert "Operational</dt><dd>inactive" in response.text
    assert "Synthetic smoke</dt><dd>pending" in response.text
    assert "https://api.openai.com" not in response.text


def test_status_defaults_disabled_and_gate_read_does_not_mutate_it():
    app = create_app(Settings())
    app.state.credential_store = SimpleNamespace(
        credential_presence=lambda service, account: "missing")
    with TestClient(app) as client:
        assert "AI</dt><dd>disabled" in client.get("/").text
        assert "Commercial authorization</dt><dd>blocked" in client.get("/").text
        assert app.state.commercial_gate.is_enabled is False
        app.state.commercial_gate.enable()
        assert "Commercial authorization</dt><dd>authorized" in client.get("/").text
        assert app.state.commercial_gate.is_enabled is True
    assert create_app(Settings()).state.commercial_gate.is_enabled is False


@pytest.mark.parametrize("state,expected", [
    ("missing", "missing"), ("unavailable", "unavailable"),
    ("synthetic-status-secret", "unavailable"),
])
def test_status_credential_state_is_whitelisted(state, expected):
    app = create_app(Settings())
    app.state.credential_store = SimpleNamespace(
        credential_presence=lambda service, account: state)
    with TestClient(app) as client:
        response = client.get("/")
    assert f"Credential</dt><dd>{expected}" in response.text
    assert "synthetic-status-secret" not in response.text


def test_status_credential_error_and_external_calls_are_bounded(monkeypatch, caplog):
    def forbidden(*_args, **_kwargs):
        pytest.fail("provider/network must not be called")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=forbidden))
    app = create_app(Settings(ai=AISettings(enabled=True,
                              base_url="https://eu.api.openai.com/v1")))

    def fail(_service, _account):
        raise RuntimeError("synthetic-status-secret and raw keyring error")

    app.state.credential_store = SimpleNamespace(credential_presence=fail)
    with caplog.at_level(logging.DEBUG):
        with TestClient(app) as client:
            response = client.get("/")
            assert client.get("/health").json() == {"status": "ok"}
    assert "Credential</dt><dd>unavailable" in response.text
    assert "synthetic-status-secret" not in response.text + caplog.text


def test_import_and_inert_composition_never_read_credential(monkeypatch):
    from app.security.credentials import KeyringCredentialStore

    def forbidden(*_args, **_kwargs):
        pytest.fail("credential looked up before status request")

    monkeypatch.setattr(KeyringCredentialStore, "get_secret", forbidden)
    app = create_app(Settings())
    assert app.state.commercial_gate.is_enabled is False
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_csrf_token_is_reused_per_session_and_rejects_invalid_token():
    session: dict[str, str] = {}
    token = issue_csrf_token(session)
    assert token == issue_csrf_token(session)
    assert validate_csrf_token(session, token)
    assert not validate_csrf_token(session, "invalid-token")


def test_audit_rejects_arbitrary_sensitive_payload(caplog):
    secret = "secret-commercial-payload"
    with caplog.at_level(logging.INFO, logger="aclimar.audit"):
        record(AuditCode.APPLICATION_STARTED)
    assert AuditCode.APPLICATION_STARTED.value in caplog.text
    with pytest.raises(ValueError):
        record(secret)  # type: ignore[arg-type]
    assert secret not in caplog.text


def test_session_factory_uses_isolated_sqlite_sessions(isolated_tmp_path):
    factory = make_session_factory(f"sqlite:///{isolated_tmp_path / 'assistant-test.db'}")
    first_session = factory()
    second_session = factory()
    try:
        assert first_session is not second_session
        assert first_session.execute(text("SELECT 1")).scalar_one() == 1
        assert second_session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        first_session.close()
        second_session.close()
        factory.kw["bind"].dispose()
