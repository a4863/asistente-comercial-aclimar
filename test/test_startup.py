import pytest

from app.config import Settings
from app.main import create_app, run


def test_app_starts_with_validated_settings():
    settings = Settings(host="127.0.0.1", port=8123, database_url="sqlite:///isolated.db")
    app = create_app(settings)
    assert app.title == "Asistente Comercial ACLIMAR"
    assert app.state.settings is settings
    assert app.state.settings.host == "127.0.0.1"


def test_app_rejects_non_loopback_settings():
    with pytest.raises(ValueError):
        create_app(Settings(host="0.0.0.0"))


def test_controlled_launcher_uses_validated_loopback_settings(monkeypatch):
    calls = []
    monkeypatch.setattr("app.main.uvicorn.run", lambda *args, **kwargs: calls.append((args, kwargs)))
    settings = Settings(host="127.0.0.1", port=8123, database_url="sqlite:///isolated.db")

    run(settings)

    assert len(calls) == 1
    arguments, keywords = calls[0]
    assert arguments[0].state.settings is settings
    assert keywords == {"host": "127.0.0.1", "port": 8123}


def test_controlled_launcher_rejects_non_loopback_settings(monkeypatch):
    monkeypatch.setattr("app.main.uvicorn.run", lambda *args, **kwargs: pytest.fail("must not run"))

    with pytest.raises(ValueError):
        run(Settings(host="0.0.0.0"))
