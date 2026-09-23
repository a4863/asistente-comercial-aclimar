# Phase 3D3D Implementation Task — Transaction Wrapper, Lock Retry, and Final 3D3 Closure

**Status:** Approved for Implement
**Date:** 2026-09-23
**Parent plan:** docs/plans/implementation-phase-3d3-plan.md
**Accepted prerequisites:** Phase 3D3A, Phase 3D3B, Phase 3D3C

## Objective
Implement only the final Engine-level transaction wrapper around the accepted 3D3C reconstruction core.

This task closes Phase 3D3 by adding:
- account-wide SQLite write reservation before corpus read;
- three-attempt busy/locked acquisition handling;
- one caller-owned Session bound to the reserved connection;
- atomic commit/rollback;
- final public result contract;
- concurrency/retry tests.

Do NOT alter 3D2 topology rules, snapshot semantics, lineage rules, persistence primitives, migrations, docs, scheduler, UI, IMAP, CRM, Calendar, AI, or external integrations.

## Exact Scope Lock
Modify only:
- app/services/email_thread_reconstruction.py
- test/test_email_thread_reconstruction.py

No other tracked path may change.

## Public wrapper contract

Add:

ThreadReconstructionResult(
    account_scope: str,
    status: Literal['completed', 'busy_retry_later'],
    reconstruction_key: str | None,
    source_count: int | None,
    component_count: int | None,
    conversations_created: int,
    memberships_changed: int,
    lineage_operations_created: int,
)

and:

reconstruct_account_threads(engine: sqlalchemy.Engine,
                            account_scope: str) -> ThreadReconstructionResult

The existing reconstruct_account_threads_in_session() remains the deterministic core.

## Scope validation
Validate account_scope before opening any connection:
- string
- nonblank after strip
- length 1..100
Invalid -> ThreadReconstructionError('invalid_scope').

## Connection/transaction protocol

For each acquisition attempt:

1. open a fresh Engine connection;
2. ensure SQLite dialect; otherwise raise bounded persistence_conflict;
3. set and verify PRAGMA foreign_keys=ON;
4. set PRAGMA busy_timeout=0;
5. ensure no preliminary SQLAlchemy transaction remains before reservation;
6. issue explicit BEGIN IMMEDIATE;
7. only after BEGIN IMMEDIATE succeeds, create/bind one SQLAlchemy Session to that same connection;
8. call reconstruct_account_threads_in_session(session, account_scope);
9. flush as needed;
10. commit exactly once through the connection/transaction owner;
11. close Session and connection.

No corpus read may occur before successful BEGIN IMMEDIATE.

No repository/service core may commit independently.

## Busy retry

Only SQLite busy/locked failure while acquiring BEGIN IMMEDIATE is retriable.

Behavior:
- maximum 3 attempts total;
- fresh connection each attempt;
- 100 ms wait between attempt 1→2 and 2→3;
- do not sleep after attempt 3;
- after third acquisition failure return:
  status='busy_retry_later'
  reconstruction_key=None
  source_count=None
  component_count=None
  all write counts=0

No exception should leak raw SQLite message text to user-visible result.

Busy/locked after acquisition is NOT automatically retried:
- rollback entire transaction;
- raise ThreadReconstructionError('persistence_conflict').

## Success

On success convert CoreResult to ThreadReconstructionResult:
- status='completed'
- all key/count values populated.

Exact replay must remain zero topology-change counts.

## Failure semantics

For ThreadReconstructionError raised by the core:
- rollback entire reserved transaction;
- re-raise same bounded code.

For unexpected SQLAlchemy/SQLite/persistence errors after reservation:
- rollback;
- raise ThreadReconstructionError('persistence_conflict').

Never partially commit evidence, decisions, conversations, memberships, lineage, or supersession.

## Transaction ownership rules

Wrapper may:
- open/close connection;
- create/close Session;
- BEGIN IMMEDIATE;
- commit/rollback outer transaction.

Core must remain transaction-agnostic:
- no Engine;
- no begin/commit/rollback/close;
- no retry/sleep.

## Required tests

Add focused synthetic tests for:

1. successful wrapper on empty corpus;
2. successful initial reconstruction;
3. exact replay through wrapper;
4. BEGIN IMMEDIATE occurs before snapshot read;
5. same reserved connection is used by Session/core;
6. successful wrapper commits exactly once;
7. core error causes full rollback;
8. injected failure after evidence persistence rolls back everything;
9. injected failure after decision persistence rolls back everything;
10. injected failure after Conversation creation rolls back everything;
11. injected failure after lineage creation rolls back everything;
12. injected failure after membership change rolls back everything;
13. first lock acquisition busy, second succeeds;
14. first two busy, third succeeds;
15. three busy attempts -> busy_retry_later;
16. exactly 3 attempts maximum;
17. exactly two 100ms waits on three-busy path;
18. no wait after third attempt;
19. fresh connection per acquisition attempt;
20. busy/locked after successful acquisition does not retry;
21. concurrent writer blocks acquisition and yields retry behavior deterministically;
22. no corpus read before reservation success;
23. non-SQLite Engine -> persistence_conflict;
24. invalid_scope opens no connection;
25. no AuditEvent rows created;
26. full exact replay still creates no duplicate Conversation/ThreadEvidence/ThreadEvidenceDecision/ThreadMembershipChange/ThreadLineageOperation/ThreadLineageEdge.

Use isolated SQLite databases only.
Concurrency tests must be deterministic and bounded; no hanging tests.

## Timing implementation

Use an injectable/internal sleep helper if needed for deterministic tests, but do not add a dependency.

Do not expose timing implementation as public API.

## Restrictions
- no new dependency;
- no model/repository/migration/doc changes;
- no scheduler;
- no UI;
- no network;
- no IMAP/CRM/Calendar/AI;
- no production database execution;
- no generic AuditEvent;
- no changes outside the two Scope Lock files.

## Validation

Run:
python -m pytest test/test_email_thread_reconstruction.py

Then:
python -m pytest

Confirm tracked diff contains only:
- app/services/email_thread_reconstruction.py
- test/test_email_thread_reconstruction.py

## Completion

Commit:
Implement phase 3D3D transaction wrapper

Push only origin/codex-work.

If another tracked file is required, STOP.
