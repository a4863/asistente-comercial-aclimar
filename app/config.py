from dataclasses import dataclass
import tomllib
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///assistant.db"

def load_settings(path: Path | None = None) -> Settings:
    data = {} if path is None else tomllib.loads(path.read_text(encoding="utf-8"))
    server, database = data.get("server", {}), data.get("database", {})
    host = server.get("host", "127.0.0.1")
    if host != "127.0.0.1":
        raise ValueError("The application must bind only to 127.0.0.1")
    return Settings(host, int(server.get("port", 8000)), database.get("url", "sqlite:///assistant.db"))
