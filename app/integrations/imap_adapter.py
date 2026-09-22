from dataclasses import dataclass
from datetime import datetime
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


class ReadOnlyIMAPAdapter:
    def __init__(self, settings: IMAPSettings, credential_store: CredentialStore, client_factory: Callable = _default_client_factory):
        self._settings = settings
        self._credential_store = credential_store
        self._client_factory = client_factory
        self._client = None

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
        return SelectedMailbox(folder_name, uidvalidity, normalized_capabilities)
