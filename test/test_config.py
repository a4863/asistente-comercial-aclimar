from pathlib import Path

import pytest

from app.config import load_settings
from app.integrations.ai_schema import MAX_REQUEST_BYTES


def test_defaults_are_loopback():
    settings = load_settings()
    assert settings.host == "127.0.0.1"
    assert settings.imap.host == "imap.invalid"
    assert settings.imap.port == 993
    assert settings.imap.folder_allowlist == ("INBOX", "Sent")
    assert settings.imap.initial_window_days == 30
    assert settings.imap.max_body_bytes == 2 * 1024 * 1024
    assert settings.ai.enabled is False
    assert settings.ai.provider == "openai"
    assert settings.ai.model == "gpt-6-sol"
    assert settings.ai.base_url is None
    assert settings.ai.timeout_seconds == 60
    assert settings.ai.max_retries == 1
    assert settings.ai.max_output_tokens > 0
    assert settings.ai.max_request_bytes == MAX_REQUEST_BYTES
    assert settings.ai.credential_service != settings.imap.credential_service
    assert settings.ai.credential_account != settings.imap.credential_account


def test_non_loopback_rejected(isolated_tmp_path: Path):
    path = isolated_tmp_path / "x.toml"
    path.write_text("[server]\nhost='0.0.0.0'", encoding="utf-8")
    with pytest.raises(ValueError):
        load_settings(path)


def _load_imap_toml(isolated_tmp_path: Path, imap: str):
    path = isolated_tmp_path / "imap.toml"
    path.write_text(f"[imap]\n{imap}", encoding="utf-8")
    return load_settings(path)


def test_valid_non_secret_imap_configuration(isolated_tmp_path: Path):
    settings = _load_imap_toml(
        isolated_tmp_path,
        """host = "mail.example.test"
port = 1993
account = "person@example.test"
account_scope = "imap:person@example.test"
folder_allowlist = ["INBOX", "Projects"]
initial_window_days = 7
max_body_bytes = 100
credential_service = "test.imap"
credential_account = "person@example.test"
""",
    )
    assert settings.imap.host == "mail.example.test"
    assert settings.imap.port == 1993
    assert settings.imap.folder_allowlist == ("INBOX", "Projects")


@pytest.mark.parametrize(
    "imap",
    [
        'host = ""',
        "port = 0",
        "port = -1",
        'account = ""',
        'account_scope = ""',
        "folder_allowlist = []",
        'folder_allowlist = ["INBOX", "INBOX"]',
        'folder_allowlist = ["INBOX", ""]',
        "initial_window_days = -1",
        "max_body_bytes = 0",
        "max_body_bytes = -1",
    ],
)
def test_invalid_imap_configuration_is_rejected(isolated_tmp_path: Path, imap: str):
    with pytest.raises(ValueError):
        _load_imap_toml(isolated_tmp_path, imap)


@pytest.mark.parametrize(
    "secret_key",
    ["password", "app_password", "secret", "token", "access_token", "refresh_token"],
)
def test_imap_secret_keys_are_rejected(isolated_tmp_path: Path, secret_key: str):
    with pytest.raises(ValueError):
        _load_imap_toml(isolated_tmp_path, f'{secret_key} = "not-a-real-secret"')


def _load_ai_toml(isolated_tmp_path: Path, ai: str):
    path = isolated_tmp_path / "ai.toml"
    path.write_text(f"[ai]\n{ai}", encoding="utf-8")
    return load_settings(path)


def test_valid_non_secret_ai_configuration(isolated_tmp_path: Path):
    settings = _load_ai_toml(isolated_tmp_path, '''enabled = true
provider = "openai"
model = "gpt-6-sol"
base_url = "https://api.openai.com/v1"
timeout_seconds = 60
max_retries = 1
max_output_tokens = 1000
max_request_bytes = 120000
credential_service = "test.ai.openai"
credential_account = "synthetic-profile"
''')
    assert settings.ai.enabled is True
    assert settings.ai.max_output_tokens == 1000
    assert settings.ai.max_request_bytes == 120000
    assert settings.ai.credential_service == "test.ai.openai"
    assert settings.ai.credential_account == "synthetic-profile"
    assert settings.imap.credential_service != settings.ai.credential_service


@pytest.mark.parametrize("key", [
    "api_key", "key", "secret", "token", "access_token", "refresh_token",
    "password", "bearer", "authorization", "unknown_setting",
])
def test_ai_unknown_and_secret_keys_rejected_without_echo(isolated_tmp_path: Path, key: str):
    synthetic = "synthetic-not-a-real-secret"
    with pytest.raises(ValueError) as caught:
        _load_ai_toml(isolated_tmp_path, f'{key} = "{synthetic}"')
    assert synthetic not in str(caught.value) and synthetic not in repr(caught.value)


@pytest.mark.parametrize("ai", [
    'enabled = "true"',
    'provider = "other"',
    'provider = ""',
    'model = ""',
    'credential_service = ""',
    'credential_account = ""',
    'timeout_seconds = true',
    'timeout_seconds = 59',
    'max_retries = false',
    'max_retries = 2',
    'max_output_tokens = false',
    'max_output_tokens = 0',
    'max_output_tokens = -1',
    'max_request_bytes = true',
    'max_request_bytes = 0',
    'max_request_bytes = -1',
    f'max_request_bytes = {MAX_REQUEST_BYTES + 1}',
    'enabled = true',
    'base_url = "http://api.openai.com/v1"',
    'base_url = "https://user:pass@api.openai.com/v1"',
    'base_url = "https://api.openai.com/v1?key=synthetic"',
    'base_url = "https://api.openai.com/v1#fragment"',
    'base_url = "https://api.openai.com/v1?"',
    'base_url = "https://api.openai.com/v1#"',
    'base_url = "https:///v1"',
    'base_url = "https://localhost/v1"',
    'base_url = "https://api.openai.com/other"',
])
def test_invalid_ai_configuration_rejected(isolated_tmp_path: Path, ai: str):
    with pytest.raises(ValueError, match="invalid ai configuration"):
        _load_ai_toml(isolated_tmp_path, ai)


def test_non_table_ai_and_malformed_toml_do_not_echo_secret(isolated_tmp_path: Path):
    with pytest.raises(ValueError, match="invalid ai configuration"):
        _load_ai_toml(isolated_tmp_path, 'not_relevant = 1')
    path = isolated_tmp_path / "malformed.toml"
    path.write_text('[ai]\napi_key = "synthetic-secret"\ninvalid = ', encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        load_settings(path)
    assert "synthetic-secret" not in str(caught.value)


def test_settings_repr_contains_no_secret_value(isolated_tmp_path: Path):
    settings = _load_ai_toml(isolated_tmp_path,
                             'credential_service = "test.ai"\ncredential_account = "synthetic"')
    assert "synthetic-not-a-real-secret" not in repr(settings)
