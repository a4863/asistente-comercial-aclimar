# Python Packaging Contract Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-28

## Scope

Accepted implementation:
- `pyproject.toml`
- `test/test_packaging.py`

Implementation commit:
- `2c07f6325f07b09a13bea691b10032096268d635`

## Accepted behavior

- explicit setuptools build backend is declared;
- package discovery is restricted to exactly:
  - app
  - app.domain
  - app.integrations
  - app.persistence
  - app.security
  - app.services
  - app.web
- `skills`, `docs`, `test`, `alembic` and `app.web.templates` are not import packages;
- `app/web/templates/status.html` is included as package data;
- existing runtime dependency declarations remain unchanged;
- existing three console-script targets remain unchanged;
- wheel/archive contract is covered by offline tests;
- no application source, main, migration code or runtime behavior changed;
- no live provider, real keyring or operational database access occurred.

## Validation

User-reported:
- packaging focal tests: 5 passed;
- full suite: 736 passed, 2 skipped;
- wheel build validated without network;
- editable installation metadata validated without network;
- exact three console scripts registered without executing them;
- commit diff contains only the two approved files.

## Result

**ACCEPTED.**

This removes the package-discovery blocker. Full runtime dependency installation in the selected Python 3.13 interpreter remains an operational step and is not proven by --no-deps metadata validation.
