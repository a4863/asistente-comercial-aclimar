# Phase 4E Implementation Task — AIService Boundary and Analysis Orchestrator

**Status:** Approved for Implement
**Date:** 2026-09-24
**Prerequisites:** Phase 4A1/4A2/4B/4C/4D ACCEPTED
**Approved plan:** docs/plans/implementation-phase-4-plan.md

## Objective

Implement the Phase 4 service boundary and orchestration for email/thread analysis using only a deterministic fake AIService.

This phase wires:
- canonical input selection;
- AnalysisRun reservation/replay;
- provider-neutral AIService protocol;
- deterministic FakeAIService;
- provider call outside long write transaction;
- stale-input revalidation;
- completion persistence through AnalysisRepository;
- bounded retryable failure states.

No real remote AI provider.
No CRM calls.
No external mutations.

## Exact Scope Lock

Modify only:
1. app/services/email_analysis.py
2. test/test_email_analysis_service.py

No other tracked path may change.

## AIService protocol

Define a synchronous provider-neutral protocol equivalent to:

AIService.analyze(analysis_input: AnalysisInput) -> AnalysisCandidates

Rules:
- receives only approved AnalysisInput projection;
- no Session/ORM/repository/credential/adapter handles;
- cannot execute email/CRM/calendar actions;
- cannot approve proposals;
- returns immutable AnalysisCandidates;
- provider exceptions must not leak raw text through service result/state.

## FakeAIService

Implement a deterministic fake for tests only.

Required characteristics:
- same AnalysisInput => same AnalysisCandidates;
- no network/filesystem/environment access;
- configurable canned output and configurable bounded failure mode;
- records only safe call metadata for assertions, never credentials/raw unrelated state;
- may be configured to raise a fake provider failure.

## Orchestrator

Implement service function/class equivalent to:

analyze_email_in_thread(session_factory_or_session_boundary, ai_service, account_scope, target_source_record_id, *, request_mode='automatic', contract_version=1, policy_version=1)

Return a bounded result with outcomes at least:
- completed
- completed_replay
- in_progress
- stale_retryable
- failed_retryable

## Required orchestration sequence

1. Open short DB unit-of-work.
2. select_analysis_input(...).
3. capture exact AnalysisSourceSnapshot for selected sources.
4. resolve current conversation_id from canonical target.
5. AnalysisRepository.reserve_run(...).
6. If completed_replay: return without provider call.
7. If in_progress: return without provider call.
8. Commit only the reservation unit-of-work if a new run was created.
9. Close/leave write transaction before AI call.
10. Call ai_service.analyze(analysis_input).
11. On provider failure: open new short UoW and mark run failed_retryable/provider_failure; commit; return bounded failed_retryable.
12. Validate returned object is AnalysisCandidates; malformed output maps to failed_retryable/invalid_output.
13. Open new short DB UoW.
14. Re-select canonical input with same contract/policy limits.
15. If digest/current selection changed: mark run stale_retryable/input_changed; commit; persist zero derivations; return stale_retryable.
16. Otherwise call AnalysisRepository.complete_run(...) using original snapshot/candidates.
17. Commit completion atomically.
18. Return completed.

Provider call must never execute inside a transaction holding DB writes/locks.

## Transaction boundary

The service may own commit/rollback at UoW level.
Repositories continue not to own commit/rollback.

If SessionFactory is required to guarantee provider-outside-transaction semantics, use it locally in service tests. Do not change persistence infrastructure.

## Snapshot rules

Capture snapshot from exact selected sources before provider call:
- source IDs exactly equal AnalysisInput selected_messages;
- target body must be string;
- prior body may be str|None;
- no attachments;
- no folder/UID;
- no credentials/logs/audit;
- no unrelated messages.

Do not send AnalysisSourceSnapshot to AIService; AIService receives AnalysisInput only.

## Stale revalidation

Before complete_run:
- reconstruct/select current AnalysisInput with same account/target/contract/policy and approved limits;
- exact equality or digest equality must prove the disclosed input is still current;
- changes to body outside excerpt must be caught through full-body digest;
- membership/order/metadata changes that affect digest must mark stale_retryable;
- conversation repartition/supersession must mark stale_retryable/input_changed;
- do not call complete_run on stale input.

## Failure mapping

Provider exception -> failed_retryable/provider_failure.
Returned wrong type or domain-invalid aggregate -> failed_retryable/invalid_output.
Repository persistence failure -> failed_retryable/persistence_failure where safely markable in a fresh transaction.
Interrupted recovery is out of scope here; no scheduler.

Never store raw exception text.

## Replay/force behavior

- automatic/manual exact replay of latest completed run => completed_replay; provider not called.
- force => new run and provider called even if digest identical.
- matching reserved run => in_progress; provider not called.

## Security boundary

Tests must prove the AIService input contains only the approved AnalysisInput fields.
No ORM rows, Session, repository, credentials, IMAP location, attachment metadata, audit events, CRM rows, or source bodies beyond disclosed excerpts.

Embedded email instructions are data only. FakeAIService cannot trigger actions.

## Tests

Add focused tests covering at least:
1. new automatic analysis completes end-to-end with fake;
2. provider called exactly once for new run;
3. completed replay makes zero provider calls;
4. manual replay makes zero provider calls;
5. force calls provider and creates next version;
6. in_progress makes zero provider calls;
7. provider call occurs with no active write transaction/lock;
8. provider failure -> failed_retryable/provider_failure;
9. raw provider exception text not persisted/returned;
10. malformed non-AnalysisCandidates -> failed_retryable/invalid_output;
11. candidate validation failure -> failed_retryable/invalid_output;
12. target body change during provider call -> stale_retryable/input_changed;
13. hidden body suffix change outside 30k excerpt -> stale_retryable;
14. subject/recipient/date metadata change affecting digest -> stale_retryable;
15. conversation membership/repartition change -> stale_retryable;
16. stale case creates zero derivations/operational rows;
17. successful case creates run + derivations via 4D;
18. snapshot preserves metadata-only prior None;
19. metadata-only prior change -> stale;
20. persistence failure -> bounded failed_retryable/persistence_failure when possible;
21. no commit by repository regression preserved;
22. AIService receives no forbidden fields/objects;
23. FakeAIService deterministic;
24. no external actions/Alert/ActionProposal/ApprovalDecision/ExecutionResult;
25. forced reanalysis append-only and supersedes previous completed run.

Use isolated SQLite fixtures only.
No network.

## Restrictions
- no domain changes;
- no persistence/model/migration changes;
- no real provider SDK;
- no CRM/IMAP/Calendar actions;
- no scheduler/UI;
- no new dependencies;
- no cache/untracked inspection.

## Validation
Run:
python -m pytest test/test_email_analysis_service.py
Then:
python -m pytest

Tracked diff must contain exactly:
- app/services/email_analysis.py
- test/test_email_analysis_service.py

## Completion
Commit:
Implement phase 4E analysis orchestration

Push only origin/codex-work.

If this requires changing domain/persistence contracts, STOP.