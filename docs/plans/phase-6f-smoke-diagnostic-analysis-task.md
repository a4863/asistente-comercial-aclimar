# Phase 6F Smoke Diagnostic Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY
**Trigger:** first authorized live synthetic smoke returned only `smoke_failed`

## Objective

Determine the smallest safe diagnostic improvement that preserves secret/content isolation while making a future separately authorized smoke attempt report the adapter's existing bounded failure category.

Do not make another provider call.

## Current problem

`app/integrations/ai_smoke_cli.py` catches `OpenAIAnalysisError` and always prints `smoke_failed`.

`OpenAIAnalysisError.code` already contains bounded categories and intentionally excludes raw provider error text/body.

Therefore the prior live result cannot distinguish authentication, quota, timeout, provider response-shape, schema/decoder failure, or other bounded categories.

## Questions to resolve

1. Which existing `OpenAIAnalysisError.code` values are safe to expose from the dedicated synthetic smoke CLI?
2. Should the CLI print:
   - `smoke_failed:<code>`,
   - a separate bounded diagnostic line,
   - or map codes to a smaller allowlist?
3. Which codes must remain collapsed to avoid leaking internal/security state?
4. How do we guarantee an arbitrary/unknown code can never be echoed?
5. Should successful output remain exactly `passed`?
6. Should exit codes remain unchanged?
7. Should the diagnostic apply only to smoke CLI, not browser/commercial routes?
8. Can this be implemented only in:
   - `app/integrations/ai_smoke_cli.py`
   - `test/test_ai_smoke_cli.py`
9. What offline tests prove raw provider/body/key/credential/config details never appear?
10. Can existing adapter tests establish the safe code vocabulary without modifying the adapter?
11. Is any change to logging required? Prefer no.
12. Should another live attempt be prohibited until this bounded diagnostic is accepted?
13. Confirm no model/config/provider changes are justified by the single generic failure.

## Restrictions

Do not:
- call OpenAI;
- access real keyring;
- print raw exception text/body;
- change adapter request semantics;
- change model, endpoint, timeout, schema or retry policy;
- change commercial gate;
- change routes;
- add telemetry persistence;
- add dependencies.

## Preferred direction

Prefer a fixed explicit allowlist of safe diagnostic codes sourced from the existing adapter contract. Unknown/unexpected codes should collapse to `smoke_failed`.

A future live attempt, if separately authorized, should still be one-shot and stop on any failure.

## Deliverable

Create only:

`docs/plans/phase-6f-smoke-diagnostic-analysis.md`

Include:
- current-state findings;
- safe/unsafe code classification;
- recommended CLI output contract;
- exact proposed Scope Lock;
- offline test matrix;
- security invariants;
- verdict: READY FOR PLAN or STOP.

No code changes.
No tests.
No provider call.

Commit:

Analyze bounded phase 6F smoke diagnostics

Push only origin/codex-work.
