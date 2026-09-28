"""Offline distribution contract checks; never build, install or invoke entry points."""

from configparser import ConfigParser
from pathlib import Path
import tomllib
from zipfile import ZipFile

import pytest
from setuptools import find_namespace_packages


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = [
    "app", "app.domain", "app.integrations", "app.persistence", "app.security",
    "app.services", "app.web",
]
SCRIPTS = {
    "asistente-aclimar": "app.main:run",
    "asistente-aclimar-credential": "app.security.credential_cli:main",
    "asistente-aclimar-ai-smoke": "app.integrations.ai_smoke_cli:main",
}
DEPENDENCIES = [
    "fastapi", "uvicorn", "jinja2", "sqlalchemy>=2", "alembic", "IMAPClient",
    "keyring", "openai==3.17.0",
]


def _metadata():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def inspect_wheel_archive(path: Path) -> None:
    """Assert archive contents only; caller explicitly supplies an existing wheel."""
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        assert archive.testzip() is None
        assert {
            "app/__init__.py", "app/config.py", "app/main.py", "app/web/routes.py",
            "app/security/credential_cli.py", "app/integrations/ai_smoke_cli.py",
            "app/web/templates/status.html",
        } <= names
        assert "app/web/templates/__init__.py" not in names
        assert all(name.startswith("app/") or ".dist-info/" in name for name in names)
        assert not any(name.startswith(("skills/", "docs/", "test/", "alembic/")) or
                       name == "alembic.ini" or "/alembic/versions/" in name
                       for name in names)
        entry_files = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        assert len(entry_files) == 1
        entries = ConfigParser()
        entries.read_string(archive.read(entry_files[0]).decode("utf-8"))
        assert set(entries.sections()) == {"console_scripts"}
        assert dict(entries.items("console_scripts")) == SCRIPTS


def test_build_system_and_explicit_package_configuration():
    metadata = _metadata()
    assert metadata["build-system"] == {
        "requires": ["setuptools>=77.0.3"],
        "build-backend": "setuptools.build_meta",
    }
    assert metadata["tool"]["setuptools"] == {
        "include-package-data": False,
        "packages": {"find": {"where": ["."], "include": PACKAGES, "namespaces": True}},
        "package-data": {"app.web": ["templates/*.html"]},
    }


def test_project_dependencies_scripts_and_pytest_contract_unchanged():
    metadata = _metadata()
    assert metadata["project"] == {
        "name": "asistente-comercial-aclimar",
        "version": "0.1.0",
        "requires-python": ">=3.11",
        "dependencies": DEPENDENCIES,
        "optional-dependencies": {"test": ["pytest"]},
        "scripts": SCRIPTS,
    }
    assert metadata["tool"]["pytest"]["ini_options"] == {
        "pythonpath": ["."], "testpaths": ["test"],
    }


def test_namespace_discovery_is_exactly_seven_packages():
    finder = _metadata()["tool"]["setuptools"]["packages"]["find"]
    discovered = find_namespace_packages(where=str(ROOT), include=finder["include"])
    assert set(discovered) == set(PACKAGES)
    assert len(discovered) == len(PACKAGES)
    assert not set(discovered) & {"skills", "docs", "test", "alembic", "app.web.templates"}


def test_jinja_asset_exists_in_source_for_explicit_package_data():
    assert (ROOT / "app" / "web" / "templates" / "status.html").is_file()


def test_archive_inspector_accepts_only_required_assets_and_scripts(isolated_tmp_path):
    wheel = isolated_tmp_path / "synthetic.whl"
    entries = "[console_scripts]\n" + "".join(
        f"{name} = {target}\n" for name, target in SCRIPTS.items())
    with ZipFile(wheel, "w") as archive:
        for name in (
            "app/__init__.py", "app/config.py", "app/main.py", "app/web/routes.py",
            "app/security/credential_cli.py", "app/integrations/ai_smoke_cli.py",
            "app/web/templates/status.html",
        ):
            archive.writestr(name, "synthetic")
        archive.writestr("synthetic-0.1.0.dist-info/entry_points.txt", entries)
    inspect_wheel_archive(wheel)
    with ZipFile(wheel, "a") as archive:
        archive.writestr("alembic/versions/0001.py", "synthetic")
    with pytest.raises(AssertionError):
        inspect_wheel_archive(wheel)
