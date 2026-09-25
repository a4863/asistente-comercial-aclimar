"""Offline tests for the interactive, non-echoing AI credential command."""

import sys
from types import SimpleNamespace

import pytest

from app.config import load_settings
from app.security import credential_cli


@pytest.fixture
def fake_keyring(monkeypatch):
    entries = {}
    calls = []

    def get_password(service, account):
        calls.append(("get", service, account))
        return entries.get((service, account))

    def set_password(service, account, secret):
        calls.append(("set", service, account))
        entries[(service, account)] = secret

    def delete_password(service, account):
        calls.append(("delete", service, account))
        entries.pop((service, account))

    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(
        get_password=get_password, set_password=set_password,
        delete_password=delete_password))
    monkeypatch.setattr(credential_cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    return entries, calls


def test_set_prompts_without_echo_and_replaces_configured_reference(
        fake_keyring, monkeypatch, capsys, caplog):
    entries, calls = fake_keyring
    prompts = []
    secrets = iter(("synthetic-first-secret", "synthetic-second-secret"))

    def getpass(prompt):
        prompts.append(prompt)
        return next(secrets)

    monkeypatch.setattr(credential_cli.getpass, "getpass", getpass)
    reference = (load_settings().ai.credential_service, load_settings().ai.credential_account)
    assert credential_cli.main(["set"]) == 0
    assert credential_cli.main(["set"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "stored\nstored\n"
    assert captured.err == ""
    assert prompts == ["OpenAI API key: "] * 2
    assert entries[reference] == "synthetic-second-secret"
    assert calls == [("set", *reference), ("set", *reference)]
    for secret in ("synthetic-first-secret", "synthetic-second-secret"):
        assert secret not in captured.out + captured.err + caplog.text


def test_status_only_uses_presence_and_never_reads_secret_in_cli(monkeypatch, capsys):
    calls = []

    class PresenceOnly:
        def credential_presence(self, service, account):
            calls.append((service, account))
            return "present"

        def get_secret(self, *_args):
            pytest.fail("CLI must not retrieve a secret")

    monkeypatch.setattr(credential_cli, "KeyringCredentialStore", PresenceOnly)
    assert credential_cli.main(["status"]) == 0
    assert capsys.readouterr().out == "present\n"
    assert calls == [(load_settings().ai.credential_service,
                      load_settings().ai.credential_account)]


def test_status_missing_unavailable_and_delete_repeated_are_bounded(fake_keyring, capsys):
    entries, calls = fake_keyring
    reference = (load_settings().ai.credential_service, load_settings().ai.credential_account)
    assert credential_cli.main(["status"]) == 0
    assert credential_cli.main(["delete"]) == 0
    entries[reference] = "synthetic-secret"
    assert credential_cli.main(["status"]) == 0
    assert credential_cli.main(["delete"]) == 0
    assert credential_cli.main(["delete"]) == 0
    assert capsys.readouterr().out == "missing\nmissing\npresent\ndeleted\nmissing\n"
    assert reference not in entries
    assert ("delete", *reference) in calls


def test_empty_input_and_noninteractive_stdin_never_write(fake_keyring, monkeypatch, capsys):
    entries, calls = fake_keyring
    monkeypatch.setattr(credential_cli.getpass, "getpass", lambda _prompt: "")
    assert credential_cli.main(["set"]) == 1
    monkeypatch.setattr(credential_cli.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert credential_cli.main(["set"]) == 1
    assert capsys.readouterr().out == "invalid_secret\ninteractive_terminal_required\n"
    assert entries == {} and calls == []


def test_bad_arguments_never_echo_a_secret_or_prompt(fake_keyring, monkeypatch, capsys):
    def forbidden(_prompt):
        pytest.fail("unexpected credential prompt")

    monkeypatch.setattr(credential_cli.getpass, "getpass", forbidden)
    assert credential_cli.main(["set", "synthetic-secret-in-argv"]) == 2
    assert credential_cli.main(["--secret", "synthetic-secret-in-argv"]) == 2
    assert credential_cli.main(["--help"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "Usage: asistente-aclimar-credential {set|status|delete}\n"
    assert captured.err == "invalid_command\ninvalid_command\n"
    assert "synthetic-secret-in-argv" not in captured.out + captured.err
    assert fake_keyring == ({}, [])


def test_backend_failures_and_provider_calls_are_absent(fake_keyring, monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail("provider/network must not be called")

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=forbidden))
    monkeypatch.setattr(credential_cli.getpass, "getpass", lambda _prompt: "synthetic-secret")

    class FailingStore:
        def credential_presence(self, *_args):
            raise RuntimeError("synthetic-secret read error")

        def set_secret(self, *_args):
            raise RuntimeError("synthetic-secret write error")

        def delete_secret(self, *_args):
            raise RuntimeError("synthetic-secret delete error")

    monkeypatch.setattr(credential_cli, "KeyringCredentialStore", FailingStore)
    assert credential_cli.main(["status"]) == 1
    assert credential_cli.main(["set"]) == 1
    assert credential_cli.main(["delete"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "unavailable\nunavailable\nunavailable\n"
    assert captured.err == ""
    assert "synthetic-secret" not in captured.out + captured.err


def test_cli_does_not_enable_commercial_gate(fake_keyring, monkeypatch):
    from app.security.activation import CommercialActivationGate

    gate = CommercialActivationGate()
    monkeypatch.setattr(credential_cli.getpass, "getpass", lambda _prompt: "synthetic-secret")
    assert credential_cli.main(["set"]) == 0
    assert credential_cli.main(["status"]) == 0
    assert credential_cli.main(["delete"]) == 0
    assert gate.is_enabled is False
