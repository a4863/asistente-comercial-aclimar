"""Offline synthetic smoke CLI tests; no real keyring, database or provider."""

from types import SimpleNamespace

import pytest

from app.config import AISettings
from app.integrations import ai_smoke_cli
from app.integrations.openai_analysis import OpenAIAnalysisError
from app.security.single_instance import SingleInstanceError


@pytest.fixture
def smoke_fakes(monkeypatch):
    events = []
    settings = SimpleNamespace(ai=AISettings(enabled=True,
                               base_url="https://eu.api.openai.com/v1"),
                               database_url="sqlite:///synthetic-smoke.db")

    class FakeLock:
        def __init__(self, database_url):
            assert database_url == settings.database_url
            events.append("lock_construct")
            self.is_owner = False

        def __enter__(self):
            events.append("lock_acquire")
            self.is_owner = True
            return self

        def __exit__(self, *_exc):
            self.is_owner = False
            events.append("lock_release")

    class FakeAdapter:
        def __init__(self, ai, credentials, *, ownership):
            assert ai is settings.ai
            assert ownership.is_owner is True
            assert isinstance(credentials, FakeCredentials)
            events.append("adapter_construct")

        def smoke(self):
            events.append("smoke")
            return "passed"

    class FakeCredentials:
        pass

    monkeypatch.setattr(ai_smoke_cli, "load_settings", lambda: settings)
    monkeypatch.setattr(ai_smoke_cli, "SingleInstanceLock", FakeLock)
    monkeypatch.setattr(ai_smoke_cli, "KeyringCredentialStore", FakeCredentials)
    monkeypatch.setattr(ai_smoke_cli, "OpenAIAnalysis", FakeAdapter)
    return events, settings


def test_cli_acquires_configured_lock_calls_smoke_once_and_releases(smoke_fakes, capsys):
    events, _settings = smoke_fakes
    assert ai_smoke_cli.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out == "passed\n" and captured.err == ""
    assert events == ["lock_construct", "lock_acquire", "adapter_construct",
                      "smoke", "lock_release"]


def test_cli_rejects_payload_arguments_and_help_is_narrow(smoke_fakes, capsys):
    events, _settings = smoke_fakes
    assert ai_smoke_cli.main(["--payload", "commercial-secret"]) == 2
    assert ai_smoke_cli.main(["commercial-secret"]) == 2
    assert ai_smoke_cli.main(["--help"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "Usage: asistente-aclimar-ai-smoke\n"
    assert captured.err == "invalid_command\ninvalid_command\n"
    assert "commercial-secret" not in captured.out + captured.err
    assert events == []


def test_cli_disabled_never_acquires_lock_or_credentials(smoke_fakes, monkeypatch, capsys):
    events, settings = smoke_fakes
    settings.ai = AISettings()
    assert ai_smoke_cli.main([]) == 1
    assert capsys.readouterr().out == "disabled\n"
    assert events == []


def test_cli_second_owner_failure_prevents_adapter_and_credentials(
        smoke_fakes, monkeypatch, capsys):
    events, _settings = smoke_fakes

    class Locked:
        def __init__(self, _url):
            events.append("lock_construct")

        def __enter__(self):
            events.append("lock_denied")
            raise SingleInstanceError("already_locked")

        def __exit__(self, *_exc):
            pytest.fail("failed acquisition has no entered context")

    monkeypatch.setattr(ai_smoke_cli, "SingleInstanceLock", Locked)
    monkeypatch.setattr(ai_smoke_cli, "KeyringCredentialStore",
                        lambda: pytest.fail("credentials before lock"))
    assert ai_smoke_cli.main([]) == 1
    assert capsys.readouterr().out == "lock_unavailable\n"
    assert events == ["lock_construct", "lock_denied"]


@pytest.mark.parametrize("failure", ["adapter", "credential", "unexpected"])
def test_cli_releases_lock_and_bounds_all_failures(smoke_fakes, monkeypatch, capsys, failure):
    events, _settings = smoke_fakes
    if failure == "adapter":
        class FailingAdapter:
            def __init__(self, *_args, **_kwargs):
                events.append("adapter_construct")

            def smoke(self):
                events.append("smoke")
                raise OpenAIAnalysisError("raw-commercial-secret")

        monkeypatch.setattr(ai_smoke_cli, "OpenAIAnalysis", FailingAdapter)
    elif failure == "credential":
        monkeypatch.setattr(ai_smoke_cli, "KeyringCredentialStore",
                            lambda: (_ for _ in ()).throw(RuntimeError("raw-commercial-secret")))
    else:
        class FailingAdapter:
            def __init__(self, *_args, **_kwargs):
                raise RuntimeError("raw-commercial-secret")

        monkeypatch.setattr(ai_smoke_cli, "OpenAIAnalysis", FailingAdapter)
    assert ai_smoke_cli.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ("smoke_failed\n" if failure == "adapter" else "unavailable\n")
    assert captured.err == ""
    assert "raw-commercial-secret" not in captured.out + captured.err
    assert events[-1] == "lock_release"


def test_cli_has_no_commercial_gate_or_database_session_access(smoke_fakes, monkeypatch):
    import sqlalchemy
    from app.security.activation import CommercialActivationGate

    def forbidden(*_args, **_kwargs):
        pytest.fail("forbidden gate/database access")

    monkeypatch.setattr(sqlalchemy, "create_engine", forbidden)
    monkeypatch.setattr(CommercialActivationGate, "enable", forbidden)
    monkeypatch.setattr(CommercialActivationGate, "disable", forbidden)
    assert ai_smoke_cli.main([]) == 0
