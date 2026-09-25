# Phase 6A2 Acceptance — Worker Lifecycle and Single-Instance Composition

**Status:** ACCEPTED
**Date:** 2026-09-25

## Scope

Accepted implementation:
- `app/main.py`
- `test/test_startup.py`

Implementation commit:
- `f6826075b4ec5f17f4b2b66297453acfacd0fc7e`

## Accepted behavior

- module import remains inert;
- default `create_app()` remains inert and does not acquire the operational lock;
- controlled `run()` composes the operational lifespan;
- serving worker acquires exactly one `SingleInstanceLock` during lifespan startup;
- lock is held strongly in application state for the full operational lifespan;
- second worker for the same SQLite identity fails startup closed;
- shutdown releases ownership;
- restart can reacquire ownership;
- controlled launcher remains loopback-only;
- operational launcher explicitly fixes `reload=False`, `workers=1`, `lifespan="on"`;
- direct module app remains non-operational;
- startup performs no provider, keyring or network access;
- no recovery, provider composition, route trigger or commercial activation was introduced.

## Validation

User validation on Windows:

`python -m pytest test/test_startup.py test/test_single_instance.py`
- 22 passed
- 2 skipped
- 1 warning

`python -m pytest`
- 550 passed
- 2 skipped
- 8 warnings

Warnings are known/non-blocking:
- Starlette TestClient/httpx deprecation;
- SQLite datetime adapter deprecations in migration tests.

## Result

**ACCEPTED.**

Proceed to Phase 6A3 only under a new exact Scope Lock.
