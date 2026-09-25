# Packaging Contract Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** docs/plans/packaging-contract-plan.md — READY FOR IMPLEMENT
**Purpose:** fix explicit setuptools packaging so editable/wheel metadata can be validated without changing runtime behavior

## Objective

Implement the approved minimal Python packaging contract.

No live OpenAI call, keyring access, dependency installation or application execution is authorized by this task.

## Exact Scope Lock

Modify/create exactly these two files:

1. pyproject.toml
2. test/test_packaging.py

No other tracked file may change.

## pyproject.toml

Keep existing:
- [project]
- [project.optional-dependencies]
- [project.scripts]
- [tool.pytest.ini_options]

unchanged.

Add exactly:

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

Do not:
- alter dependency strings;
- alter script targets;
- add __init__.py files;
- add MANIFEST.in;
- package Alembic revisions;
- add source-layout changes;
- add another build/runtime dependency.

## test/test_packaging.py

Create deterministic offline packaging-contract tests.

At minimum assert:

1. Exact [build-system] values.
2. Exact tool.setuptools include-package-data=false.
3. Exact ordered seven-package include list.
4. namespaces=true.
5. Exact package-data mapping for app.web/templates/*.html.
6. Existing project metadata/dependencies unchanged.
7. Existing optional test dependency unchanged.
8. Existing pytest configuration unchanged.
9. Exact three approved console-script names/targets.
10. setuptools.find_namespace_packages(... include=<declared list>) returns exactly:
   - app
   - app.domain
   - app.integrations
   - app.persistence
   - app.security
   - app.services
   - app.web
11. Explicitly prove absent:
   - skills
   - docs
   - test
   - alembic
   - app.web.templates
12. Provide a wheel-archive inspection helper/test path that can validate:
   - intended app Python files;
   - app/web/templates/status.html present;
   - support directories absent;
   - alembic.ini/revisions absent;
   - exact console_scripts metadata.
13. Default pytest execution must not build/install packages or invoke console scripts.

Use only stdlib + already-installed setuptools/pytest.

## Validation

Run:

python -m pytest test/test_packaging.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- pyproject.toml
- test/test_packaging.py

## Packaging validation

After implementation, perform only packaging metadata/build checks that do not require dependency resolution or real services.

Allowed if available without network:
- wheel build with:
  python -m pip wheel --no-index --no-build-isolation --no-deps -w <temp> .
- disposable editable metadata install with:
  python -m pip install --no-index --no-build-isolation --no-deps -e .

Do not:
- execute console-script bodies;
- access real config;
- access keyring;
- open production SQLite;
- call OpenAI;
- fetch packages from network.

If the local backend lacks a prerequisite, STOP and report it; do not add dependencies or change project metadata beyond this task.

## Acceptance criteria

Packaging correction is acceptable only if:
- focal packaging tests pass;
- full suite passes;
- exact seven-package discovery passes;
- wheel contains status.html;
- support directories and Alembic assets are absent;
- exact three entry points are present;
- diff contains only two authorized files;
- no runtime/provider/credential access occurred.

Do not claim full Python 3.13 runtime dependency compatibility merely from metadata/build success.

## STOP conditions

STOP if:
- any third tracked file is needed;
- template inclusion fails with approved mapping;
- package discovery includes additional packages;
- a dependency/version change is required;
- Alembic must be bundled;
- wheel/editable metadata cannot be validated without broadening scope;
- a real Python 3.13 dependency incompatibility is discovered.

## Completion

Commit:

Implement explicit Python packaging contract

Push only origin/codex-work.
