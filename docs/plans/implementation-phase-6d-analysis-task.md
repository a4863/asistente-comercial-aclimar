# Phase 6D Analysis Task — Synthetic Live Smoke Authorization Boundary

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-25
**Depends on:** Phase 6C ACCEPTED
**Decisions:** D5, D8, D11 and accepted Phase 6B1 gate semantics

## Objective

Determine the smallest safe design that allows a dedicated explicit synthetic live smoke command to exercise the real OpenAI adapter without using or enabling the commercial authorization gate and without creating a reusable bypass for arbitrary `AnalysisInput`.

This task is **READ-ONLY analysis**.

Do not modify application code, tests, config, dependencies, migrations or credentials.

## Current invariants

- `OpenAIAnalysis.analyze(AnalysisInput)` requires:
  - AI technically enabled;
  - operational ownership;
  - commercial gate ON.
- Commercial gate defaults OFF and is reserved for real commercial-data authorization.
- D5 requires a dedicated explicit synthetic live smoke command with fixed synthetic non-commercial content only.
- D8 states synthetic smoke is a separate synthetic-only capability, not a general bypass.
- D11 states smoke result is process-local/transient only.
- No live provider call is authorized during this analysis.

## Questions to resolve

Analyze the current code and propose one exact design answering:

1. Where should the synthetic-only capability live?
2. How can the adapter verify that the input is the fixed approved synthetic payload rather than caller-supplied arbitrary content?
3. Should the adapter expose a separate method such as `smoke()`, a dedicated adapter wrapper, or a sealed capability/token?
4. How do we prevent a caller from constructing the same capability and sending commercial `AnalysisInput`?
5. What operational ownership requirement should synthetic smoke retain?
6. Should technical `AISettings.enabled` be required for smoke?
7. How should credential lookup, endpoint validation, schema validation, timeout and retry behavior be reused without duplicating provider code?
8. What files must change for the implementation?
9. Can the implementation remain migration-free and dependency-free?
10. How should tests prove there is no arbitrary-input bypass?
11. How should smoke state remain process-local and non-persistent?
12. What exact CLI command/API should be implemented in 6D?
13. Confirm that no commercial gate state changes during smoke.
14. Confirm that no IMAP/CRM/Calendar/SQLite commercial source data can enter the smoke path.

## Preferred properties

Prefer:
- a dedicated narrow API for fixed synthetic input;
- no boolean/test flag on `analyze()`;
- no caller-supplied arbitrary synthetic text;
- no environment-variable bypass;
- no route/UI trigger;
- reuse of existing strict schema/decoder/provider mechanics where safe;
- explicit operational ownership;
- exact offline tests plus an optional separately approved real live smoke later.

## STOP conditions

STOP and present alternatives if:
- the synthetic path cannot be made structurally incapable of carrying arbitrary commercial input;
- safe reuse requires broad changes to the analysis domain contract;
- provider code would need duplication substantial enough to create divergent security behavior;
- another design decision is required.

## Deliverable

Create only:

`docs/plans/phase-6d-smoke-analysis.md`

Include:
- current-state findings;
- candidate designs considered;
- rejected designs and why;
- recommended design;
- exact proposed production/test file Scope Lock;
- security invariants;
- test matrix;
- STOP/ambiguity findings;
- readiness verdict: READY FOR PLAN or STOP.

Commit:

Analyze phase 6D synthetic smoke boundary

Push only origin/codex-work.
