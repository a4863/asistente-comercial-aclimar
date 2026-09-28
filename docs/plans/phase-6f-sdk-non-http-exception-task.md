# Phase 6F SDK Non-HTTP Exception Classification Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-sdk-non-http-exception-plan.md — READY FOR IMPLEMENT

## Objective

Implement the approved fixed-class refinement of the remaining `provider_non_http_failure` bucket.

No live smoke and no OpenAI call are authorized by this task.

## Exact Scope Lock

Modify exactly these four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

No fifth tracked file may change.

## Required adapter mapping

Inside the existing `except Exception as error` for:

`client.responses.create(**request_kwargs)`

preserve all current branches and retry semantics unchanged.

After the existing anomalous `APIStatusError` branch and before the final `provider_non_http_failure` fallback, add exactly:

1. `type(error) is openai.APIResponseValidationError`
   -> `provider_response_validation_failure`
   -> non-transient

2. `type(error) is json.JSONDecodeError`
   -> `provider_response_json_failure`
   -> non-transient

3. `type(error) is TypeError`
   -> `provider_sdk_type_failure`
   -> non-transient

4. `type(error) is ValueError`
   -> `provider_sdk_value_failure`
   -> non-transient

5. `type(error) is RuntimeError`
   -> `provider_sdk_runtime_failure`
   -> non-transient

6. Every other remaining exception
   -> existing `provider_non_http_failure`
   -> non-transient

Critical:
- JSONDecodeError check must remain before ValueError.
- Use exact-type checks for all five new categories.
- Do not use broad isinstance for TypeError/ValueError/RuntimeError.
- Do not reflect arbitrary class names.
- Custom subclasses remain provider_non_http_failure.

Preserve unchanged:
- APITimeoutError handling
- APIConnectionError handling
- 429/quota/rate handling
- auth handling
- all verified HTTP mappings
- malformed APIStatusError -> provider_failure
- request_schema_failure boundary
- retry counts/delay
- deadline
- request kwargs
- model/endpoint/schema/payload/token limit

## Required CLI additions

Add exactly these five literals to the existing private diagnostic allowlist:

- provider_response_validation_failure
- provider_response_json_failure
- provider_sdk_type_failure
- provider_sdk_value_failure
- provider_sdk_runtime_failure

Preserve:
- existing allowlisted codes
- type(code) is str before membership
- generic fallback for unknown/internal/non-string/unhashable values
- all current stdout/stderr/exit behavior

## Adapter tests

In `test/test_openai_analysis.py`, add/adjust only offline tests that prove:

1. Exact APIResponseValidationError -> provider_response_validation_failure.
2. Exact JSONDecodeError -> provider_response_json_failure, not provider_sdk_value_failure.
3. Exact TypeError -> provider_sdk_type_failure.
4. Exact ValueError -> provider_sdk_value_failure.
5. Exact RuntimeError -> provider_sdk_runtime_failure.
6. Each new category:
   - exactly one SDK call
   - no retry/sleep
   - lock released
   - no raw injected text leak.
7. Custom subclasses of:
   - APIResponseValidationError
   - JSONDecodeError
   - TypeError
   - ValueError
   - RuntimeError
   remain provider_non_http_failure.
8. Forged status_code on non-APIStatusError remains non-HTTP fallback behavior.
9. Existing HTTP/auth/quota/timeout/connection mappings and retry counts remain unchanged.
10. Existing request_schema_failure remains unchanged.
11. Existing request kwargs remain byte/semantic equivalent.

## Pinned-SDK offline/no-network tests

Use only synthetic API keys and explicit no-network/mock transport.

At minimum prove:

- malformed in-process JSON 200 -> exact JSONDecodeError classification;
- deliberate strict test-only response validation failure -> APIResponseValidationError classification;
- injected exact TypeError in request-build path -> type category with zero mock dispatch;
- injected exact ValueError and RuntimeError in local/mock SDK path -> correct categories;
- connection/timeout/proxy mock paths still map to existing categories;
- no default transport/network dispatch;
- no real keyring/config/SQLite.

Do not modify production strict-response-validation settings.

## CLI tests

In `test/test_ai_smoke_cli.py`:

1. Add all five new codes to expected allowlist.
2. Verify exact `smoke_failed:<code>\n`, empty stderr, exit 1, lock released.
3. Preserve provider_non_http_failure and request_schema_failure behavior.
4. Preserve generic fallback for unknown/internal/non-string/unhashable values.
5. Preserve success/help/disabled/lock_unavailable/unavailable/invalid-command behavior.
6. No gate/keyring/config/SQLite/provider real access.

## Security restrictions

Never expose/log:
- str(error)
- repr(error)
- traceback/cause
- raw SDK/provider body/message/code
- malformed JSON document
- request payload
- URL/headers
- API key/credential reference
- arbitrary class names

Do not:
- call OpenAI
- execute live smoke
- access real keyring
- access operational config/SQLite
- install/update/downgrade dependencies
- change model/endpoint/schema/payload/retries/timeout/gate/routes
- add telemetry or transport instrumentation

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

## STOP conditions

STOP if:
- a fifth file is required;
- raw exception/provider content is needed;
- dependency change is required;
- transport instrumentation is needed;
- retry semantics must change;
- live access is needed to validate.

## Completion

Commit:

Implement phase 6F SDK non-HTTP exception classification

Push only origin/codex-work.
