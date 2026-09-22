# Phase 3C Plan Task — IMAP Synchronization and Recovery

**Status:** Approved for Plan
**Date:** 2026-09-22
**Baseline:** current `codex-work`
**Analysis:** `docs/plans/implementation-phase-3c-analysis.md`
**Decisions:** `docs/plans/implementation-phase-3c-decisions.md`

## Objective

Prepare the implementation plan for Phase 3C using the approved decisions without reopening them.

Split into:
- 3C1 — persistence/repository boundary;
- 3C2 — initial and incremental synchronization;
- 3C3 — reconciliation and recovery.

## Fixed decisions

### D1-C
Conservative Message-ID correlation:
- strong evidence, not absolute uniqueness;
- reuse only one unambiguous candidate within account scope;
- ambiguity/conflict => no auto-merge;
- absent Message-ID => independent occurrence;
- no weak-field-only merge.

### D2-A
A location may become unavailable only after full reconciliation across all currently allowlisted synchronized folders for the account.
Reactivation appends SourceObservation and preserves history.

### D3-A
One transaction per message.
Checkpoint advances only with durable successful message commit.
Checkpoint = highest successfully committed UID, holes allowed.

### D4
UIDVALIDITY reset:
- new namespace;
- reconcile exactly initial_window_days per folder;
- correlation follows D1-C;
- unavailability still requires D2-A.

## Questions the plan must settle

1. exact SourceRecord stable_external_id strategy for:
   - unambiguous Message-ID;
   - duplicate Message-ID;
   - missing Message-ID;
2. exact conservative correlation evidence/conflict rule;
3. exact IdempotencyIdentity operation_kind/scope/key;
4. exact SourceObservation marker/version scheme;
5. exact SynchronizationCheckpoint scope and deterministic marker encoding;
6. repository methods needed;
7. whether current schema suffices;
8. if schema does not suffice, STOPPED FOR DECISION before proposing migration;
9. exact transaction boundary implementation;
10. initial sync algorithm;
11. incremental sync algorithm;
12. UIDVALIDITY reset algorithm;
13. full-allowlist reconciliation algorithm;
14. move detection;
15. unavailable/reactivation transition algorithm;
16. attachment metadata replacement/upsert semantics;
17. update rules for existing EmailMessage metadata/body;
18. failure/audit/degraded-state behavior;
19. fake-only test matrix;
20. Scope Lock per 3C1/3C2/3C3.

## Restrictions

No implementation.
No real network/keyring.
No scheduler/UI/threading/AI/CRM/Calendar.
No mailbox mutations.
No schema change unless plan proves unavoidable; if unavoidable, STOPPED FOR DECISION.

## Output

Create only:

`docs/plans/implementation-phase-3c-plan.md`

Status:
- READY FOR APPROVAL
- or STOPPED FOR DECISION

## Completion protocol

Commit:
`Plan phase 3C IMAP synchronization and recovery`

Push only to `origin/codex-work`.
Do not touch `main`.
