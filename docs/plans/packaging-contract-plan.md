# Python packaging contract — implementation plan

**Status:** READY FOR IMPLEMENT (requires explicit approval)

**Date:** 2026-09-25

## 1. Objective and authority

Correct only Python distribution metadata so the current flat-layout project builds as the `app` distribution, includes its Jinja template and registers the existing three console scripts. This plan operationalizes `docs/plans/packaging-contract-plan-task.md` and `docs/plans/packaging-contract-analysis.md`; `AGENTS.md`, `docs/architecture.md`, `docs/security.md` and `docs/testing-strategy.md` remain binding. No runtime behavior, dependency version, migration delivery or live Phase 6F execution is authorized.

## 2. Exact `pyproject.toml` edit

Keep the complete existing `[project]`, `[project.optional-dependencies]`, `[project.scripts]` and `[tool.pytest.ini_options]` tables unchanged, including all dependency strings and `requires-python = ">=3.11"`. Add exactly:

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

The finder must return **exactly** those seven import-package names, with no implicit `app.web.templates` package. `namespaces = true` retains the existing marker-less `app.persistence`, `app.security` and `app.web`; no `__init__.py` or source-layout move is permitted. Explicit `package-data` must place `app/web/templates/status.html` in the wheel, while `include-package-data = false` prevents unrelated data sweep. No `skills`, `docs`, `test`, `alembic`, `alembic.ini` or migration revision may become a Python package or wheel runtime asset. Alembic remains a repository/test migration concern; installed migration provisioning needs another task if later required.

The existing entry-point metadata stays exactly:

```toml
asistente-aclimar = "app.main:run"
asistente-aclimar-credential = "app.security.credential_cli:main"
asistente-aclimar-ai-smoke = "app.integrations.ai_smoke_cli:main"
```

Do not execute any script body to test packaging. A registered entry point does not authorize opening SQLite, keyring or the provider.

## 3. Exact two-file Scope Lock and implementation order

**IN SCOPE:**

1. Modify `pyproject.toml` only to add the four tables above.
2. Create `test/test_packaging.py` for deterministic, offline packaging-contract assertions. Its tests may read repository metadata, run the already-installed setuptools finder and inspect a wheel supplied by an explicit test fixture/path, but may **not** invoke pip installation/build automatically, fetch the network, use real keyring or execute console-script callables.

**OUT OF SCOPE:** every `app/` source/asset, `skills/`, `docs/`, existing tests, `alembic/`, `alembic.ini`, config/SQLite, `MANIFEST.in`, dependency versions, lockfiles, setup files and external systems.

**RESTRICTIONS:** no third tracked file, package-marker addition, `src` relocation, new runtime/build dependency beyond the approved setuptools floor, revision bundling, script-target change, real LocalAppData/keyring/OpenAI access or live smoke. If an expected package/template cannot be delivered with these two files, STOP instead of broadening the Scope Lock.

Implementation sequence: capture current `[project]` tables; add metadata; add static tests; run focal tests; perform separately authorized disposable offline wheel/editable checks; run full offline suite; inspect exact diff and commit only these two paths.

## 4. Required `test/test_packaging.py` assertions

Use `tomllib` to assert:

- `[build-system]` is exactly `requires = ["setuptools>=77.0.3"]`, backend `setuptools.build_meta`;
- `tool.setuptools.include-package-data is False`; finder `where`, ordered exact `include` list and `namespaces is True`; package-data mapping exactly `{"app.web": ["templates/*.html"]}`;
- `[project]` name/version/`requires-python` and exact pre-change dependency list remain unchanged; `[project.optional-dependencies].test` and pytest options remain unchanged;
- `[project.scripts]` has exactly the three approved names and target strings, with no new or modified entry point;
- `setuptools.find_namespace_packages(where=".", include=<declared list>)` yields exactly the seven names; `skills`, `docs`, `test`, `alembic`, `app.web.templates` and any other discovered name are absent. A direct check that `app/web/templates/status.html` exists in source is **not** sufficient evidence of wheel inclusion.

Wheel archive validation is a separate, explicitly invoked offline check. Inspect `*.whl` with `zipfile`: require the intended `app/**/*.py` paths and `app/web/templates/status.html`; reject `skills/`, `docs/`, `test/`, `alembic/`, `alembic.ini`, revision files and accidental `app/web/templates/__init__.py`. Inspect its `*.dist-info/entry_points.txt` with `configparser` and assert the same three `console_scripts` targets. Verify exactly one project wheel is selected; do not execute launchers. Static test code may provide an archive-check helper called only by an explicitly selected wheel test or validation command; the default pytest run must not build or install anything.

## 5. Offline wheel and editable validation procedure

Future implementation validation, **not part of this planning task**:

1. Create a disposable Python 3.13 environment outside the repository, e.g. `C:\Python313\python.exe -m venv --system-site-packages <temp>\venv`, so the installed setuptools 84.0.0 is visible. Check interpreter version and setuptools floor inside it. `--system-site-packages` is only for packaging metadata validation; it does not prove an isolated dependency set. Use an explicit temporary wheel-output directory and no live project DB/config.
2. Build a wheel from the project with that environment's Python using `-m pip wheel --no-index --no-build-isolation --no-deps -w <temp>\wheels .`. Do not fetch packages. If the local backend cannot build a wheel without an additional prerequisite, record the exact missing prerequisite and STOP; do not change project dependencies or tracked files. Inspect the wheel ZIP and entry-point metadata as above. A successful wheel is evidence of build metadata and packaged files, **not** runtime dependency resolution.
3. In a separate disposable Python 3.13 environment with a preinstalled compatible setuptools backend, run `-m pip install --no-index --no-build-isolation --no-deps -e .` only for editable metadata/script registration. Check `importlib.metadata.distribution("asistente-comercial-aclimar")`, its `console_scripts` values and existence of all three generated launchers under that environment's `Scripts` directory. Do not invoke `run()`, `main()` or any script, nor read real config/keyring. This `--no-deps` check **does not** demonstrate that the application can run.
4. Separately, when a complete local wheelhouse is available and installation is authorized, use a fresh disposable Python 3.13 environment with `--no-index --find-links <wheelhouse>` to resolve/install the *unchanged* project requirements (editable or wheel) and run `pip check` plus import-only checks. If the wheelhouse is incomplete, report dependency validation **not performed**, not success. The user's eventual real `C:\Python313\python.exe -m pip install -e .` may require downloaded dependencies; do not run it under this plan without a separate authorization. Never use package-install validation as a pretext for a provider, IMAP or keyring call.

The local Python is 3.13.7; setuptools 84.0.0 is present, while current metadata shows `IMAPClient`, `keyring` and `openai` absent. Thus an offline build/editable **metadata** check is feasible with the existing backend, but full dependency resolution is not established by it. The package index metadata assessed in the analysis indicates no immediate 3.13 incompatibility; actual resolver/import evidence is still required. If a genuine Python 3.13 dependency incompatibility appears, STOP and request a version decision rather than altering pins.

## 6. Validation commands, acceptance and rollback

After the two-file implementation, run `python -m pytest test/test_packaging.py`, then `python -m pytest` using the existing offline test setup. Perform the wheel/editable checks above only in disposable environments; no test may implicitly run pip. Then run `git diff --name-only` and `git diff --check` and inspect the complete diff. Exactly `pyproject.toml` and `test/test_packaging.py` may be staged/committed.

Accept only if static tests and full suite pass; the wheel contains `status.html` and only intended application assets; the exact three scripts register; the seven-package finder set is exact; and wheel/editable metadata results are reported separately from dependency resolution. If wheel build or template inclusion fails, do **not** declare packaging accepted even if editable import from the checkout works.

Rollback of an approved future correction is reverting that two-file commit in a controlled task and reinstalling the prior distribution metadata in any test environment. No database/config/credential rollback is involved. Deleting a disposable validation environment is separate cleanup and never targets production paths. This plan creates no operational database and consumes no Phase 6F live-call authorization.

## 7. STOP findings and verdict

No third file, dependency-version change, package marker, source restructuring or Alembic inclusion is required by the inspected contract. If a future wheel build disproves that, or Python 3.13 resolution fails for an actual compatibility reason, apply STOP under the task's conditions. Do not equate a console script missing from the current global `PATH` with missing entry-point metadata in a correctly installed environment.

**Verdict: READY FOR IMPLEMENT**, subject to explicit approval of this exact two-file Scope Lock and the offline validation procedure. No installation, code change, keyring access or OpenAI call occurred during planning.
