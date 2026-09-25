# Phase 6F Blocker — Python Package Discovery

**Status:** BLOCKED / NO LIVE CALL
**Date:** 2026-09-25

## Observed failure

Attempted local editable install:

`C:\Python313\python.exe -m pip install -e .`

failed before installation with setuptools package-discovery error:

`Multiple top-level packages discovered in a flat-layout: ['app', 'skills', 'alembic']`

No live OpenAI call occurred.

## Root cause

The repository's `pyproject.toml` declares:
- project metadata;
- runtime dependencies;
- console scripts;

but does not explicitly configure the build backend/package discovery for the intended Python application package.

Setuptools therefore falls back to automatic flat-layout discovery and refuses to guess among multiple top-level directories.

## Security/operational interpretation

Do not work around this by:
- installing only `keyring` or selected dependencies ad hoc;
- invoking the smoke via a different direct Python/provider path;
- adding repository paths to PYTHONPATH as an operational substitute;
- bypassing the approved console-script entry point.

The packaging contract must be fixed and tested offline first.

Phase 6F remains unexecuted. The prior one-live-call authorization is still unused.
