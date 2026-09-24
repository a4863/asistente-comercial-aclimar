# Phase 6 Final Plan Update Task

**Status:** APPROVED FOR PLANNING ONLY
**Date:** 2026-09-24
**Inputs:**
- docs/plans/implementation-phase-6-plan.md
- docs/plans/phase-6-activation-decisions.md
- docs/plans/phase-6-single-instance-analysis.md

## Objective

Update the Phase 6 implementation plan from BLOCKED to a final executable planning state using approved D12/D13.

Planning/documentation only.

## Required work

Modify only:

`docs/plans/implementation-phase-6-plan.md`

The updated plan must:

1. set status to `READY FOR APPROVAL` if no new blocker is found;
2. replace the blocked ownership section with the approved exclusive Windows file-handle design;
3. define exact per-subphase Scope Locks;
4. keep implementation increments small and independently reviewable;
5. explicitly separate:
   - lock primitive;
   - worker lifecycle/composition;
   - startup recovery;
   - runtime commercial gate;
   - status/credential presence;
   - credential CLI;
   - synthetic smoke tooling;
   - protected manual trigger;
   - final rollback/security regression;
6. state that operational AI mode forbids Uvicorn reload/multiple workers;
7. state that development reload is allowed only with operational AI disabled;
8. require canonical DB identity for lock naming and fail closed on unsupported/non-file/ambiguous DB identities;
9. preserve the pre-lock rollout/quiescence rule;
10. keep default tests fully offline;
11. keep live synthetic smoke and commercial-data activation as separate later approvals;
12. keep Global commercial-data processing blocked absent separate explicit approval;
13. include focal/full-suite validation commands for every implementation subphase;
14. keep the architecture documentation correction as a separate documentation-only task.

## Preferred implementation sequence

Use this sequence unless exact repository facts require a smaller split:

- 6A1 — Windows exclusive lock primitive
- 6A2 — worker lifecycle / single-instance operational composition
- 6A3 — startup reserved-run recovery
- 6B1 — process-local commercial authorization gate + adapter retry recheck
- 6B2 — local status + credential presence
- 6C — interactive credential CLI
- 6D — synthetic smoke CLI tooling, offline-tested only
- 6E1 — local session/CSRF/origin protection
- 6E2 — protected manual analysis trigger
- 6E3 — rollback/security regression
- 6F — optional separately approved one-shot live synthetic smoke
- 6G — optional separately approved commercial-data activation
- documentation-only architecture correction

Each future implementation task requires separate explicit approval.

## Hard restrictions

Do not:
- modify production code;
- modify tests;
- modify config;
- modify docs/architecture.md;
- add dependencies;
- create migrations;
- call OpenAI;
- inspect real credentials;
- touch production SQLite/IMAP/CRM/Calendar;
- activate AI.

## STOP conditions

STOP if exact Scope Locks still require an unresolved architectural choice or if any subphase needs a migration/new dependency not already approved.

## Completion

Modify only:
`docs/plans/implementation-phase-6-plan.md`

Commit:
`Finalize executable phase 6 activation plan`

Push only to `origin/codex-work`.
