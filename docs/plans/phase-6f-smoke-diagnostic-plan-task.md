# Phase 6F Smoke Diagnostic Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-smoke-diagnostic-analysis.md — READY FOR PLAN
**Purpose:** make a future synthetic smoke failure diagnostically useful without exposing raw provider or security-internal details

## Objective

Produce an implementation-ready plan for a CLI-only bounded diagnostic improvement.

Do not implement code in this task.
Do not call OpenAI.

## Fixed diagnostic contract

For OpenAIAnalysisError raised by the synthetic smoke CLI:

Expose exactly these allowlisted codes:

- credential_missing
- credential_unavailable
- provider_unavailable
- provider_auth
- provider_quota
- provider_transient_exhausted
- provider_failure
- timeout
- provider_incomplete
- provider_refusal
- invalid_output
- invalid_configuration

For an allowlisted code, stdout must be exactly:

smoke_failed:<code>

with newline and exit code 1.

Collapse to exactly:

smoke_failed

for:
- operational_ownership_required
- commercial_activation_required
- busy
- smoke_already_used
- sensitive_content
- invalid_input
- disabled if unexpectedly raised by adapter rather than handled preflight
- any unknown value
- any non-string value
- any malformed/arbitrary/attacker-controlled code

Never print:
- str(error)
- repr(error)
- error body
- SDK metadata
- HTTP body/status detail beyond the mapped bounded code
- request/response content
- credential reference or secret
- endpoint/model/path
- traceback

Existing outputs remain unchanged:
- passed
- disabled
- lock_unavailable
- unavailable
- invalid_command/help behavior

stderr remains empty for adapter smoke failures.

## Expected Scope Lock

Exactly two files:

1. app/integrations/ai_smoke_cli.py
2. test/test_ai_smoke_cli.py

If any other tracked file is needed, STOP.

## Planning questions to resolve exactly

1. Exact immutable/local allowlist representation.
2. Exact helper/function structure, if any, without changing adapter API.
3. Exact behavior for non-string and unhashable error.code.
4. Exact ordering of exception handling so unexpected exceptions remain unavailable.
5. Exact output and exit-code mapping for every allowlisted code.
6. Exact fallback mapping for excluded/internal/unknown codes.
7. Exact tests proving injected raw secret/body/control/newline text never appears.
8. Exact tests proving lock release remains correct after diagnostic failures.
9. Exact tests preserving success/help/disabled/lock_unavailable/unavailable behavior.
10. Exact tests proving no commercial gate access.
11. Exact test command set and diff checks.
12. Confirm no logging changes, no adapter changes, no provider call.

## Restrictions

Do not:
- modify app/integrations/openai_analysis.py;
- modify schema/decoder;
- change model, endpoint, retries, timeout or payload;
- change credentials/keyring;
- change lock;
- change commercial gate;
- change routes/UI;
- add telemetry/logging;
- add dependency;
- call OpenAI;
- access real keyring/config/SQLite.

## Validation requirements for future implementation

At minimum:

python -m pytest test/test_ai_smoke_cli.py test/test_openai_analysis.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must contain exactly the two Scope-Locked files.

## STOP conditions

STOP if:
- any third file is needed;
- safe bounded output requires adapter changes;
- raw/provider details would need to be surfaced;
- any new functional decision appears;
- live access appears necessary.

## Deliverable

Create only:

docs/plans/phase-6f-smoke-diagnostic-plan.md

Include:
- exact output contract;
- exact allowlist/fallback behavior;
- exact two-file Scope Lock;
- per-file steps;
- offline test matrix;
- rollback;
- security invariants;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan bounded phase 6F smoke diagnostics

Push only origin/codex-work.
