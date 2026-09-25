# Packaging Contract Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-25
**Depends on:** docs/plans/packaging-contract-analysis.md — READY FOR PLAN
**Purpose:** unblock editable installation and Phase 6F without changing application behavior

## Objective

Produce an implementation-ready plan for the minimal Python packaging correction that allows the project to build/install explicitly with setuptools and preserves the existing three console scripts.

Do not implement code in this task.

## Fixed conclusions from analysis

The intended distributable import-package set is exactly:

- app
- app.domain
- app.integrations
- app.persistence
- app.security
- app.services
- app.web

Do not package:
- skills
- docs
- test
- alembic
- app.web.templates as an import package

The runtime Jinja asset that must be included is:

- app/web/templates/status.html

Existing console-script targets remain exactly:

- asistente-aclimar = app.main:run
- asistente-aclimar-credential = app.security.credential_cli:main
- asistente-aclimar-ai-smoke = app.integrations.ai_smoke_cli:main

## Proposed packaging contract to operationalize

The plan should use this exact direction unless code inspection proves a blocker:

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

No dependency-version change is authorized by this planning task.

## Questions the plan must resolve exactly

1. Exact pyproject.toml edits, preserving all existing project metadata/dependencies/scripts/pytest settings.
2. Whether the exact fixed include list above is sufficient for editable and wheel installs.
3. How the plan proves app.web.templates is not discovered as a package while status.html is still included as package data.
4. Exact assertions for package discovery.
5. Exact assertions for console-script metadata.
6. Exact assertions for wheel contents.
7. Exact approach for packaging validation without executing the script bodies.
8. Exact approach for Python 3.13 validation while distinguishing:
   - metadata/build success;
   - script registration;
   - runtime dependency resolution.
9. Whether offline wheel/editable verification can be done with the currently installed build backend and no network.
10. How to handle the later authorized real editable install if runtime dependencies must be downloaded.
11. Exact failure/STOP behavior if template inclusion or namespace discovery differs from expectations.
12. Exact Scope Lock and validation commands.

## Exact expected Scope Lock

Modify/create only:

1. pyproject.toml
2. test/test_packaging.py

If any third tracked file is required, STOP.

## Restrictions

Do not:
- modify application source;
- add __init__.py files;
- move to src-layout;
- modify dependency versions;
- add a runtime dependency;
- change console-script targets;
- package Alembic migrations;
- touch real LocalAppData/config/keyring;
- install dependencies;
- call OpenAI;
- execute the smoke.

## Validation requirements for the future implementation plan

At minimum define checks for:

- tomllib parsing of exact build metadata;
- exact seven-package discovery;
- exclusion of support directories;
- template package-data declaration;
- unchanged project dependencies;
- unchanged three script targets;
- wheel/archive content inspection without external services;
- editable metadata/script registration in an isolated/disposable environment where feasible;
- Python 3.13 compatibility validation clearly separated from live/provider execution;
- full pytest suite;
- git diff --name-only;
- git diff --check.

No packaging test may itself invoke pip install automatically.

## STOP conditions

STOP if:
- correct packaging requires a third file;
- package markers/source relocation become necessary;
- template inclusion cannot be achieved with the narrow package-data mapping;
- dependency-version changes are required;
- Alembic assets prove necessary for installed runtime behavior;
- Python 3.13 exposes an actual dependency incompatibility requiring a version decision.

## Deliverable

Create only:

docs/plans/packaging-contract-plan.md

Include:
- exact metadata contract;
- exact Scope Lock;
- per-file implementation steps;
- exact offline test matrix;
- wheel/editable validation procedure;
- Python 3.13 validation procedure;
- rollback;
- STOP findings;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan Python packaging contract

Push only origin/codex-work.
