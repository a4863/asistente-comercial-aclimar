# Phase 6F Provider Failure Classification Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-provider-failure-classification-plan.md — READY FOR IMPLEMENT

## Objective

Implement the approved bounded provider-failure refinement and expose the six new fixed categories through the synthetic smoke CLI.

No live smoke and no OpenAI call are authorized by this task.

## Exact Scope Lock

Modify exactly these four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

No fifth tracked file may change.

## Required adapter classification

Inside the existing exception handler around the Responses create expression/call:

Use a verified HTTP status only when:
- `isinstance(error, openai.APIStatusError)`
- `type(error.status_code) is int`

Do not trust arbitrary objects with a status_code attribute.
Do not inspect or emit provider message/body/param/request/URL/headers for any new branch.

Preserve branch priority and existing behavior:

1. APITimeoutError -> timeout
2. APIConnectionError -> provider_transient_exhausted
3. RateLimitError OR verified 429 -> existing quota/transient logic unchanged
4. AuthenticationError OR verified 401/403 -> provider_auth
5. verified 402 -> provider_quota
6. verified 500-599 -> provider_transient_exhausted
7. verified 400 -> provider_bad_request
8. verified 404 -> provider_not_found
9. verified 409 -> provider_conflict
10. verified 422 -> provider_unprocessable
11. any other verified 400-499 -> provider_client_error
12. remaining APIStatusError with malformed/unclassifiable status -> provider_failure
13. any other remaining non-APIStatusError exception -> provider_non_http_failure

All six new categories are non-transient and one-attempt only.

Do not change:
- retry count
- retry delay
- timeout/deadline
- request payload
- model
- endpoint
- Responses API usage
- Structured Outputs schema
- credential/gate/lock logic

## Required CLI allowlist additions

Add exactly these six literals to the existing diagnostic allowlist:

- provider_bad_request
- provider_not_found
- provider_conflict
- provider_unprocessable
- provider_client_error
- provider_non_http_failure

Preserve:
- type(code) is str before membership
- all current allowlisted codes
- generic fallback for unknown/internal/non-string/unhashable values
- all existing stdout/stderr/exit-code behavior

Do not output raw HTTP status, SDK class names or provider-controlled values.

## Tests — adapter

Extend only test/test_openai_analysis.py with fakes sufficient to prove:

1. Typed APIStatusError 400/404/409/422 -> exact new code, one attempt, no retry.
2. Other typed 4xx (e.g. 405/408/410/413) -> provider_client_error, one attempt.
3. Existing 401/402/403/429/5xx mappings and retry counts remain unchanged.
4. Existing APITimeoutError/APIConnectionError behavior remains unchanged.
5. Non-HTTP TypeError/ValueError/schema-construction error -> provider_non_http_failure.
6. Non-APIStatusError carrying forged status_code=400/429/503 -> provider_non_http_failure, no HTTP/quota/retry classification.
7. APIStatusError with bool/string/None/out-of-range/malformed status -> provider_failure.
8. Synthetic raw secret/body/path/URL/control text never appears in OpenAIAnalysisError string/repr or captured logs.
9. Request method/arguments and smoke payload remain unchanged via existing tests.

## Tests — CLI

Extend only test/test_ai_smoke_cli.py:

1. Each of six new codes -> exact `smoke_failed:<code>\n`, empty stderr, exit 1, lock released.
2. Existing allowlisted codes still work.
3. Unknown/internal/non-string/unhashable codes still collapse generically.
4. Success/help/disabled/lock_unavailable/unavailable/invalid-command/non-passed behavior unchanged.
5. No commercial gate read/change and no real keyring/config/SQLite/provider access.

## Validation

Run:

python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/integrations/openai_analysis.py
- test/test_openai_analysis.py
- app/integrations/ai_smoke_cli.py
- test/test_ai_smoke_cli.py

## Security restrictions

Never print/log:
- str(error)
- repr(error)
- provider response body
- provider message
- provider code/param
- request/URL/headers
- API key/credential reference
- raw HTTP status in CLI output

Do not:
- call OpenAI
- access real keyring
- access operational config/SQLite
- change dependencies
- change model/endpoint/schema/payload/retries/timeout/gate/routes

## STOP conditions

STOP if:
- a fifth file is required;
- a safe mapping requires raw provider content;
- retry semantics need to change;
- the pinned SDK behavior differs materially from the analyzed contract;
- live access is needed to validate.

## Completion

Commit:

Implement phase 6F provider failure classification

Push only origin/codex-work.
