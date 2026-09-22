import sys
from types import SimpleNamespace

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
