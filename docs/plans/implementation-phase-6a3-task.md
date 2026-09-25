# Phase 6A3 Implementation Task — Startup Recovery of Reserved Analysis Runs

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6A1 and 6A2 ACCEPTED
**Plan:** docs/plans/implementation-phase-6-plan.md
**Decisions:** D10, D12, D13 in docs/plans/phase-6-activation-decisions.md

## Objective

Implement controlled startup recovery for inherited `AnalysisRun(status='reserved')` rows after the operational single-instance lock has been successfully acquired.

This task is recovery only.

It must not compose OpenAI, create a commercial activation gate, expose a manual analysis trigger, add a scheduler, or change the data model.

## Exact Scope Lock

Modify only:

1. app/persistence/repositories.py
2. app/main.py
3. test/test_persistence_repositories.py
4. test/test_startup.py

No other tracked file may change.

## Required behavior

### Recovery ordering

During operational lifespan startup:

1. acquire the single-instance operational lock;
2. only after ownership is proven, perform reserved-run recovery;
3. only after recovery succeeds may the app become operationally ready;
4. if recovery fails, startup fails closed and the lock is released.

No recovery may occur:
- on module import;
- on inert `create_app()`;
- before lock acquisition;
- from a second worker that fails to acquire the lock.

### Repository operation

Add the smallest repository API needed to atomically and idempotently transition eligible inherited runs:

- from `status='reserved'`
- to `status='failed_retryable'`
- with bounded failure code `interrupted`

Use the existing schema and existing allowed lifecycle values.

Requirements:
- conditional update only from `reserved`;
- repeated recovery is idempotent;
- completed/stale_retryable/failed_retryable rows are untouched;
- no age-based heuristic;
- no PID/owner/heartbeat field;
- no migration/model change;
- no provider call;
- no content/body mutation beyond lifecycle fields necessary for the existing transition;
- preserve existing repository concurrency/CAS semantics where applicable.

### Cutover invariant

This implementation is only valid for lock-aware operational runs after the approved first-deployment quiescence rule.

Do not invent automatic handling for legacy pre-lock reservations.

If the repository cannot distinguish or safely constrain legacy pre-lock rows with the current schema, implement only the lock-aware recovery primitive and keep actual legacy cutover as an operator prerequisite; do not silently sweep known legacy rows in tests or production assumptions.

### Startup readiness

Expose the smallest internal readiness state needed by later phases, if necessary, such that:

- app is not operationally ready until lock + recovery complete;
- failed recovery leaves readiness false;
- shutdown resets readiness false before lock release.

Do not add routes/templates in this task.

## Tests

Add/update tests proving at minimum:

1. repository recovery changes reserved -> failed_retryable/interrupted;
2. completed/stale_retryable/failed_retryable rows remain unchanged;
3. repeated recovery is idempotent;
4. recovery is atomic for the intended operation;
5. recovery runs only after lock acquisition;
6. recovery does not run if lock acquisition fails;
7. recovery failure aborts startup and releases lock;
8. successful startup marks internal readiness true only after recovery;
9. shutdown resets readiness before/with lock release;
10. restart does not duplicate transitions;
11. inert import/create_app causes zero recovery;
12. no provider/keyring/network access;
13. no model/migration/schema change is required.

Use isolated synthetic SQLite fixtures only.

## Restrictions

Do not modify:
- persistence models
- migrations
- app/security/single_instance.py
- OpenAI adapter
- config
- routes/templates
- credentials
- pyproject
- docs

Do not:
- call OpenAI;
- access production SQLite;
- perform commercial activation;
- add scheduler/background jobs;
- expose manual trigger.

## Validation

Run:

python -m pytest test/test_persistence_repositories.py test/test_startup.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/persistence/repositories.py
- app/main.py
- test/test_persistence_repositories.py
- test/test_startup.py

## STOP conditions

STOP if:
- repository recovery requires a model/migration change;
- another production/test file is required;
- safe recovery needs an age/PID/heartbeat heuristic;
- startup cannot guarantee lock-before-recovery ordering;
- any provider/commercial path must be introduced.

## Completion

Commit:

Implement phase 6A3 startup reserved-run recovery

Push only origin/codex-work.
