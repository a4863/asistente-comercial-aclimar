from dataclasses import dataclass
import tomllib
from pathlib import Path


_IMAP_SECRET_KEYS = {
    "password",
    "app_password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}


@dataclass(frozen=True)
class IMAPSettings:
    host: str = "outlook.office365.com"
    port: int = 993
    account: str = "alexllopez@aclimar.com"
    account_scope: str = "imap:alexllopez@aclimar.com"
    folder_allowlist: tuple[str, ...] = ("INBOX", "Sent")
    initial_window_days: int = 30
    max_body_bytes: int = 2 * 1024 * 1024
    credential_service: str = "asistente-comercial-aclimar.imap"
    credential_account: str = "alexllopez@aclimar.com"


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///assistant.db"
    imap: IMAPSettings = IMAPSettings()


def _require_nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"imap {field} must not be empty")
    return value


def _load_imap_settings(values: dict) -> IMAPSettings:
    secret_keys = _IMAP_SECRET_KEYS & set(values)
    if secret_keys:
        raise ValueError("imap secrets must not be stored in TOML")
    defaults = IMAPSettings()
    folders = values.get("folder_allowlist", defaults.folder_allowlist)
    if not isinstance(folders, list) and not isinstance(folders, tuple):
        raise ValueError("imap folder_allowlist must be an array")
    if not folders or any(not isinstance(folder, str) or not folder.strip() for folder in folders):
        raise ValueError("imap folder_allowlist must contain non-empty folders")
    if len(set(folders)) != len(folders):
        raise ValueError("imap folder_allowlist must not contain duplicates")
    port = values.get("port", defaults.port)
    initial_window_days = values.get("initial_window_days", defaults.initial_window_days)
    max_body_bytes = values.get("max_body_bytes", defaults.max_body_bytes)
    if not isinstance(port, int) or port <= 0:
        raise ValueError("imap port must be positive")
    if not isinstance(initial_window_days, int) or initial_window_days < 0:
        raise ValueError("imap initial_window_days must be non-negative")
    if not isinstance(max_body_bytes, int) or max_body_bytes <= 0:
        raise ValueError("imap max_body_bytes must be positive")
    return IMAPSettings(
        host=_require_nonempty(values.get("host", defaults.host), "host"),
        port=port,
        account=_require_nonempty(values.get("account", defaults.account), "account"),
        account_scope=_require_nonempty(values.get("account_scope", defaults.account_scope), "account_scope"),
        folder_allowlist=tuple(folders),
        initial_window_days=initial_window_days,
        max_body_bytes=max_body_bytes,
        credential_service=_require_nonempty(values.get("credential_service", defaults.credential_service), "credential_service"),
        credential_account=_require_nonempty(values.get("credential_account", defaults.credential_account), "credential_account"),
    )

def load_settings(path: Path | None = None) -> Settings:
    data = {} if path is None else tomllib.loads(path.read_text(encoding="utf-8"))
    server, database, imap = data.get("server", {}), data.get("database", {}), data.get("imap", {})
    host = server.get("host", "127.0.0.1")
    if host != "127.0.0.1":
        raise ValueError("The application must bind only to 127.0.0.1")
    if not isinstance(imap, dict):
        raise ValueError("imap configuration must be a table")
    return Settings(host, int(server.get("port", 8000)), database.get("url", "sqlite:///assistant.db"), _load_imap_settings(imap))
