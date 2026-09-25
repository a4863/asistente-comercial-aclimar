# Python packaging contract — analysis

**Status:** READY FOR PLAN (no implementation authorized)

**Date:** 2026-09-25

## 1. Objective and context

Define the smallest explicit packaging contract for the existing ACLIMAR application so an installation with the intended `C:\Python313\python.exe` can register its three current console scripts and install the already-declared runtime dependencies. The reported editable-install failure comes from setuptools' automatic flat-layout discovery seeing multiple top-level directories (`app`, `skills`, `alembic`). No dependency, package, credential, database or provider operation was changed or executed in this analysis.

## 2. Interpretation and documentation consulted

This is packaging metadata plus offline packaging tests, not a source-layout migration or permission to perform the installation now. Reviewed `AGENTS.md`, `docs/plans/packaging-contract-analysis-task.md`, `pyproject.toml`, relevant `app/` and `alembic/` file names, `app/web/routes.py`, `test/test_migrations.py`, `alembic.ini`, `docs/architecture.md`, `docs/security.md` and `docs/testing-strategy.md`. The functional specification and data model do not add packaging requirements. Consulted primary [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/), [setuptools package discovery](https://setuptools.pypa.io/en/stable/userguide/package_discovery.html), [setuptools package data](https://setuptools.pypa.io/en/stable/userguide/datafiles.html) and [pip build-system guidance](https://pip.pypa.io/en/stable/reference/build-system/) for the proposed metadata and offline verification. No required project document was missing.

## 3. Current project state and distributable package set

- `pyproject.toml` has `[project]` metadata, `requires-python = ">=3.11"`, runtime dependencies, `[project.optional-dependencies] test = ["pytest"]`, three `[project.scripts]`, and pytest configuration, but no `[build-system]` or explicit package finder.
- `app/__init__.py`, `app/domain/__init__.py`, `app/integrations/__init__.py` and `app/services/__init__.py` exist. `app/persistence`, `app/security` and `app/web` contain Python modules but no `__init__.py`; they are importable implicit namespace subpackages. `app/web/templates/status.html` is a non-Python runtime asset: `app/web/routes.py` resolves `Path(__file__).parent / "templates"` and renders it with Jinja.
- The exact intended import-package set today is `app`, `app.domain`, `app.integrations`, `app.persistence`, `app.security`, `app.services`, `app.web`. A read-only `setuptools.find_namespace_packages(where=".", include=[these exact names])` returns that set on this checkout. A broad `include=["app", "app.*"]` additionally discovers `app.web.templates` as an implicit namespace package, so a fixed exact include list is safer.
- `skills`, `docs`, `test`, `alembic` and other top-level project support directories are **not** distributable import packages. `alembic.ini` points to repository-relative `alembic`; `test/test_migrations.py` invokes it under the source checkout. No inspected production `app/` module invokes Alembic or needs its revision scripts at import/startup. Installed migration provisioning is a separate future deployment concern, not authority to package `alembic` accidentally.
- The current three scripts already target `app.main:run`, `app.security.credential_cli:main` and `app.integrations.ai_smoke_cli:main`. Packaging should preserve these exact targets and never execute them during import/metadata inspection.

## 4. Recommended exact build and discovery contract

Add to `pyproject.toml` without changing `[project.dependencies]` or script targets:

```toml
[build-system]
requires = ["setuptools>=77.0.3"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
include-package-data = false

[tool.setuptools.packages.find]
where = ["."]
include = ["app", "app.domain", "app.integrations", "app.persistence", "app.security", "app.services", "app.web"]
namespaces = true

[tool.setuptools.package-data]
"app.web" = ["templates/*.html"]
```

`setuptools>=77.0.3` follows the current PyPA setuptools build-system example; the local Python 3.13 interpreter has setuptools 84.0.0. The build backend's wheel/editable hooks are provided by setuptools; `wheel` need not be declared as a separate build requirement absent a demonstrated need. `namespaces = true` is necessary because three selected subpackages lack package markers. The fixed include list prevents accidental import-package discovery of `skills`, `docs`, `test`, `alembic` and `app.web.templates`; `include-package-data = false` avoids sweeping in unrelated repository assets, while the narrow package-data mapping includes `app/web/templates/status.html` in a wheel. Setuptools documents implicit-namespace discovery and explicit package-data mapping in `pyproject.toml`.

Do not add `__init__.py`, relocate code, add `MANIFEST.in`, bundle Alembic scripts, alter dependency versions or change UI/template behavior in this correction. If a wheel inspection shows the Jinja asset missing, STOP and revise the package-data contract under separate approval rather than silently broadening distribution contents.

## 5. Python 3.13 and dependency findings

The selected interpreter is `C:\Python313\python.exe`, Python 3.13.7, with pip 25.2 and setuptools 84.0.0. FastAPI, Uvicorn, Jinja2, SQLAlchemy and Alembic are present there, but `wheel`, `IMAPClient`, `keyring` and `openai` distribution metadata are absent. This explains why direct `import keyring` failed; it does **not** prove a 3.13 incompatibility. The pinned [OpenAI SDK 3.17.0](https://pypi.org/project/openai/3.17.0/) declares Python >=3.10 and a Python 3.13 classifier. The current [keyring](https://pypi.org/project/keyring/) metadata declares Python >=3.9 and a universal wheel; current [IMAPClient](https://pypi.org/project/IMAPClient/) metadata declares Python >=3.8 and a universal wheel. These are compatibility indications, not proof that the entire transitive dependency graph resolves in this particular environment. No contrary metadata requiring a dependency-version decision was found. Actual install/resolution must be validated in the future implementation task without a live provider/keyring call.

The exact production command `C:\Python313\python.exe -m pip install -e .` may need network access to resolve missing dependencies; this analysis does **not** run it or claim an offline install will succeed without a prepared wheelhouse. Use an isolated interpreter/environment and locally available wheels for strictly offline packaging validation; do not silently change dependency pins to compensate for an incomplete cache.

## 6. Proposed implementation and exact Scope Lock

**IN SCOPE — future correction, exactly two files:**

1. Modify `pyproject.toml`: add the exact build-system, narrow namespace finder and explicit Jinja package data above; leave dependency/script/pytest metadata intact.
2. Create `test/test_packaging.py`: standard-library-only contract checks for the TOML metadata, exact discovered package set, exclusion of support directories, template availability and unchanged script targets. It must not import a real keyring, run a script body, query SQLite or call OpenAI.

**OUT OF SCOPE:** all `app/` implementation files, `alembic/`, `alembic.ini`, `skills/`, `docs/` other than this authorized analysis, existing tests, dependency constraints, real config/credentials, database and external services.

**RESTRICTIONS:** no package-marker additions, source-layout move, new runtime dependency, migration, live smoke, real keyring lookup or provider request. If a correct package requires a third tracked file or inclusion of Alembic runtime assets, STOP for a new decision.

Implementation order after approval: add metadata; add static packaging-contract test; verify package finder; build/inspect an isolated wheel and editable installation offline; run existing offline tests and inspect exact diff. This analysis is not that approval.

## 7. Offline validation and acceptance matrix

- Parse `pyproject.toml` with `tomllib` and assert exact `[build-system]`, `tool.setuptools` finder/data mapping, unchanged dependency declarations and the three entry-point strings. Use `setuptools.find_namespace_packages` to assert the exact seven-name set; explicitly assert `skills`, `docs`, `test`, `alembic` and `app.web.templates` are absent. Do not execute the console scripts.
- In a disposable environment using the same Python 3.13 interpreter, with a pre-staged local wheelhouse or already installed build/runtime requirements, build a non-editable wheel without fetching from the index (for example pip wheel/build with `--no-index --no-build-isolation --no-deps` where suitable). Inspect the wheel archive: only intended `app/**` Python modules, required `app/web/templates/status.html` and metadata/scripts; no top-level support directories or Alembic revisions. Verify the installed wheel can resolve the template relative to `app.web.routes.__file__`.
- Separately validate `C:\Python313\python.exe -m pip install -e .` when dependency installation is authorized and available; for strictly offline verification use a disposable environment with `--no-index`, a complete local wheelhouse and preinstalled build backend, or `--no-build-isolation --no-deps` for *metadata/script registration only*. The latter does **not** prove all runtime dependencies are installed. Inspect distribution metadata `console_scripts`, confirm the three generated launchers are on that environment's Scripts path and import their callable targets without invoking `run()`/`main()`; no keyring, SQLite or OpenAI action.
- Run `python -m pytest test/test_packaging.py` and then the existing full offline suite when implementation is authorized. `git diff --name-only` must show only the two Scope-Locked files; `git diff --check` must pass. No test may install packages automatically or depend on network.

Acceptance: editable metadata and wheel can be built with the explicit backend, only the seven intended import packages are discovered, the Jinja template is present in the wheel, all three console entry points resolve, Python 3.13 offline checks pass, and no real secret/provider/DB access occurs. Actual dependency resolution and any CLI use remain separate operational gates.

## 8. Dependencies, risks, ambiguities and out-of-scope discoveries

Dependencies: existing setuptools build backend (local 84.0.0), pip for future validation, and the already-declared project runtime dependencies. No additional dependency is justified. Principal risks: broad namespace discovery packaging support directories or template folder as an import package; omitting `status.html` from a wheel; confusing editable source-tree behavior with wheel contents; console scripts being absent from `PATH` even when registered in another interpreter; assuming Python compatibility from `requires-python` alone; accidental provider/keyring execution during smoke-like tests. The proposed narrow finder, package-data assertion and isolated validation address them.

**Ambiguities:** None requiring a product/security/model decision for an analysis. The installed runtime's need for Alembic migration provisioning remains outside this packaging correction because current production imports do not invoke it. If future deployment explicitly requires migration scripts inside the wheel, that is a new scope and must STOP.

**OUT-OF-SCOPE DISCOVERY:** Python 3.13 currently lacks installed `keyring`, `IMAPClient` and `openai`; packaging metadata correction alone will not populate those in the interpreter. Also, `alembic.ini` uses a checkout-relative script path and default database URL; it is not a safe installed migration contract. Neither is modified here.

## 9. Result

**READY FOR PLAN.** The metadata and tests can be planned within the proposed two-file Scope Lock without changing dependencies, restructuring the repository or using real services. No installation, code change, credential access or OpenAI call was performed.
