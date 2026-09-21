import pytest

from app.config import Settings
from app.main import create_app


def test_app_starts_with_validated_settings():
    settings = Settings(host="127.0.0.1", port=8123, database_url="sqlite:///isolated.db")
    app = create_app(settings)
    assert app.title == "Asistente Comercial ACLIMAR"
    assert app.state.settings is settings
    assert app.state.settings.host == "127.0.0.1"


def test_app_rejects_non_loopback_settings():
    with pytest.raises(ValueError):
        create_app(Settings(host="0.0.0.0"))
