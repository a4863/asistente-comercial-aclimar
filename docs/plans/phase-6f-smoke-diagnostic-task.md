# Phase 6F Smoke Diagnostic Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-smoke-diagnostic-plan.md — READY FOR IMPLEMENT

## Objective

Implement the approved bounded diagnostic output for the dedicated synthetic smoke CLI.

No live smoke and no OpenAI call are authorized by this task.

## Exact Scope Lock

Modify exactly:

1. app/integrations/ai_smoke_cli.py
2. test/test_ai_smoke_cli.py

No third tracked file may change.

## Required CLI contract

Declare one private module-local immutable allowlist containing exactly:

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

For OpenAIAnalysisError:
- first require `type(error.code) is str`;
- only then test exact membership in the literal allowlist;
- if allowlisted: print exactly `smoke_failed:<code>` to stdout and return 1;
- otherwise: print exactly `smoke_failed` to stdout and return 1.

Do not reflect arbitrary values.

Known excluded codes that must remain generic:
- operational_ownership_required
- commercial_activation_required
- busy
- smoke_already_used
- sensitive_content
- invalid_input
- disabled when unexpectedly raised inside adapter

Any unknown/new code must remain generic.

## Preserve exactly

- passed -> stdout, exit 0
- disabled -> stdout, exit 1
- lock_unavailable -> stdout, exit 1
- unavailable -> stdout, exit 1
- invalid_command -> stderr, exit 2
- --help usage -> stdout, exit 0
- normal non-passed return -> smoke_failed, exit 1

Exception order must remain:
1. SingleInstanceError
2. OpenAIAnalysisError
3. generic Exception

## Security restrictions

Never print/log:
- str(error)
- repr(error)
- traceback/cause
- provider body
- SDK metadata
- request/response content
- API key/credential reference
- endpoint/model/path
- arbitrary .code values

Do not:
- modify app/integrations/openai_analysis.py
- change model/endpoint/schema/retry/timeout/payload
- change keyring/credentials
- change lock/gate/routes/persistence
- add logging/telemetry/dependencies
- access real config/keyring/SQLite
- call OpenAI
- execute a live smoke

## Tests

In test/test_ai_smoke_cli.py add/adjust fake-driven tests that prove:

1. Each of the 12 allowlisted codes -> exact `smoke_failed:<code>\n`, empty stderr, exit 1.
2. Each excluded known code -> exact generic output.
3. Unknown/arbitrary strings including secret-like/body/path/URL/control/newline strings do not appear in stdout/stderr/logs.
4. Non-string/unhashable values (None, int, list, dict) collapse safely without TypeError.
5. Unexpected generic exceptions with raw secret/body preserve `unavailable\n` and do not leak content.
6. Lock release remains correct after all failures.
7. Success/help/disabled/lock_unavailable/invalid command/non-passed return stay unchanged.
8. No commercial gate read/change and no DB/provider/keyring real access.

Do not modify test/test_openai_analysis.py.

## Validation

Run:

python -m pytest test/test_ai_smoke_cli.py test/test_openai_analysis.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/integrations/ai_smoke_cli.py
- test/test_ai_smoke_cli.py

## STOP conditions

STOP if:
- a third file is required;
- safe output needs adapter changes;
- any raw provider detail must be surfaced;
- a new functional decision appears;
- a live call would be needed.

## Completion

Commit:

Implement bounded phase 6F smoke diagnostics

Push only origin/codex-work.
