import logging
import re
import socket
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.audit import AuditCode, record
from app.config import AISettings, IMAPSettings, Settings
from app.main import create_app
from app.persistence.database import make_session_factory
from app.persistence.models import (
    AnalysisRun, Base, Conversation, ConversationMembership, EmailMessage, SourceRecord,
)
from app.security.session import issue_csrf_token, validate_csrf_token
from app.services.email_analysis import FakeAIService


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


@pytest.fixture
def manual_web(isolated_tmp_path):
    settings = Settings(database_url=f"sqlite:///{isolated_tmp_path / 'manual-web.db'}",
                        imap=IMAPSettings(account_scope="imap:web"),
                        ai=AISettings(enabled=True, base_url="https://eu.api.openai.com/v1"))
    factory = make_session_factory(settings.database_url)
    Base.metadata.create_all(factory.kw["bind"])
    with factory() as session, session.begin():
        source = SourceRecord(source_type="email_message", source_system_scope="imap:web",
                              stable_external_id=str(uuid4()), provenance="test")
        conversation = Conversation(account_scope="imap:web", stable_key=str(uuid4()),
                                    legacy_status="resolved", provenance="test")
        session.add_all((source, conversation))
        session.flush()
        source_id = source.id
        session.add_all((EmailMessage(source_record_id=source_id,
                                      sender_address="sender@example.test",
                                      subject="Synthetic quote", normalized_body="PRIVATE BODY",
                                      provenance="test"),
                         ConversationMembership(conversation_id=conversation.id,
                                                source_record_id=source_id,
                                                evidence_type="test", evidence_reference="test")))
    app = create_app(settings)
    app.state.operational_ready = True
    app.state.operational_lock = SimpleNamespace(is_owner=True)
    presence_calls = []
    app.state.credential_store = SimpleNamespace(
        credential_presence=lambda *_args: presence_calls.append("probe") or "present")
    try:
        yield app, factory, source_id, presence_calls
    finally:
        factory.kw["bind"].dispose()


def _action_headers(page, *, origin="http://127.0.0.1:8000"):
    token = re.search(r'id="analysis-action-token" value="([^"]+)"', page.text)
    assert token is not None
    return {"Origin": origin, "X-CSRF-Token": token.group(1)}


def test_manual_selector_is_read_only_bounded_and_safe(manual_web):
    app, factory, source_id, _ = manual_web
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "sender@example.test" in page.text and "Synthetic quote" in page.text
        assert 'data-path="/analysis/email"' in page.text
        assert f'data-source-id="{source_id}"' in page.text
        assert "PRIVATE BODY" not in page.text and "imap:web" not in page.text
        assert "force_reanalysis" not in page.text and "gate.enable" not in page.text
        assert page.headers["cache-control"] == "no-store"
        assert page.headers["referrer-policy"] == "no-referrer"
        assert "credentials: \"same-origin\"" in page.text
        assert "X-CSRF-Token" in page.text
        assert _action_headers(page) == _action_headers(client.get("/"))
    with factory() as session:
        assert session.scalars(select(AnalysisRun)).all() == []


def test_manual_post_gate_off_precedes_reservation_and_credential(manual_web, monkeypatch):
    app, factory, source_id, presence_calls = manual_web
    monkeypatch.setattr("app.web.routes.OpenAIAnalysis", lambda *_args, **_kwargs:
                        pytest.fail("adapter constructed with gate OFF"))
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        presence_calls.clear()
        response = client.post("/analysis/email", json={"source_record_id": source_id},
                               headers=headers)
        assert response.status_code == 403 and response.json() == {"status": "blocked"}
        assert presence_calls == []
    with factory() as session:
        assert session.scalars(select(AnalysisRun)).all() == []


def test_manual_initial_retry_and_replay_use_distinct_posts(manual_web, monkeypatch):
    app, factory, source_id, _ = manual_web
    fake = FakeAIService(fail=True)
    monkeypatch.setattr("app.web.routes.OpenAIAnalysis", lambda *_args, **_kwargs: fake)
    app.state.commercial_gate.enable()
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        payload = {"source_record_id": source_id}
        first = client.post("/analysis/email", json=payload, headers=headers)
        assert first.json() == {"status": "failed_retryable"}
        assert len(fake.calls) == 1
        page = client.get("/")
        assert 'data-path="/analysis/email/retry"' in page.text
        again = client.post("/analysis/email", json=payload, headers=headers)
        assert again.status_code == 409 and again.json() == {"status": "retry_required"}
        assert len(fake.calls) == 1
        fake.fail = False
        retried = client.post("/analysis/email/retry", json=payload, headers=headers)
        assert retried.json() == {"status": "completed"}
        assert len(fake.calls) == 2
        replay = client.post("/analysis/email", json=payload, headers=headers)
        assert replay.json() == {"status": "completed_replay"}
        assert client.post("/analysis/email/retry", json=payload,
                           headers=headers).json() == {"status": "completed_replay"}
        assert len(fake.calls) == 2
        assert "data-path=\"/analysis/email\"" not in client.get("/").text
    with factory() as session:
        assert [row.request_mode for row in session.scalars(select(AnalysisRun))] == ["manual", "manual"]


@pytest.mark.parametrize("header_change", [
    {}, {"X-CSRF-Token": "wrong"}, {"Origin": "http://evil.example:8000"},
    {"Origin": "null"}, {"Origin": "https://127.0.0.1:8000"},
])
def test_manual_post_rejects_invalid_security_before_db_or_credentials(
        manual_web, monkeypatch, header_change):
    app, factory, source_id, presence_calls = manual_web
    app.state.commercial_gate.enable()
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        valid = _action_headers(client.get("/"))
        monkeypatch.setattr("app.web.routes.make_session_factory", lambda *_args:
                            pytest.fail("security failure reached database"))
        presence_calls.clear()
        headers = valid | header_change
        if header_change == {}:
            headers.pop("X-CSRF-Token")
        response = client.post("/analysis/email", json={"source_record_id": source_id},
                               headers=headers)
        assert response.status_code == 403 and response.json() == {"status": "invalid_security"}
        assert presence_calls == []


@pytest.mark.parametrize("body", [
    {}, {"source_record_id": 0}, {"source_record_id": True},
    {"source_record_id": "1"}, {"source_record_id": 1, "force": True},
])
def test_manual_post_rejects_invalid_json_shape(manual_web, body):
    app, _, _, _ = manual_web
    app.state.commercial_gate.enable()
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        response = client.post("/analysis/email", json=body, headers=headers)
        assert response.status_code == 400 and response.json() == {"status": "invalid_request"}


def test_manual_post_rejects_oversize_json_and_wrong_host(manual_web):
    app, _, source_id, _ = manual_web
    app.state.commercial_gate.enable()
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        assert client.post("/analysis/email", content=b"{" + b" " * 300 + b"}",
                           headers=headers | {"Content-Type": "application/json"}).json() == {
                               "status": "invalid_request"}
        assert client.post("/analysis/email", json={"source_record_id": source_id},
                           headers=headers | {"Host": "evil.example:8000"}).status_code == 400


def test_manual_post_rejects_stale_target_and_missing_ownership(manual_web, monkeypatch):
    app, factory, source_id, _ = manual_web
    app.state.commercial_gate.enable()
    fake = FakeAIService()
    monkeypatch.setattr("app.web.routes.OpenAIAnalysis", lambda *_args, **_kwargs: fake)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        app.state.operational_lock.is_owner = False
        assert client.post("/analysis/email", json={"source_record_id": source_id},
                           headers=headers).json() == {"status": "unavailable"}
        app.state.operational_lock.is_owner = True
        with factory() as session, session.begin():
            session.get(SourceRecord, source_id).retention_state = "redacted"
        assert client.post("/analysis/email", json={"source_record_id": source_id},
                           headers=headers).json() == {"status": "invalid_target"}
        assert fake.calls == []


def test_manual_retry_without_prior_and_matching_reservation(manual_web, monkeypatch):
    app, factory, source_id, _ = manual_web
    app.state.commercial_gate.enable()
    fake = FakeAIService()
    monkeypatch.setattr("app.web.routes.OpenAIAnalysis", lambda *_args, **_kwargs: fake)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        assert client.post("/analysis/email/retry", json={"source_record_id": source_id},
                           headers=headers).json() == {"status": "retry_not_available"}
        with factory() as session, session.begin():
            from app.domain.email_analysis import select_analysis_input
            from app.persistence.repositories import AnalysisRepository

            canonical = select_analysis_input(session, "imap:web", source_id)
            conversation_id = session.scalar(select(ConversationMembership.conversation_id).where(
                ConversationMembership.source_record_id == source_id))
            AnalysisRepository(session).reserve_run(
                "imap:web", source_id, conversation_id, canonical.input_digest, 1, 1, "manual")
        for path in ("/analysis/email", "/analysis/email/retry"):
            response = client.post(path, json={"source_record_id": source_id}, headers=headers)
            assert response.status_code == 202 and response.json() == {"status": "in_progress"}
        assert fake.calls == []


@pytest.mark.parametrize("state,expected", [
    ("missing", "credential_missing"), ("unavailable", "credential_unavailable"),
])
def test_manual_post_credential_presence_is_bounded(manual_web, monkeypatch, state, expected):
    app, factory, source_id, _ = manual_web
    app.state.commercial_gate.enable()
    monkeypatch.setattr("app.web.routes.OpenAIAnalysis", lambda *_args, **_kwargs:
                        pytest.fail("missing credential reached adapter"))
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        app.state.credential_store = SimpleNamespace(credential_presence=lambda *_args: state)
        response = client.post("/analysis/email", json={"source_record_id": source_id},
                               headers=headers)
        assert response.status_code == 503 and response.json() == {"status": expected}
    with factory() as session:
        assert session.scalars(select(AnalysisRun)).all() == []


def test_manual_post_technical_disable_and_inert_readiness(manual_web, monkeypatch):
    app, _, source_id, _ = manual_web
    app.state.commercial_gate.enable()
    monkeypatch.setattr("app.web.routes.OpenAIAnalysis", lambda *_args, **_kwargs:
                        pytest.fail("disabled request reached adapter"))
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        app.state.settings = Settings(database_url=app.state.settings.database_url,
                                      imap=app.state.settings.imap, ai=AISettings(enabled=False))
        assert client.post("/analysis/email", json={"source_record_id": source_id},
                           headers=headers).json() == {"status": "disabled"}
        app.state.operational_ready = False
        assert client.post("/analysis/email", json={"source_record_id": source_id},
                           headers=headers).json() == {"status": "unavailable"}


def test_manual_post_provider_failure_does_not_leak_details(manual_web, monkeypatch):
    app, _, source_id, _ = manual_web
    app.state.commercial_gate.enable()

    class FailingFake:
        def analyze(self, _analysis_input):
            raise RuntimeError("RAW SECRET PROVIDER FAILURE")

    monkeypatch.setattr("app.web.routes.OpenAIAnalysis", lambda *_args, **_kwargs: FailingFake())
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        response = client.post("/analysis/email", json={"source_record_id": source_id},
                               headers=headers)
        assert response.json() == {"status": "failed_retryable"}
        assert "RAW SECRET" not in response.text and "PRIVATE BODY" not in response.text


def test_manual_post_rejects_duplicate_json_key(manual_web):
    app, _, _, _ = manual_web
    app.state.commercial_gate.enable()
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        headers = _action_headers(client.get("/"))
        response = client.post("/analysis/email",
                               content=b'{"source_record_id":1,"source_record_id":1}',
                               headers=headers | {"Content-Type": "application/json"})
        assert response.json() == {"status": "invalid_request"}
