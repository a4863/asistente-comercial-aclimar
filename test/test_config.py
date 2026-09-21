from pathlib import Path
import pytest
from app.config import load_settings
def test_defaults_are_loopback(): assert load_settings().host == "127.0.0.1"
def test_non_loopback_rejected(tmp_path: Path):
    p=tmp_path/"x.toml"; p.write_text("[server]\nhost='0.0.0.0'")
    with pytest.raises(ValueError): load_settings(p)
