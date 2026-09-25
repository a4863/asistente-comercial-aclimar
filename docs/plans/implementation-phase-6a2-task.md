# Phase 6A2 Implementation Task — Worker Lifecycle and Single-Instance Composition

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6A1 ACCEPTED
**Plan:** docs/plans/implementation-phase-6-plan.md

## Objective

Integrate the accepted single-instance lock into the controlled application lifecycle so that the real serving worker acquires and holds operational ownership for its lifetime.

This task is lifecycle/composition only.

It must not yet perform reserved-run recovery, compose OpenAIAnalysis, expose a manual analysis trigger, or activate commercial processing.

## Exact Scope Lock

Modify only:

1. app/main.py
2. test/test_startup.py

No other tracked file may change.

## Required behavior

### Inert import/create_app

Preserve:
- module import has no lock acquisition;
- `create_app()` does not acquire the lock merely by being called;
- no provider/network/keyring/database recovery call on import or app construction.

### Worker lifespan ownership

Add a FastAPI lifespan/lifecycle integration such that:

- the actual serving worker acquires `SingleInstanceLock(settings.database_url)` during startup;
- acquisition occurs before operational readiness;
- the lock object is strongly retained in application state/runtime state while the worker is alive;
- startup fails closed if lock acquisition fails;
- shutdown closes the lock only after the application is no longer accepting operational work;
- repeated/partial shutdown remains safe.

No recovery transaction yet.

### Controlled launcher policy

The supported `run()` path must remain one worker and non-reload.

Operational mode must fail closed for unsupported serving semantics:
- reload;
- multiple workers;
- lifespan disabled.

Do not add a new third-party dependency.

If direct `uvicorn app.main:app` cannot be fully constrained in this task, ensure it still cannot gain operational ownership incorrectly and document/test the fail-closed behavior available within this Scope Lock.

### Development reload

Development reload may remain possible only without operational AI capability.

This task does not need to create a user-facing mode switch. It must ensure that merely running development reload does not create an analysis-capable owner path.

### Ownership exposure

Application state may expose only the minimum runtime ownership object/predicate needed by later phases.

Do not expose raw Win32 handles in routes or logs.

## Tests

Update/add startup tests proving at minimum:

1. importing `app.main` acquires no lock;
2. `create_app()` acquires no lock;
3. entering app lifespan acquires exactly one lock;
4. second app/worker for same DB fails startup while first owns the lock;
5. shutdown releases ownership;
6. restart can reacquire;
7. failed acquisition leaves app non-operational;
8. no provider/network/keyring call occurs;
9. controlled launcher remains loopback-only;
10. no reload/multi-worker operational configuration is silently enabled;
11. lock object remains held for full lifespan;
12. existing startup tests remain green.

Use synthetic temporary DB paths only.

## Restrictions

Do not modify:
- app/security/single_instance.py
- persistence/models/repositories
- migrations
- OpenAI adapter
- config schema
- routes/templates
- credentials
- pyproject
- docs

Do not:
- perform reserved-run recovery;
- call OpenAI;
- read real keyring;
- touch production SQLite;
- expose manual analysis POST;
- add scheduler/background work.

## Validation

Run:

python -m pytest test/test_startup.py test/test_single_instance.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/main.py
- test/test_startup.py

## STOP conditions

STOP if:
- another production/test file is required;
- safe lifespan ownership requires modifying the lock primitive;
- unsupported Uvicorn mode enforcement requires a new dependency or config model change;
- startup recovery is needed to make this task work;
- any provider or commercial activation path would be introduced.

## Completion

Commit:

Implement phase 6A2 worker lifecycle ownership

Push only origin/codex-work.
