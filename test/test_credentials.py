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
    assert not hasattr(store, "set_secret")


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
