# Phase 4 Final Plan Revision Task — Resolve Blocked Plan

**Status:** Approved for planning only
**Date:** 2026-09-23

## Inputs

Read:
- docs/plans/implementation-phase-4-analysis.md
- docs/plans/implementation-phase-4-decisions.md
- docs/plans/implementation-phase-4-final-decisions.md
- docs/plans/implementation-phase-4-plan.md
- AGENTS.md
- relevant approved architecture/data-model/security/testing documents
- current Phase 3D3 implementation and relevant persistence/domain code

## Objective

Revise the blocked Phase 4 plan into one deterministic implementation-ready plan.

Use all approved D1-D9 and P4-1-P4-6 decisions exactly.

Do not reopen resolved alternatives unless there is a genuinely new contradiction with the existing code/model.

## Required output

Update only:

docs/plans/implementation-phase-4-plan.md

The final plan must end with one of:
- READY FOR APPROVAL
- STOPPED FOR DECISION, only if a genuinely new unresolved business/data contradiction remains.

Do not create implementation code or implementation task files.

## Required exactness

The revised plan must define:

1. Final Phase 4 architecture/data flow.
2. Exact AnalysisRun lifecycle/status values and replay/version semantics.
3. Exact schema changes, including:
   - analysis run identity/version/replay;
   - dedicated <=4000-character derived summary artifact;
   - source-local evidence span anchored to original body;
   - derivation/run association and supersession;
   - commitment responsibility/date certainty;
   - current-vs-superseded analytical provenance for operational objects.
4. Exact bounded enums:
   - response_needed yes|no|uncertain;
   - commercial_risk none|low|medium|high|unknown;
   - priority low|normal|high|urgent.
5. Exact canonical input-selection/digest contract:
   - target first;
   - up to 6 prior;
   - <=30000 body chars;
   - first 30000 target chars if target alone exceeds limit;
   - metadata/separators excluded from body budget but included in canonical digest;
   - no ingestion-time substitution for missing source date.
6. Exact same-input replay vs force_reanalysis behavior.
7. Exact evidence validation and conservative quoted-history behavior.
8. Exact provider-neutral AIService DTOs and deterministic fake.
9. Exact transaction/failure/stale-before-commit flow.
10. Exact repository/service contracts.
11. Migration revision, downgrade behavior, checks/FKs/indexes/backfill.
12. Exact small subphase decomposition.

## Subphase-size requirement

Keep implementation tasks small.

Prefer 2-4 tracked files per subphase where practical.

Do not recreate one monolithic Phase 4 implementation task.

Each subphase must have:
- purpose;
- exact Scope Lock;
- dependencies;
- focused tests;
- full-suite timing;
- acceptance condition.

## Expected decomposition

You may refine names, but preserve separation of concerns approximately as:

- 4A: data model + migration foundation
- 4B: model constraints/evidence details
- 4C: pure selection/canonical digest/DTO contract
- 4D: repository replay/supersession primitives
- 4E: orchestration + fake AIService
- 4F: final integration/security acceptance

If a stage exceeds a manageable Scope Lock, split it further rather than expanding scope.

## Restrictions

- no concrete AI provider/model;
- no live CRM API;
- no external writes;
- no scheduler/UI;
- no attachment bodies;
- no quote/signature minimizer;
- no new dependencies unless already approved;
- no tests/migrations execution;
- no production file changes.

Do not inspect caches or untracked files.

Use:
- git status --short --untracked-files=no
- git diff --name-only

## Commit

Commit:
Finalize phase 4 implementation plan

Push only origin/codex-work.
