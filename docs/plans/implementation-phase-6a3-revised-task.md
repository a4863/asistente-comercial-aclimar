# Phase 6A3 Revised Implementation Task — Cutover Marker and Startup Recovery

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Supersedes:** docs/plans/implementation-phase-6a3-task.md
**Depends on:** Phase 6A1 and 6A2 ACCEPTED
**Decisions:** D10, D12, D13, D14

## Objective

Implement a persistent lock-aware cutover boundary using the existing `ConfigurationReference` model, then enable startup recovery of inherited `AnalysisRun(status='reserved')` rows only after that boundary has been safely established.

No migration or model change.

## Exact Scope Lock

Modify only:

1. app/persistence/repositories.py
2. app/main.py
3. test/test_persistence_repositories.py
4. test/test_startup.py

No other tracked file may change.

## Required behavior

### Cutover marker

Use the existing `ConfigurationReference` table/model.

Define one fixed bounded marker identity, for example:
- scope: `phase6_lock_cutover`
- reference_kind: a fixed bounded value indicating operational ownership cutover
- reference_value: a fixed version such as `v1`

Exact strings may differ only if existing repository conventions require it; keep them fixed, bounded and non-sensitive.

The marker must:
- be unique by its existing model constraint;
- be created only while the operational lock is held;
- be idempotent;
- never contain secrets, hostnames, PIDs, provider data or commercial content.

### First lock-aware startup

Ordering must be:

1. acquire operational single-instance lock;
2. begin controlled startup recovery transaction;
3. check marker existence;
4. if marker is absent:
   - count/check `AnalysisRun(status='reserved')`;
   - if one or more exist: fail startup closed, create no marker, modify no run;
   - if zero exist: create the cutover marker atomically;
5. commit;
6. only then allow readiness.

No automatic recovery of reserved runs is allowed in this same marker-creation transaction on the first cutover startup.

### Later lock-aware startup

If the marker already exists and the operational lock is held:

- atomically transition all currently `reserved` analysis runs to:
  - `status='failed_retryable'`
  - `failure_code='interrupted'`
- only rows currently in `reserved` are eligible;
- completed/stale_retryable/failed_retryable are untouched;
- operation is idempotent;
- startup readiness becomes true only after successful commit.

### Failure behavior

Fail closed if:
- lock is not owned;
- marker query/write fails;
- marker exists but is malformed/inconsistent with the expected fixed identity/value;
- reserved detection fails;
- recovery update fails;
- commit fails.

On any startup failure:
- readiness remains false;
- operational lock is released during shutdown/unwind;
- no provider/analysis route becomes available.

### Repository API

Add the smallest repository methods needed for:
- checking/creating the fixed cutover marker;
- detecting whether reserved runs exist;
- recovering reserved runs after marker is established.

Prefer bounded return values such as status/count rather than leaking row bodies or unrelated data.

Caller owns transaction/commit semantics consistently with existing repository patterns unless the existing repository architecture clearly requires otherwise.

## Tests

Repository tests must prove:

1. marker absent + zero reserved -> marker created;
2. repeated marker creation is idempotent;
3. marker absent + any reserved -> bounded failure / no marker / no run mutation;
4. marker present + reserved -> reserved becomes failed_retryable/interrupted;
5. marker present + no reserved -> no-op;
6. completed/stale_retryable/failed_retryable untouched;
7. repeated recovery idempotent;
8. malformed/conflicting marker fails closed;
9. no age/PID/heartbeat logic exists;
10. transaction rollback leaves both marker and runs unchanged when failure is injected.

Startup tests must prove:

11. lock acquired before marker/recovery work;
12. lock acquisition failure causes zero marker/recovery mutation;
13. first clean lock-aware startup creates marker and reaches readiness;
14. later startup recovers reserved rows and reaches readiness;
15. marker absent + reserved aborts startup and releases lock;
16. recovery failure aborts startup and releases lock;
17. readiness false until commit succeeds;
18. shutdown resets readiness before lock release;
19. inert import/default create_app performs zero recovery;
20. no provider/keyring/network access.

Use isolated synthetic SQLite only.

## Restrictions

Do not modify:
- app/persistence/models.py
- migrations
- app/security/single_instance.py
- OpenAI adapter
- config
- routes/templates
- credentials
- pyproject
- docs other than this already-created task

Do not:
- call OpenAI;
- access production SQLite;
- introduce commercial activation;
- add scheduler/background jobs;
- use temporal/PID heuristics.

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
- safe use of `ConfigurationReference` requires a model/migration change;
- marker semantics conflict with an existing use/constraint;
- another production/test file is required;
- transaction ownership cannot remain consistent with existing repository patterns;
- startup cannot guarantee lock-before-cutover/recovery ordering.

## Completion

Commit:

Implement phase 6A3 cutover marker and startup recovery

Push only origin/codex-work.
