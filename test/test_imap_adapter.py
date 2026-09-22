import pytest

from app.config import IMAPSettings
from app.integrations.imap_adapter import IMAPAuthenticationError, IMAPConnectionError, IMAPCredentialMissingError, IMAPFolderNotAllowedError, IMAPFolderUnavailableError, IMAPProtocolError, ReadOnlyIMAPAdapter


class FakeCredentialStore:
    def __init__(self, secret, error=None):
        self.secret = secret
        self.error = error

    def get_secret(self, service, account):
        if self.error:
            raise self.error
        return self.secret


class FakeClient:
    def __init__(self, folders=None, select_response=None, login_error=None):
        self.folders = folders or [((), "/", "INBOX"), ((b"\\Sent",), "/", "Sent")]
        self.select_response = {b"UIDVALIDITY": b"7"} if select_response is None else select_response
        self.login_error = login_error
        self.login_calls, self.select_calls, self.logout_calls = [], [], 0
        self.capabilities = (b"IMAP4rev1", b"UIDPLUS")

    def login(self, account, secret):
        self.login_calls.append((account, secret))
        if self.login_error:
            raise self.login_error

    def logout(self):
        self.logout_calls += 1

    def list_folders(self):
        return self.folders

    def select_folder(self, name, readonly):
        self.select_calls.append((name, readonly))
        return self.select_response


def _adapter(secret="fake-secret", client=None, factory_error=None):
    created = []

    def factory(host, **kwargs):
        if factory_error:
            raise factory_error
        created.append((host, kwargs))
        return client or FakeClient()

    return ReadOnlyIMAPAdapter(IMAPSettings(), FakeCredentialStore(secret), factory), created


def test_connect_uses_tls_and_fake_secret_only_for_login():
    client = FakeClient()
    adapter, created = _adapter(client=client)
    adapter.connect()
    assert created == [("imap.invalid", {"port": 993, "ssl": True})]
    assert client.login_calls == [("alexllopez@aclimar.com", "fake-secret")]


@pytest.mark.parametrize("secret", [None, ""])
def test_missing_or_empty_secret_blocks_client_creation(secret):
    adapter, created = _adapter(secret=secret)
    with pytest.raises(IMAPCredentialMissingError):
        adapter.connect()
    assert created == []


def test_credential_store_failure_is_normalized_without_sensitive_cause():
    adapter = ReadOnlyIMAPAdapter(
        IMAPSettings(),
        FakeCredentialStore(None, RuntimeError("fake-secret backend failure")),
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("factory must not run")),
    )
    with pytest.raises(IMAPConnectionError) as error:
        adapter.connect()
    assert "fake-secret" not in str(error.value)
    assert error.value.__cause__ is None


def test_connection_and_authentication_failures_are_safe():
    adapter, _ = _adapter(factory_error=OSError("fake-secret transport failure"))
    with pytest.raises(IMAPConnectionError) as connection_error:
        adapter.connect()
    assert "fake-secret" not in str(connection_error.value)
    assert connection_error.value.__cause__ is None

    class FakeAuthenticationFailure(Exception):
        pass

    adapter, _ = _adapter(client=FakeClient(login_error=FakeAuthenticationFailure("fake-secret")))
    with pytest.raises(IMAPAuthenticationError) as authentication_error:
        adapter.connect()
    assert "fake-secret" not in str(authentication_error.value)
    assert authentication_error.value.__cause__ is None


def test_generic_login_failure_maps_to_protocol_error_and_cleans_up():
    client = FakeClient(login_error=RuntimeError("protocol"))
    adapter, _ = _adapter(client=client)
    with pytest.raises(IMAPProtocolError):
        adapter.connect()
    assert client.logout_calls == 1
    adapter.disconnect()
    assert client.logout_calls == 1


def test_disconnect_and_context_manager_cleanup():
    client = FakeClient()
    adapter, _ = _adapter(client=client)
    with adapter as connected:
        assert connected is adapter
    assert client.logout_calls == 1
    adapter.disconnect()
    assert client.logout_calls == 1


def test_folders_allowlist_and_readonly_selection():
    client = FakeClient(folders=[((b"\\Inbox",), b"/", b"INBOX"), ((), b"/", b"Other")])
    adapter, _ = _adapter(client=client)
    adapter.connect()
    folders = adapter.list_folders()
    assert folders[0].flags == ("\\Inbox",)
    assert folders[0].delimiter == "/"
    assert folders[0].name == "INBOX"
    assert adapter.allowed_folders() == (folders[0],)
    with pytest.raises(IMAPFolderNotAllowedError):
        adapter.select_read_only("Other")
    with pytest.raises(IMAPFolderUnavailableError):
        adapter.select_read_only("Sent")
    assert client.select_calls == []
    selected = adapter.select_read_only("INBOX")
    assert selected.uidvalidity == 7
    assert selected.capabilities == ("IMAP4rev1", "UIDPLUS")
    assert client.select_calls == [("INBOX", True)]


def test_invalid_or_missing_uidvalidity_is_none_and_no_mutators_are_exposed():
    for response in ({}, {"UIDVALIDITY": "invalid"}, {b"UIDVALIDITY": 0}):
        adapter, _ = _adapter(client=FakeClient(select_response=response))
        adapter.connect()
        assert adapter.select_read_only("INBOX").uidvalidity is None
    adapter, _ = _adapter()
    for name in ("append", "copy", "move", "delete", "rename_folder", "create_folder", "search_uids", "fetch_messages"):
        assert not hasattr(adapter, name)
