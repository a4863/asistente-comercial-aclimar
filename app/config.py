from dataclasses import dataclass
import tomllib
from pathlib import Path
from urllib.parse import urlsplit


_IMAP_SECRET_KEYS = {
    "password",
    "app_password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}

_AI_KEYS = {
    "enabled", "provider", "model", "base_url", "timeout_seconds", "max_retries",
    "max_output_tokens", "max_request_bytes", "credential_service", "credential_account",
}
_AI_REQUEST_BYTE_CEILING = 160_000  # Phase 5A's fixed local projection ceiling.


@dataclass(frozen=True)
class IMAPSettings:
    host: str = "imap.invalid"
    port: int = 993
    account: str = "alexllopez@aclimar.com"
    account_scope: str = "imap:alexllopez@aclimar.com"
    folder_allowlist: tuple[str, ...] = ("INBOX", "Sent")
    initial_window_days: int = 30
    max_body_bytes: int = 2 * 1024 * 1024
    credential_service: str = "asistente-comercial-aclimar.imap"
    credential_account: str = "alexllopez@aclimar.com"


@dataclass(frozen=True)
class AISettings:
    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-6-sol"
    base_url: str | None = None
    timeout_seconds: int = 60
    max_retries: int = 1
    max_output_tokens: int = 4096
    max_request_bytes: int = _AI_REQUEST_BYTE_CEILING
    credential_service: str = "asistente-comercial-aclimar.ai.openai"
    credential_account: str = "default"


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///assistant.db"
    imap: IMAPSettings = IMAPSettings()
    ai: AISettings = AISettings()


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


def _ai_nonempty(value: object) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("invalid ai configuration")
    return value


def _ai_integer(value: object, *, expected: int | None = None, maximum: int | None = None) -> int:
    if type(value) is not int or value <= 0 or (expected is not None and value != expected) or (
        maximum is not None and value > maximum
    ):
        raise ValueError("invalid ai configuration")
    return value


def _ai_url(value: object) -> str | None:
    if value is None:
        return None
    url = _ai_nonempty(value)
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError:
        raise ValueError("invalid ai configuration") from None
    if (parts.scheme != "https" or not host or parts.username is not None or
            parts.password is not None or parts.query or parts.fragment or
            parts.path not in ("", "/v1") or port is not None or
            "?" in url or "#" in url or "\\" in url or
            host in {"localhost", "127.0.0.1", "::1"} or
            any(char.isspace() for char in url)):
        raise ValueError("invalid ai configuration")
    return url


def _load_ai_settings(values: dict) -> AISettings:
    if set(values) - _AI_KEYS:
        # This rejects unknown and secret-bearing keys without echoing their values/names.
        raise ValueError("invalid ai configuration")
    defaults = AISettings()
    enabled = values.get("enabled", defaults.enabled)
    if type(enabled) is not bool:
        raise ValueError("invalid ai configuration")
    provider = _ai_nonempty(values.get("provider", defaults.provider))
    if provider != "openai":
        raise ValueError("invalid ai configuration")
    model = _ai_nonempty(values.get("model", defaults.model))
    base_url = _ai_url(values.get("base_url", defaults.base_url))
    if enabled and base_url is None:
        raise ValueError("invalid ai configuration")
    return AISettings(
        enabled=enabled, provider=provider, model=model, base_url=base_url,
        timeout_seconds=_ai_integer(values.get("timeout_seconds", defaults.timeout_seconds), expected=60),
        max_retries=_ai_integer(values.get("max_retries", defaults.max_retries), expected=1),
        max_output_tokens=_ai_integer(values.get("max_output_tokens", defaults.max_output_tokens)),
        max_request_bytes=_ai_integer(values.get("max_request_bytes", defaults.max_request_bytes),
                                      maximum=_AI_REQUEST_BYTE_CEILING),
        credential_service=_ai_nonempty(values.get("credential_service", defaults.credential_service)),
        credential_account=_ai_nonempty(values.get("credential_account", defaults.credential_account)),
    )


def load_settings(path: Path | None = None) -> Settings:
    try:
        data = {} if path is None else tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        raise ValueError("invalid TOML configuration") from None
    server, database, imap, ai = (data.get("server", {}), data.get("database", {}),
                                  data.get("imap", {}), data.get("ai", {}))
    host = server.get("host", "127.0.0.1")
    if host != "127.0.0.1":
        raise ValueError("The application must bind only to 127.0.0.1")
    if not isinstance(imap, dict):
        raise ValueError("imap configuration must be a table")
    if not isinstance(ai, dict):
        raise ValueError("invalid ai configuration")
    return Settings(host, int(server.get("port", 8000)),
                    database.get("url", "sqlite:///assistant.db"),
                    _load_imap_settings(imap), _load_ai_settings(ai))
