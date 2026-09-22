from datetime import date

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
    def __init__(self, folders=None, select_response=None, login_error=None, search_result=None, fetch_responses=None):
        self.folders = folders or [((), "/", "INBOX"), ((b"\\Sent",), "/", "Sent")]
        self.select_response = {b"UIDVALIDITY": b"7"} if select_response is None else select_response
        self.login_error = login_error
        self.login_calls, self.select_calls, self.logout_calls = [], [], 0
        self.search_result = [12, 13] if search_result is None else search_result
        self.fetch_responses = list(fetch_responses or [])
        self.search_calls, self.fetch_calls = [], []
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

    def search(self, criteria):
        self.search_calls.append(criteria)
        return self.search_result

    def fetch(self, uids, fields):
        self.fetch_calls.append((uids, fields))
        if not self.fetch_responses:
            raise AssertionError("unexpected fake fetch")
        return self.fetch_responses.pop(0)


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
    for name in ("append", "copy", "move", "delete", "rename_folder", "create_folder"):
        assert not hasattr(adapter, name)


def _selected_adapter(client, max_body_bytes=64):
    adapter, _ = _adapter(client=client)
    adapter._settings = IMAPSettings(max_body_bytes=max_body_bytes)
    adapter.connect()
    adapter.select_read_only("INBOX")
    return adapter


def _headers(**overrides):
    values = {
        "From": "Sender <sender@example.test>",
        "To": "One <one@example.test>, two@example.test",
        "Subject": "=?utf-8?q?Hello_=E2=9C=93?=",
        "Date": "Tue, 02 Jan 2024 12:00:00 +0000",
        "Message-ID": "<message@example.test>",
        "In-Reply-To": "<parent@example.test>",
        "References": "<root@example.test> <parent@example.test>",
    }
    values.update(overrides)
    return b"".join(f"{name}: {value}\r\n".encode() for name, value in values.items()) + b"\r\n"


def _top_response(uid=12, structure=None, headers=None):
    return {uid: {b"BODY[HEADER]": headers or _headers(), b"BODYSTRUCTURE": structure or _single_part(b"text", b"plain", 5)}}


def _body_response(uid=12, part="1", mime=b"Content-Type: text/plain; charset=utf-8\r\n", body=b"hello", length=65):
    return {uid: {f"BODY[{part}.MIME]".encode(): mime, f"BODY[{part}]<0>".encode(): body}}


def _single_part(major, subtype, octets, parameters=None, content_id=None, disposition=None):
    basic = [major, subtype, parameters, content_id, None, b"7BIT", octets]
    if major == b"text":
        return tuple(basic + [0, None, disposition, None, None])
    return tuple(basic + [None, disposition, None, None])


def _multipart(parts, subtype=b"mixed", parameters=None, disposition=None):
    return (parts, subtype, parameters, disposition, None, None)


def test_uid_search_requires_selected_mailbox_and_uses_all_or_since():
    client = FakeClient()
    adapter, _ = _adapter(client=client)
    adapter.connect()
    with pytest.raises(IMAPProtocolError):
        adapter.search_uids()
    adapter.select_read_only("INBOX")
    assert adapter.search_uids() == (12, 13)
    assert adapter.search_uids(date(2024, 1, 2)) == (12, 13)
    assert client.search_calls == [["ALL"], ["SINCE", date(2024, 1, 2)]]


def test_fetch_accepts_generic_uid_iterable():
    client = FakeClient(fetch_responses=[_top_response(), _body_response()])
    adapter = _selected_adapter(client)
    messages = adapter.fetch_messages(uid for uid in [12])
    assert tuple(message.uid for message in messages) == (12,)


def test_invalid_server_or_requested_uids_are_safe_and_do_not_fetch():
    client = FakeClient(search_result=[12, "bad"])
    adapter = _selected_adapter(client)
    with pytest.raises(IMAPProtocolError) as error:
        adapter.search_uids()
    assert error.value.__cause__ is None
    with pytest.raises(IMAPProtocolError):
        adapter.fetch_messages([12, 0])
    assert client.fetch_calls == []


def test_fetch_is_selective_and_normalizes_headers_and_plain_body():
    client = FakeClient(fetch_responses=[_top_response(), _body_response(body=b"hello\r\nworld")])
    adapter = _selected_adapter(client)
    message = adapter.fetch_messages([12])[0]
    assert message.uid == 12
    assert message.normalized_message_id == "<message@example.test>"
    assert message.sender_address == "sender@example.test"
    assert message.recipient_addresses == ("one@example.test", "two@example.test")
    assert message.subject == "Hello \u2713"
    assert message.in_reply_to == "<parent@example.test>"
    assert message.references_header == "<root@example.test> <parent@example.test>"
    assert message.normalized_body == "hello\nworld"
    assert client.fetch_calls[0][1] == ["BODY.PEEK[HEADER]", "BODYSTRUCTURE"]
    assert "BODY.PEEK[1]<0.65>" in client.fetch_calls[1][1]
    assert all("RFC822" not in str(field) and "BODY[]" not in str(field) for _, fields in client.fetch_calls for field in fields)


def test_fetch_prefers_plain_extracts_nested_attachment_metadata_and_never_fetches_attachment():
    structure = _multipart([
        _multipart([
            _single_part(b"text", b"html", 30),
            _single_part(b"text", b"plain", 5),
        ], subtype=b"alternative"),
        _single_part(b"application", b"pdf", 99, parameters=(b"name", b"quote.pdf"), content_id=b"cid-1", disposition=(b"attachment", (b"filename", b"quote.pdf"))),
    ])
    client = FakeClient(fetch_responses=[_top_response(structure=structure), _body_response(part="1.2", body=b"plain")])
    message = _selected_adapter(client).fetch_messages([12])[0]
    assert message.normalized_body == "plain"
    assert message.attachments[0].filename == "quote.pdf"
    assert message.attachments[0].media_type == "application/pdf"
    assert message.attachments[0].part_index == 0
    assert all("pdf" not in str(fields).lower() for _, fields in client.fetch_calls)


def test_html_charset_replacement_and_body_limit_are_safe():
    structure = _single_part(b"text", b"html", 999)
    client = FakeClient(fetch_responses=[_top_response(structure=structure), _body_response(part="1", mime=b"Content-Type: text/html; charset=unknown\r\n", body=b"<p>A &amp; B</p><script>secret</script><style>x</style>extra", length=17)])
    message = _selected_adapter(client, max_body_bytes=16).fetch_messages([12])[0]
    assert message.normalized_body is not None
    assert "secret" not in message.normalized_body
    assert "A & B" in message.normalized_body
    assert message.body_size_bytes == 16
    assert message.content_truncated is True


def test_absent_message_id_and_no_text_part_are_normalized_without_body_fetch():
    structure = _single_part(b"application", b"pdf", 4, parameters=(b"name", b"only.pdf"), disposition=(b"attachment", (b"filename", b"only.pdf")))
    headers = _headers().replace(b"Message-ID: <message@example.test>\r\n", b"")
    client = FakeClient(fetch_responses=[_top_response(structure=structure, headers=headers)])
    message = _selected_adapter(client).fetch_messages([12])[0]
    assert message.normalized_message_id is None
    assert message.normalized_body is None
    assert message.body_size_bytes == 0
    assert len(client.fetch_calls) == 1


def test_text_attachment_uses_text_specific_disposition_index_and_is_not_fetched():
    structure = _multipart([
        _single_part(b"text", b"plain", 20, disposition=(b"attachment", (b"filename", b"notes.txt"))),
        _single_part(b"text", b"html", 8),
    ], subtype=b"alternative")
    client = FakeClient(fetch_responses=[_top_response(structure=structure), _body_response(part="2", mime=b"Content-Type: text/html\r\n", body=b"<p>safe</p>")])
    message = _selected_adapter(client).fetch_messages([12])[0]
    assert message.normalized_body == "safe"
    assert message.attachments[0].filename == "notes.txt"
    assert message.attachments[0].media_type == "text/plain"
    assert all("[1]" not in str(fields) for _, fields in client.fetch_calls[1:])


def test_whole_message_response_key_is_not_accepted_for_a_requested_part():
    client = FakeClient(fetch_responses=[_top_response(), {12: {b"BODY[1.MIME]": b"Content-Type: text/plain\r\n", b"BODY[]": b"not selected"}}])
    with pytest.raises(Exception) as error:
        _selected_adapter(client).fetch_messages([12])
    assert error.value.__cause__ is None


def test_malformed_message_or_bodystructure_is_safe_and_has_no_raw_cause():
    client = FakeClient(fetch_responses=[_top_response(structure=([_single_part(b"text", b"plain", 1)],))])
    with pytest.raises(Exception) as error:
        _selected_adapter(client).fetch_messages([12])
    assert "BODYSTRUCTURE" not in str(error.value)
    assert error.value.__cause__ is None
