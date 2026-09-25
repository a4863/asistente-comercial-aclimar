import sys
from types import SimpleNamespace

import pytest

from app.config import load_settings
from app.security.credentials import KeyringCredentialStore


def test_keyring_credential_store_uses_fake_keyring(monkeypatch):
    calls = []

    def get_password(service, account):
        calls.append((service, account))
        return "fake-secret"

    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(get_password=get_password))

    store = KeyringCredentialStore()
    assert store.get_secret("test.service", "person@example.test") == "fake-secret"
    assert calls == [("test.service", "person@example.test")]
    assert hasattr(store, "set_secret")


def test_keyring_credential_store_returns_none_for_missing_fake_credential(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "keyring",
        SimpleNamespace(get_password=lambda service, account: None),
    )

    assert KeyringCredentialStore().get_secret("test.service", "missing@example.test") is None


def test_ai_and_imap_fake_keyring_references_are_independent(monkeypatch):
    settings = load_settings()
    ai_ref = (settings.ai.credential_service, settings.ai.credential_account)
    imap_ref = (settings.imap.credential_service, settings.imap.credential_account)
    assert ai_ref != imap_ref
    calls = []
    secrets = {ai_ref: "synthetic-ai-secret", imap_ref: "synthetic-imap-secret"}

    def get_password(service, account):
        calls.append((service, account))
        return secrets.get((service, account))

    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(get_password=get_password))
    store = KeyringCredentialStore()
    assert store.get_secret(*ai_ref) == "synthetic-ai-secret"
    assert store.get_secret(*imap_ref) == "synthetic-imap-secret"
    assert calls == [ai_ref, imap_ref]
    secrets.pop(ai_ref)
    assert store.get_secret(*ai_ref) is None
    assert store.get_secret(*imap_ref) == "synthetic-imap-secret"
    assert "synthetic-ai-secret" not in repr(settings)
    assert "synthetic-ai-secret" not in repr(store)


def test_fake_keyring_error_does_not_expose_secret(monkeypatch):
    def get_password(service, account):
        raise RuntimeError("synthetic keyring failure")

    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(get_password=get_password))
    with pytest.raises(RuntimeError) as caught:
        KeyringCredentialStore().get_secret("test.ai", "synthetic")
    assert "synthetic-ai-secret" not in str(caught.value)


@pytest.mark.parametrize("secret,expected", [
    ("synthetic-status-secret", "present"), (None, "missing"), ("", "missing"),
    (object(), "unavailable"),
])
def test_credential_presence_returns_only_bounded_state(monkeypatch, secret, expected):
    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(
        get_password=lambda service, account: secret))
    result = KeyringCredentialStore().credential_presence("test.ai", "synthetic")
    assert result == expected
    assert "synthetic-status-secret" not in result


def test_credential_presence_catches_backend_failure_without_error_text(monkeypatch):
    def fail(_service, _account):
        raise RuntimeError("synthetic-status-secret and backend details")

    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(get_password=fail))
    assert KeyringCredentialStore().credential_presence("test.ai", "synthetic") == "unavailable"


def test_keyring_write_replace_and_bounded_delete_use_one_reference(monkeypatch):
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
    store = KeyringCredentialStore()
    reference = ("test.ai", "synthetic")
    assert store.set_secret(*reference, "synthetic-first-secret") == "stored"
    assert store.set_secret(*reference, "synthetic-second-secret") == "stored"
    assert entries[reference] == "synthetic-second-secret"
    assert store.delete_secret(*reference) == "deleted"
    assert store.delete_secret(*reference) == "missing"
    assert reference not in entries
    assert calls == [
        ("set", *reference), ("set", *reference),
        ("get", *reference), ("delete", *reference), ("get", *reference),
    ]
    assert "synthetic-second-secret" not in repr(store)


def test_keyring_write_rejects_empty_and_backend_failures_are_bounded(monkeypatch):
    calls = []

    def get_password(_service, _account):
        raise RuntimeError("synthetic-secret backend read failure")

    def set_password(*_args):
        calls.append("set")
        raise RuntimeError("synthetic-secret backend write failure")

    def delete_password(*_args):
        calls.append("delete")
        raise RuntimeError("synthetic-secret backend delete failure")

    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(
        get_password=get_password, set_password=set_password,
        delete_password=delete_password))
    store = KeyringCredentialStore()
    assert store.set_secret("test.ai", "synthetic", "") == "invalid_secret"
    assert store.set_secret("test.ai", "synthetic", "   ") == "invalid_secret"
    assert calls == []
    assert store.set_secret("test.ai", "synthetic", "synthetic-secret") == "unavailable"
    assert store.delete_secret("test.ai", "synthetic") == "unavailable"
    assert calls == ["set"]
    assert "synthetic-secret" not in repr(store)


def test_keyring_delete_failure_is_bounded(monkeypatch):
    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(
        get_password=lambda *_args: "synthetic-secret",
        delete_password=lambda *_args: (_ for _ in ()).throw(
            RuntimeError("synthetic-secret delete failure"))))
    assert KeyringCredentialStore().delete_secret("test.ai", "synthetic") == "unavailable"
