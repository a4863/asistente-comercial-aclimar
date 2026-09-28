# Phase 6F Unicode ValueError Family Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-unicode-value-family-plan.md — READY FOR IMPLEMENT

## Objective

Implement exactly one new bounded diagnostic category:

- `provider_unicode_error_family`

for residual `UnicodeError` exceptions escaping:

`client.responses.create(**request_kwargs)`

No live smoke and no OpenAI call are authorized by this task.

## Exact Scope Lock

Modify exactly these four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

No fifth tracked file may change.

## Adapter change

Inside the existing SDK-call exception classifier, preserve every existing branch and ordering.

Insert exactly:

```python
elif isinstance(error, UnicodeError):
    category, transient = "provider_unicode_error_family", False
```

Placement:

- after residual `OSError`;
- before residual `ValueError`.

Do not alter any other classification branch.

Required precedence remains:

- exact APIResponseValidationError
- exact JSONDecodeError
- exact TypeError
- exact ValueError
- exact RuntimeError
- residual OpenAIError
- residual httpx2.RequestError
- residual OSError
- NEW residual UnicodeError
- residual ValueError
- approved Python-internal family
- ExceptionGroup
- provider_non_http_failure fallback

## Required inheritance behavior

Must preserve:

- exact JSONDecodeError -> provider_response_json_failure
- exact ValueError -> provider_sdk_value_failure
- UnicodeError -> provider_unicode_error_family
- UnicodeDecodeError -> provider_unicode_error_family
- UnicodeEncodeError -> provider_unicode_error_family
- idna.IDNAError -> provider_unicode_error_family if injected/escaping by inheritance
- Pydantic ValidationError -> provider_value_subclass_family if it escapes unwrapped
- PydanticSerializationError -> provider_value_subclass_family if it escapes
- custom non-Unicode ValueError subclass -> provider_value_subclass_family

Do not claim any of those occurred in the seventh live smoke.

## CLI change

Add exactly:

- `provider_unicode_error_family`

to the private diagnostic allowlist.

Expected CLI result for that code:

- stdout: `smoke_failed:provider_unicode_error_family\n`
- stderr: empty
- exit code: 1
- lock released

Preserve all previous codes and fallback behavior.

## Adapter tests

In `test/test_openai_analysis.py`, add/adjust only offline tests proving:

1. UnicodeError -> provider_unicode_error_family
2. UnicodeDecodeError -> provider_unicode_error_family
3. UnicodeEncodeError -> provider_unicode_error_family
4. synthetic idna.IDNAError -> provider_unicode_error_family
5. each:
   - one SDK call
   - zero retry/sleep
   - lock released
   - no raw injected text leak
6. exact JSONDecodeError remains provider_response_json_failure
7. exact ValueError remains provider_sdk_value_failure
8. Pydantic validation/serialization injected residuals remain provider_value_subclass_family
9. custom non-Unicode ValueError subclass remains provider_value_subclass_family
10. all previous OpenAI/HTTP/OS/Python-family classifications remain unchanged
11. request kwargs/client factory args remain unchanged

## Pinned-SDK no-network regression

Using:
- synthetic API key only;
- installed OpenAI SDK;
- explicit `httpx2.MockTransport`;
- `trust_env=False`;
- fixed synthetic smoke request;

prove that a local 200 `application/json` response containing invalid UTF-8 bytes maps to:

`provider_unicode_error_family`

Constraints:
- one mock dispatch;
- no real network;
- do not print malformed bytes;
- do not infer this was the real seventh-smoke cause.

## CLI tests

In `test/test_ai_smoke_cli.py`:

1. Add `provider_unicode_error_family` to expected allowlist.
2. Verify exact stdout/stderr/exit behavior.
3. Verify lock release.
4. Preserve unknown/internal/non-string/unhashable fallback.
5. Preserve all prior diagnostic/success/help/disabled/lock/unavailable behavior.

## Security restrictions

Do not expose/log/derive:
- concrete exception class name/module
- MRO
- str/repr/args
- cause/context
- malformed response bytes
- provider body/message
- request payload
- URL/headers
- secrets

Do not:
- call OpenAI
- execute live smoke
- access real keyring/API key
- access operational config/SQLite
- add imports/dependencies for Pydantic/IDNA solely for production classification
- change model/endpoint/schema/payload/retries/timeout/gate/routes
- add telemetry or transport instrumentation
- attribute invalid UTF-8 to the live seventh attempt

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
- a new dependency is required;
- production classification needs a new import beyond built-ins/current runtime boundary;
- raw exception/response content is needed;
- retry semantics must change;
- live access is needed to validate;
- concrete class reflection is required.

## Completion

Commit:

Implement phase 6F Unicode ValueError family

Push only origin/codex-work.
