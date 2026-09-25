# Phase 6A1 Acceptance — Windows Single-Instance Lock Primitive

**Status:** ACCEPTED
**Date:** 2026-09-25

## Scope

Implemented and accepted:
- `app/security/single_instance.py`
- `test/test_single_instance.py`

Implementation commits:
- `ea934834fe0f272ef9e37ceb5bd262738f1fbd76`
- correction `1a1abff8921d893cb5ff679e0eeac97a0c8e9d4e`

## Accepted behavior

The primitive now:
- derives a deterministic canonical identity from a supported local file-backed SQLite path;
- supports a valid SQLite file path before the DB file itself exists, provided the parent directory exists and is valid;
- preserves the same identity before and after DB creation;
- rejects unsupported/in-memory/URI/device/network/ambiguous forms fail-closed;
- uses an exclusive Windows CreateFileW handle with zero sharing;
- holds a non-inheritable live handle as ownership proof;
- does not use stale sidecar existence, PID or port as ownership evidence;
- releases safely/idempotently;
- supports cross-process exclusivity and reacquisition after normal or forced process exit;
- remains isolated from startup, provider, recovery, routes and activation.

## Validation

User validation on Windows:

`python -m pytest test/test_single_instance.py`
- 14 passed
- 2 skipped
- 1 warning

`python -m pytest`
- 546 passed
- 2 skipped
- 8 warnings

Warnings are known/non-blocking:
- Starlette TestClient/httpx deprecation;
- SQLite datetime adapter deprecations in migration tests.

## Result

**ACCEPTED.**

Phase 6A1 is closed. Proceed to Phase 6A2 only under a new exact Scope Lock.
