import logging

import pytest
from sqlalchemy import text

from app.audit import AuditCode, record
from app.persistence.database import make_session_factory
from app.security.session import issue_csrf_token, validate_csrf_token


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_status_page(client):
    assert "Status: ok" in client.get("/").text


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
