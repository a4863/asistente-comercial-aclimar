# Phase 6A3 Acceptance — Cutover Marker and Startup Recovery

**Status:** ACCEPTED
**Date:** 2026-09-25

## Scope

Accepted implementation:
- `app/persistence/repositories.py`
- `app/main.py`
- `test/test_persistence_repositories.py`
- `test/test_startup.py`

Implementation commit:
- `61e2cb03be4023af2874d3ed8e1db272647a798f`

## Accepted behavior

- startup acquires the operational single-instance lock before any cutover/recovery work;
- persistent cutover marker reuses existing `ConfigurationReference`;
- marker absent + zero reserved runs -> marker is created atomically;
- marker absent + any reserved run -> startup fails closed, creates no marker, mutates no run;
- marker present + reserved runs -> only `reserved` rows transition to `failed_retryable / interrupted`;
- completed/stale_retryable/failed_retryable rows are untouched;
- malformed/conflicting marker fails closed;
- no age/PID/heartbeat heuristic is used;
- transaction commit/rollback keeps marker and recovery atomic;
- operational readiness becomes true only after successful recovery commit;
- startup failure leaves readiness false and releases the lock;
- inert import/default create_app performs no recovery;
- no migration/model/provider/credential/route activation change was introduced.

## Validation

User validation on Windows:

`python -m pytest test/test_persistence_repositories.py test/test_startup.py`
- 107 passed
- 1 warning

`python -m pytest`
- 561 passed
- 2 skipped
- 8 warnings

Warnings are known/non-blocking:
- Starlette TestClient/httpx deprecation;
- SQLite datetime adapter deprecations in migration tests.

## Result

**ACCEPTED.**

Proceed to Phase 6B1 only under a new exact Scope Lock.
