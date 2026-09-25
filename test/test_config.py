from pathlib import Path
from types import SimpleNamespace
import ctypes
import stat
from uuid import UUID

import pytest

from app import config
from app.config import RuntimeConfigError, load_operational_settings, load_settings
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


@pytest.fixture
def runtime_file(isolated_tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_windows_local_appdata", lambda: isolated_tmp_path)
    path = isolated_tmp_path / "ACLIMAR" / "Asistente Comercial" / "config.toml"
    path.parent.mkdir(parents=True)
    return path


def _bounded_failure():
    return pytest.raises(RuntimeConfigError, match="^configuration_unavailable$")


def test_canonical_runtime_path_is_fixed_and_cwd_independent(runtime_file, monkeypatch):
    runtime_file.write_text("", encoding="utf-8")
    first = config.operational_config_path()
    monkeypatch.chdir(runtime_file.parent)
    assert config.operational_config_path() == first == runtime_file
    assert load_operational_settings().ai.enabled is False
    assert load_settings().ai.enabled is False


@pytest.mark.parametrize("hresult", [0, -1])
def test_windows_known_folder_api_uses_exact_guid_and_frees_result(
        isolated_tmp_path, monkeypatch, hresult):
    buffer = ctypes.create_unicode_buffer(str(isolated_tmp_path))
    events = []

    def known_folder(guid, flags, token, output):
        raw_guid = bytes(ctypes.cast(guid, ctypes.POINTER(ctypes.c_ubyte * 16)).contents)
        assert raw_guid == UUID("f1b32785-6fba-4fcf-9d55-7b8e7f157091").bytes_le
        assert flags == 0 and token is None
        ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.cast(
            buffer, ctypes.c_void_p).value
        events.append("get")
        return hresult

    def free(pointer):
        assert pointer.value == ctypes.cast(buffer, ctypes.c_void_p).value
        events.append("free")

    shell = SimpleNamespace(SHGetKnownFolderPath=known_folder)
    ole = SimpleNamespace(CoTaskMemFree=free)
    monkeypatch.setattr(config.ctypes, "WinDLL", lambda name, **_kwargs: {
        "shell32": shell, "ole32": ole}[name], raising=False)
    if hresult:
        with _bounded_failure():
            config._windows_local_appdata()
    else:
        assert config._windows_local_appdata() == isolated_tmp_path
    assert events == ["get", "free"]


def test_known_folder_failure_never_uses_environment_fallback(runtime_file, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(runtime_file.parent))
    monkeypatch.setattr(config, "_windows_local_appdata",
                        lambda: (_ for _ in ()).throw(OSError("synthetic-path-secret")))
    with _bounded_failure() as caught:
        load_operational_settings()
    assert "synthetic-path-secret" not in str(caught.value)


@pytest.mark.parametrize("kind", ["missing", "directory", "symlink", "device", "reparse"])
def test_runtime_rejects_nonregular_or_redirected_file(runtime_file, monkeypatch, kind):
    if kind == "directory":
        runtime_file.mkdir()
    elif kind in {"symlink", "device", "reparse"}:
        runtime_file.write_text("", encoding="utf-8")
        original = Path.lstat

        def altered(path):
            info = original(path)
            if path == runtime_file:
                return SimpleNamespace(
                    st_mode=stat.S_IFLNK if kind == "symlink" else (
                        stat.S_IFCHR if kind == "device" else stat.S_IFREG),
                    st_file_attributes=(stat.FILE_ATTRIBUTE_REPARSE_POINT if kind == "reparse" else 0))
            return info

        monkeypatch.setattr(Path, "lstat", altered)
    with _bounded_failure():
        load_operational_settings()


@pytest.mark.parametrize("content", [
    b"\xff", b"[ai]\ninvalid = ", b"[secrets]\napi_key='synthetic-secret'",
    b"api_key='synthetic-secret'", b"[server]\npassword='synthetic-secret'",
    b"[database]\ntoken='synthetic-secret'", b"[imap]\npassword='synthetic-secret'",
    b"[ai]\napi_key='synthetic-secret'", b"[server.extra]\nvalue=1",
    b"[server]\nport=true", b"[database]\nurl=7", b"[imap]\nport=true",
    b"[ai]\nenabled=true", b"[ai]\nenabled=true\nbase_url='https://evil.example/v1'",
])
def test_runtime_parser_fails_bounded_without_value_or_path(runtime_file, content):
    runtime_file.write_bytes(content)
    with _bounded_failure() as caught:
        load_operational_settings()
    assert str(runtime_file) not in str(caught.value)
    assert "synthetic-secret" not in str(caught.value)


def test_runtime_read_failure_is_bounded(runtime_file, monkeypatch):
    runtime_file.write_text("", encoding="utf-8")
    original = Path.read_text

    def unreadable(path, *args, **kwargs):
        if path == runtime_file:
            raise PermissionError("synthetic-secret")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    with _bounded_failure() as caught:
        load_operational_settings()
    assert "synthetic-secret" not in str(caught.value)


def test_runtime_valid_closed_schema_and_allowlisted_ai(runtime_file):
    runtime_file.write_text('''[server]
host = "127.0.0.1"
port = 8123
[database]
url = "sqlite:///synthetic.db"
[imap]
host = "imap.example.test"
port = 993
[ai]
enabled = true
provider = "openai"
model = "gpt-6-sol"
base_url = "https://eu.api.openai.com/v1"
credential_service = "synthetic.ai"
credential_account = "synthetic-user"
''', encoding="utf-8")
    settings = load_operational_settings()
    assert settings.port == 8123 and settings.database_url == "sqlite:///synthetic.db"
    assert settings.imap.host == "imap.example.test"
    assert settings.ai.enabled and settings.ai.base_url == "https://eu.api.openai.com/v1"
    assert (settings.ai.credential_service, settings.ai.credential_account) == (
        "synthetic.ai", "synthetic-user")
