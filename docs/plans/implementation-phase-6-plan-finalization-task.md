# Phase 6 Plan Finalization Task

**Status:** APPROVED FOR PLANNING ONLY
**Date:** 2026-09-24
**Current plan:** docs/plans/implementation-phase-6-plan.md
**Decisions:** docs/plans/phase-6-activation-decisions.md

## Objective

Update the existing Phase 6 implementation plan to incorporate approved D8–D11 and convert it from BLOCKED to either:

- READY FOR APPROVAL with exact per-subphase Scope Locks; or
- STOP if the existing persistence data cannot support a safe orphaned-reserved-run recovery rule without a new approved model change.

Planning/documentation only.

## Required work

Modify only:

`docs/plans/implementation-phase-6-plan.md`

The updated plan must:

1. remove resolved alternatives for:
   - process-local authorization;
   - local web session/CSRF/origin protection;
   - startup recovery policy direction;
   - transient smoke status;
2. define exact file Scope Locks for the smallest feasible subphases;
3. keep each implementation subphase independently reviewable;
4. keep all default tests offline;
5. keep live synthetic smoke and commercial activation as separate later approvals;
6. define how the process-local gate is rechecked before first provider request and before retry;
7. define the minimal session/CSRF/origin mechanism using existing project facilities where possible;
8. inspect existing AnalysisRun fields/contracts and determine whether a safe orphan-detection rule is possible without schema change;
9. if safe orphan detection is not possible with existing data, STOP explicitly and identify the smallest additional data-model decision required;
10. keep smoke status transient and migration-free;
11. include the separately scoped architecture documentation correction;
12. provide focal + full-suite validation commands for each subphase.

## Preferred staging

Use the smallest viable split. A likely sequence is:

- 6A1 — runtime commercial gate + adapter retry recheck;
- 6A2 — composition foundation;
- 6B — local status + credential presence;
- 6C — interactive credential CLI;
- 6D — synthetic smoke CLI tooling, offline-tested only;
- 6E1 — local session/CSRF/origin protection + manual trigger;
- 6E2 — reserved-run startup recovery, if safely possible without schema change;
- 6E3 — rollback/security regression;
- 6F — separately approved one-shot live synthetic smoke;
- 6G — separately approved commercial activation;
- documentation-only architecture correction.

Adjust only if repository facts justify a smaller/safer split.

## Hard restrictions

Do not:
- modify production code;
- modify tests;
- modify config;
- modify docs/architecture.md;
- create scripts;
- add dependencies;
- create migrations;
- call OpenAI;
- inspect real credentials;
- activate AI;
- read production IMAP/CRM/Calendar data.

## STOP rule

STOP if safe orphaned `reserved` recovery cannot be proven from existing fields and process-local facts without a schema/data-model change.

Do not invent a timeout/ownership field that does not exist.

## Completion

Modify only:
`docs/plans/implementation-phase-6-plan.md`

Commit:
`Finalize phase 6 safe activation plan`

Push only to `origin/codex-work`.
