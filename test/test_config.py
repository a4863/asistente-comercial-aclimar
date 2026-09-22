from pathlib import Path

import pytest

from app.config import load_settings


def test_defaults_are_loopback():
    settings = load_settings()
    assert settings.host == "127.0.0.1"
    assert settings.imap.port == 993
    assert settings.imap.folder_allowlist == ("INBOX", "Sent")
    assert settings.imap.initial_window_days == 30
    assert settings.imap.max_body_bytes == 2 * 1024 * 1024


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
