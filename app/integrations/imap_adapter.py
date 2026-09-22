from dataclasses import dataclass
from datetime import date, datetime
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import re
from typing import Callable

from app.config import IMAPSettings
from app.security.credentials import CredentialStore


class IMAPAdapterError(Exception):
    pass


class IMAPCredentialMissingError(IMAPAdapterError):
    pass


class IMAPAuthenticationError(IMAPAdapterError):
    pass


class IMAPConnectionError(IMAPAdapterError):
    pass


class IMAPProtocolError(IMAPAdapterError):
    pass


class IMAPFolderNotAllowedError(IMAPAdapterError):
    pass


class IMAPFolderUnavailableError(IMAPAdapterError):
    pass


class IMAPMessageParseError(IMAPAdapterError):
    pass


@dataclass(frozen=True)
class MailboxFolder:
    name: str
    delimiter: str | None
    flags: tuple[str, ...]


@dataclass(frozen=True)
class SelectedMailbox:
    name: str
    uidvalidity: int | None
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class AttachmentMetadata:
    part_index: int
    filename: str | None
    media_type: str | None
    byte_size: int | None
    content_id: str | None
    disposition: str | None


@dataclass(frozen=True)
class FetchedMessage:
    uid: int
    normalized_message_id: str | None
    sender_address: str | None
    recipient_addresses: tuple[str, ...]
    subject: str | None
    sent_at: datetime | None
    in_reply_to: str | None
    references_header: str | None
    normalized_body: str | None
    body_size_bytes: int
    content_truncated: bool
    attachments: tuple[AttachmentMetadata, ...]


def _default_client_factory(*args, **kwargs):
    from imapclient import IMAPClient

    return IMAPClient(*args, **kwargs)


def _safe_text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _safe_tuple(value) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (_safe_text(value),)
    return tuple(_safe_text(item) for item in value)


def _positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _is_authentication_error(error: Exception) -> bool:
    name = type(error).__name__.lower()
    return "auth" in name or "login" in name


def _response_value(response, field: str):
    if not isinstance(response, dict):
        return None
    requested = _normalise_fetch_key(field)
    for key, value in response.items():
        if _normalise_fetch_key(key) == requested:
            return value
    return None


def _normalise_fetch_key(value) -> str:
    text = _safe_text(value).upper()
    match = re.fullmatch(r"BODY(?:\.PEEK)?\[([^\]]+)\](?:<(\d+)(?:\.\d+)?>)?", text)
    if not match:
        return text
    section, offset = match.groups()
    partial = f"<{offset}>" if offset is not None else ""
    return f"BODY[{section}]{partial}"


def _as_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    raise ValueError("not bytes")


def _optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalise_text(value: str) -> str | None:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]{2,}", " ", value).strip()
    return value or None


class _HTMLToText(HTMLParser):
    _BLOCK_ELEMENTS = {"address", "article", "br", "div", "li", "p", "section", "table", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif tag in self._BLOCK_ELEMENTS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag in self._BLOCK_ELEMENTS:
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._ignored_depth:
            self._parts.append(data)

    def text(self) -> str | None:
        return _normalise_text("".join(self._parts))


def _html_to_text(value: str) -> str | None:
    parser = _HTMLToText()
    parser.feed(value)
    parser.close()
    return parser.text()


def _protocol_text(value) -> str | None:
    if value is None:
        return None
    return _safe_text(value).strip() or None


def _body_parameters(value) -> dict[str, str]:
    if not isinstance(value, (list, tuple)):
        return {}
    pairs = value if all(isinstance(item, (list, tuple)) and len(item) == 2 for item in value) else zip(value[::2], value[1::2])
    return {
        key_text.lower(): value_text
        for key, parameter_value in pairs
        if (key_text := _protocol_text(key)) and (value_text := _protocol_text(parameter_value))
    }


def _body_disposition(value) -> tuple[str | None, dict[str, str]]:
    if not isinstance(value, (list, tuple)) or not value:
        return None, {}
    return _protocol_text(value[0]), _body_parameters(value[1] if len(value) > 1 else None)


def _declared_octets(value) -> int | None:
    try:
        octets = int(value)
    except (TypeError, ValueError):
        return None
    return octets if octets >= 0 else None


def _walk_bodystructure(structure, path: str = "", attachments: list[AttachmentMetadata] | None = None):
    """Traverse IMAPClient BodyData tuples without retaining protocol data."""
    if attachments is None:
        attachments = []
    if not isinstance(structure, (list, tuple)) or not structure:
        raise ValueError("invalid bodystructure")
    if isinstance(structure[0], list):
        candidates = []
        for index, child in enumerate(structure[0], 1):
            child_path = f"{path}.{index}" if path else str(index)
            candidates.extend(_walk_bodystructure(child, child_path, attachments))
        return candidates
    if len(structure) < 7:
        raise ValueError("incomplete bodystructure")
    media_type = _protocol_text(structure[0])
    subtype = _protocol_text(structure[1])
    if not media_type or not subtype:
        raise ValueError("missing body type")
    media_type, subtype = media_type.lower(), subtype.lower()
    parameters = _body_parameters(structure[2])
    content_id = _protocol_text(structure[3])
    declared_size = _declared_octets(structure[6])
    if media_type == "text":
        disposition_index = 9
    elif media_type == "message" and subtype == "rfc822":
        disposition_index = 11
    else:
        disposition_index = 8
    disposition, disposition_parameters = _body_disposition(
        structure[disposition_index] if len(structure) > disposition_index else None
    )
    disposition = disposition.lower() if disposition else None
    filename = disposition_parameters.get("filename") or parameters.get("name")
    content_type = f"{media_type}/{subtype}"
    if media_type == "text" and subtype in {"plain", "html"} and disposition != "attachment":
        return [{"part": path or "1", "subtype": subtype, "size": declared_size or 0}]
    if disposition == "attachment" or filename or media_type != "text":
        attachments.append(
            AttachmentMetadata(
                part_index=len(attachments),
                filename=filename,
                media_type=content_type,
                byte_size=declared_size,
                content_id=content_id,
                disposition=disposition,
            )
        )
    return []


class ReadOnlyIMAPAdapter:
    def __init__(self, settings: IMAPSettings, credential_store: CredentialStore, client_factory: Callable = _default_client_factory):
        self._settings = settings
        self._credential_store = credential_store
        self._client_factory = client_factory
        self._client = None
        self._selected_mailbox: SelectedMailbox | None = None

    def connect(self) -> None:
        try:
            secret = self._credential_store.get_secret(
                self._settings.credential_service,
                self._settings.credential_account,
            )
        except Exception:
            raise IMAPConnectionError("IMAP credential store is unavailable") from None
        if not secret:
            raise IMAPCredentialMissingError("IMAP credential is unavailable")
        try:
            client = self._client_factory(self._settings.host, port=self._settings.port, ssl=True)
        except Exception as error:
            raise IMAPConnectionError("IMAP connection could not be created") from None
        try:
            client.login(self._settings.account, secret)
        except Exception as error:
            try:
                client.logout()
            except Exception:
                pass
            if _is_authentication_error(error):
                raise IMAPAuthenticationError("IMAP authentication failed") from None
            raise IMAPProtocolError("IMAP login failed") from None
        self._client = client

    def disconnect(self) -> None:
        client, self._client = self._client, None
        self._selected_mailbox = None
        if client is not None:
            try:
                client.logout()
            except Exception:
                pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.disconnect()

    def _require_client(self):
        if self._client is None:
            raise IMAPConnectionError("IMAP adapter is not connected")
        return self._client

    def _require_selected_client(self):
        client = self._require_client()
        if self._selected_mailbox is None:
            raise IMAPProtocolError("IMAP mailbox is not selected")
        return client

    def list_folders(self) -> tuple[MailboxFolder, ...]:
        try:
            raw_folders = self._require_client().list_folders()
            return tuple(MailboxFolder(_safe_text(name), _safe_text(delimiter) if delimiter is not None else None, _safe_tuple(flags)) for flags, delimiter, name in raw_folders)
        except IMAPAdapterError:
            raise
        except Exception as error:
            raise IMAPProtocolError("IMAP folder listing failed") from None

    def allowed_folders(self) -> tuple[MailboxFolder, ...]:
        discovered = {folder.name: folder for folder in self.list_folders()}
        return tuple(discovered[name] for name in self._settings.folder_allowlist if name in discovered)

    def select_read_only(self, folder_name: str) -> SelectedMailbox:
        if folder_name not in self._settings.folder_allowlist:
            raise IMAPFolderNotAllowedError("IMAP folder is not allowlisted")
        if folder_name not in {folder.name for folder in self.list_folders()}:
            raise IMAPFolderUnavailableError("IMAP folder is unavailable")
        client = self._require_client()
        try:
            response = client.select_folder(folder_name, readonly=True)
        except Exception as error:
            raise IMAPProtocolError("IMAP folder selection failed") from None
        uidvalidity = _positive_int(response.get(b"UIDVALIDITY", response.get("UIDVALIDITY")))
        capabilities = getattr(client, "capabilities", ())
        try:
            normalized_capabilities = _safe_tuple(capabilities() if callable(capabilities) else capabilities)
        except Exception as error:
            raise IMAPProtocolError("IMAP capability lookup failed") from None
        selected = SelectedMailbox(folder_name, uidvalidity, normalized_capabilities)
        self._selected_mailbox = selected
        return selected

    def search_uids(self, since: date | None = None) -> tuple[int, ...]:
        client = self._require_selected_client()
        criteria = ["ALL"] if since is None else ["SINCE", since]
        try:
            raw_uids = client.search(criteria)
        except Exception:
            raise IMAPProtocolError("IMAP UID search failed") from None
        if not isinstance(raw_uids, (list, tuple)):
            raise IMAPProtocolError("IMAP search returned invalid UIDs")
        uids = tuple(_positive_int(uid) for uid in raw_uids)
        if any(uid is None for uid in uids):
            raise IMAPProtocolError("IMAP search returned invalid UIDs")
        return tuple(uid for uid in uids if uid is not None)

    def _parse_headers(self, raw_headers: bytes):
        try:
            headers = BytesParser(policy=policy.default).parsebytes(raw_headers)
            def addresses(name):
                value = headers.get(name)
                structured = getattr(value, "addresses", ())
                return tuple(address.addr_spec for address in structured if address.addr_spec)

            sender = addresses("From")
            recipients = tuple(address for name in ("To", "Cc", "Bcc") for address in addresses(name))
            sent_at = None
            raw_date = headers.get("Date")
            if raw_date:
                try:
                    sent_at = parsedate_to_datetime(str(raw_date))
                except (TypeError, ValueError, IndexError, OverflowError):
                    sent_at = None
            return {
                "normalized_message_id": _optional_text(headers.get("Message-ID")),
                "sender_address": sender[0] if sender else None,
                "recipient_addresses": recipients,
                "subject": _optional_text(headers.get("Subject")),
                "sent_at": sent_at,
                "in_reply_to": _optional_text(headers.get("In-Reply-To")),
                "references_header": _optional_text(headers.get("References")),
            }
        except Exception:
            raise IMAPMessageParseError("IMAP message headers could not be parsed") from None

    def _fetch_selected_part(self, client, uid: int, candidate: dict):
        limit = self._settings.max_body_bytes
        part = candidate["part"]
        fields = [f"BODY.PEEK[{part}.MIME]", f"BODY.PEEK[{part}]<0.{limit + 1}>"]
        try:
            response = client.fetch([uid], fields)
            item = response.get(uid) if isinstance(response, dict) else None
            mime_headers = _response_value(item, fields[0])
            payload = _response_value(item, fields[1])
            raw_mime_headers = _as_bytes(mime_headers) if mime_headers is not None else b""
            raw_payload = _as_bytes(payload)
            retained = raw_payload[:limit]
            parsed = BytesParser(policy=policy.default).parsebytes(raw_mime_headers + b"\r\n" + retained)
            decoded = parsed.get_payload(decode=True)
            if decoded is None:
                decoded = retained
            charset = parsed.get_content_charset() or "utf-8"
            try:
                body = decoded.decode(charset)
            except (LookupError, UnicodeDecodeError):
                body = decoded.decode("utf-8", errors="replace")
        except IMAPAdapterError:
            raise
        except Exception:
            raise IMAPMessageParseError("IMAP message body could not be parsed") from None
        body = body if candidate["subtype"] == "plain" else _html_to_text(body)
        return _normalise_text(body or ""), min(len(raw_payload), limit), len(raw_payload) > limit or candidate["size"] > limit

    def fetch_messages(self, uids) -> tuple[FetchedMessage, ...]:
        client = self._require_selected_client()
        if isinstance(uids, (str, bytes)) or not isinstance(uids, (list, tuple)):
            raise IMAPProtocolError("IMAP UIDs are invalid")
        normalized_uids = tuple(_positive_int(uid) for uid in uids)
        if any(uid is None for uid in normalized_uids):
            raise IMAPProtocolError("IMAP UIDs are invalid")
        normalized_uids = tuple(uid for uid in normalized_uids if uid is not None)
        if not normalized_uids:
            return ()
        try:
            response = client.fetch(list(normalized_uids), ["BODY.PEEK[HEADER]", "BODYSTRUCTURE"])
        except Exception:
            raise IMAPProtocolError("IMAP message retrieval failed") from None
        if not isinstance(response, dict):
            raise IMAPProtocolError("IMAP message retrieval returned invalid data")
        messages = []
        for uid in normalized_uids:
            item = response.get(uid)
            if not isinstance(item, dict):
                raise IMAPMessageParseError("IMAP message could not be parsed")
            try:
                headers = self._parse_headers(_as_bytes(_response_value(item, "BODY.PEEK[HEADER]")))
                attachments: list[AttachmentMetadata] = []
                candidates = _walk_bodystructure(_response_value(item, "BODYSTRUCTURE"), attachments=attachments)
                candidate = next((value for value in candidates if value["subtype"] == "plain"), None)
                candidate = candidate or next((value for value in candidates if value["subtype"] == "html"), None)
                if candidate is None:
                    body, body_size, truncated = None, 0, False
                else:
                    body, body_size, truncated = self._fetch_selected_part(client, uid, candidate)
                messages.append(FetchedMessage(uid=uid, normalized_body=body, body_size_bytes=body_size, content_truncated=truncated, attachments=tuple(attachments), **headers))
            except IMAPAdapterError:
                raise
            except Exception:
                raise IMAPMessageParseError("IMAP message could not be parsed") from None
        return tuple(messages)
