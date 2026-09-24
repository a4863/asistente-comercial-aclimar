# Phase 4C Implementation Task — AnalysisRun Repository Primitives

**Status:** Approved for Implement
**Date:** 2026-09-24
**Prerequisites:** Phase 4A1 ACCEPTED; Phase 4A2 ACCEPTED; Phase 4B ACCEPTED
**Approved plan:** docs/plans/implementation-phase-4-plan.md

## Objective

Implement only repository primitives for Phase 4 analysis run reservation, replay, retryable states, versioning, and supersession.

No AIService.
No orchestration service.
No derivation persistence.
No operational object creation.
No CRM/IMAP/Calendar interaction.

## Exact Scope Lock

Modify only:
1. app/persistence/repositories.py
2. test/test_persistence_repositories.py

No other tracked path may change.

## Repository contract

Add AnalysisRepository(session) using caller-owned transaction/commit/rollback.

### reserve_run(...)
Equivalent contract:
reserve_run(account_scope, target_source_record_id, conversation_id, input_digest, contract_version, policy_version, request_mode)

Return a bounded result distinguishing:
- reserved_new
- completed_replay
- in_progress

Rules:
- validate account_scope/target/conversation coherence against current persisted state;
- request_mode automatic|manual|force only;
- input_digest lowercase SHA-256;
- contract/policy versions >0;
- automatic/manual same-input replay may reuse only a completed run that is still the latest completed analytical result for that target;
- force always creates a new run version even if digest identical;
- run_version increments monotonically per account_scope + target_source_record_id;
- a matching currently-reserved run returns in_progress, never a second reservation;
- stale/failed runs remain append-only history and do not get mutated back to reserved;
- a new attempt after stale/failed gets a new run_version;
- no AI call here.

### mark_retryable(...)
Compare-and-set from expected status reserved to:
- stale_retryable with input_changed;
- failed_retryable with provider_failure|invalid_output|persistence_failure|interrupted.

Reject invalid status/code combinations.
Do not mutate completed runs.
Do not store raw exception text.

### completion/supersession primitive
Implement only the run-status/supersession portion needed later by 4D, without creating derivations yet.

Provide a primitive equivalent to finalize_run_status(run_id, expected_status='reserved') that can:
- link supersedes_run_id to the latest previous completed run for same target;
- set completed_at;
- transition status to completed;
- enforce append-only predecessor chain;
- never supersede a run for another target/account;
- never create self/cycles;
- never delete prior runs.

If the final plan requires completion to happen together with derivations, expose the lower-level validated helper but do not claim full complete_run semantics yet.

### Read helpers
Implement bounded reads for:
- latest completed run for target;
- replay lookup by target+digest+contract+policy;
- run history ordered by run_version;
- current analytical provenance classification at run level where possible.

Do not join/create operational or derivation rows in this phase.

## Transaction/concurrency rules

- repository owns no commit/rollback;
- callers supply transaction;
- use flush only when necessary;
- uniqueness conflicts must become bounded repository/domain errors, not raw SQLAlchemy text;
- concurrent duplicate reservation must fail closed and be retryable by caller; do not invent a scheduler;
- no long transaction around external work because external work is out of scope.

## Tests

Add focused tests covering at least:
1. first reservation creates run_version 1;
2. second changed input creates next version;
3. normal manual same-input replay reuses latest completed run;
4. automatic same-input replay reuses latest completed run;
5. force same-input creates new version;
6. force repeated twice creates distinct versions;
7. currently reserved matching request returns in_progress;
8. stale_retryable is append-only and next attempt creates new version;
9. failed_retryable is append-only and next attempt creates new version;
10. invalid request_mode rejected;
11. invalid digest rejected;
12. invalid versions rejected;
13. cross-account target/conversation rejected;
14. superseded/unresolved conversation rejected where repository contract requires current conversation;
15. mark stale only from reserved;
16. mark failed only from reserved;
17. completed cannot become retryable;
18. bounded failure codes only;
19. finalize links latest previous completed run;
20. force completion supersedes previous completed run;
21. supersession never crosses target/account;
22. unique predecessor chain preserved;
23. no self supersession;
24. history ordered by run_version;
25. repository performs no commit/rollback;
26. rollback by caller removes uncommitted reservation;
27. uniqueness/IntegrityError converted to bounded repository error;
28. no derivation/summary/operational rows created.

Use isolated SQLite fixtures only.

## Restrictions
- no app/domain changes;
- no models/migration changes;
- no service/AIService;
- no provider/network;
- no CRM/IMAP/Calendar;
- no new dependencies;
- no cache/untracked inspection.

## Validation
Run:
python -m pytest test/test_persistence_repositories.py
Then:
python -m pytest

Tracked diff must contain exactly:
- app/persistence/repositories.py
- test/test_persistence_repositories.py

## Completion
Commit:
Implement phase 4C analysis run repository

Push only origin/codex-work.

If derivation persistence or service changes are required, STOP.