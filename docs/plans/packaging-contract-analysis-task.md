# Packaging Contract Analysis Task — Precondition for Phase 6F

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-25
**Mode:** READ-ONLY

## Objective

Define the smallest safe packaging correction so:

`C:\Python313\python.exe -m pip install -e .`

installs the project and its already-approved dependencies, and registers the existing console scripts:
- `asistente-aclimar`
- `asistente-aclimar-credential`
- `asistente-aclimar-ai-smoke`

without accidentally packaging project support directories.

Do not implement anything in this task.

## Confirmed current state

Current `pyproject.toml` declares:
- project name/version/python requirement;
- dependencies;
- optional pytest dependency;
- three project scripts;
- pytest options.

Editable installation fails because setuptools automatic flat-layout discovery sees:
- `app`
- `skills`
- `alembic`

and refuses to infer intended packages.

## Questions to resolve

1. Which directory/directories are the intended distributable Python packages?
2. Should packaging include only `app` and its Python subpackages?
3. Confirm that `skills`, `docs`, `test`, migration support directories and other repo assets must not become import packages.
4. Does `app` and each required subpackage contain the expected package markers / namespace-compatible structure?
5. What exact `[build-system]` should be declared?
6. What exact setuptools package discovery configuration should be used?
7. Whether package data/templates under `app/web/templates` need explicit inclusion for installed operation.
8. Whether Alembic runtime assets are required by installed operation and, if so, how they should be handled without packaging `alembic` as an import package accidentally.
9. Whether editable and non-editable installation should both succeed.
10. Whether console scripts resolve correctly after installation.
11. Whether installation on Python 3.13 is compatible with current dependency pins.
12. Exact Scope Lock for implementation and tests.
13. Whether a packaging-specific test can validate discovery and console entry points without touching real keyring/OpenAI.
14. Whether fixing packaging requires any dependency change or only metadata/config.

## Preferred properties

Prefer:
- explicit setuptools backend;
- explicit package discovery rooted on `app` only;
- no accidental inclusion of `skills`, `docs`, `test`, or migration directories as import packages;
- inclusion of required Jinja templates/package data;
- no source layout migration;
- no dependency changes unless strictly necessary;
- editable install succeeds;
- wheel build succeeds if practical to test;
- console scripts install and import without network/provider execution.

## STOP conditions

STOP if:
- correct packaging requires repository restructuring;
- an additional dependency is required;
- templates/runtime assets cannot be safely included without a broader design choice;
- Python 3.13 incompatibility requires dependency-version decisions.

## Deliverable

Create only:

`docs/plans/packaging-contract-analysis.md`

Include:
- current-state findings;
- intended distributable package set;
- build backend recommendation;
- package discovery/package-data recommendation;
- excluded directories;
- console-script implications;
- Python 3.13 compatibility findings;
- exact proposed Scope Lock;
- offline validation matrix;
- verdict: READY FOR PLAN or STOP.

No code changes.
No dependency installation.
No OpenAI call.

Commit:

Analyze Python packaging contract

Push only origin/codex-work.
