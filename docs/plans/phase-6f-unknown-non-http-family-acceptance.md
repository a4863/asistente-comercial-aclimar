# Phase 6F Unknown Non-HTTP Family Classification Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-28

## Accepted implementation

Commit:
- `2af11cad4cbdf7084d958ae91021ddb0f66ddd25`

Exactly four files changed:
- `app/integrations/openai_analysis.py`
- `test/test_openai_analysis.py`
- `app/integrations/ai_smoke_cli.py`
- `test/test_ai_smoke_cli.py`

## Accepted family mappings

After all previously accepted exact classifications, the adapter now maps:

- residual `openai.OpenAIError`
  -> `provider_openai_error_family`

- residual `httpx2.RequestError`
  -> `provider_http_client_error_family`

- residual `OSError`
  -> `provider_os_error_family`

- residual `ValueError` subclasses
  -> `provider_value_subclass_family`

- residual approved Python structural families:
  - TypeError subclasses
  - RuntimeError subclasses
  - AttributeError
  - LookupError
  - AssertionError
  -> `provider_python_internal_family`

- outer `ExceptionGroup`
  -> `provider_exception_group_family`

Every other remaining exception continues to map to:
- `provider_non_http_failure`

All new family categories are non-transient.

## Preserved precedence

Unchanged and higher priority:
- APITimeoutError
- APIConnectionError
- auth/quota/rate/HTTP branches
- anomalous APIStatusError -> provider_failure
- exact APIResponseValidationError
- exact JSONDecodeError
- exact TypeError
- exact ValueError
- exact RuntimeError

No broad `httpx2.HTTPError` classification was added.

## Preserved boundaries

Unchanged:
- request_schema_failure
- request kwargs
- client factory arguments
- model/endpoint/schema/payload
- deadline/retry semantics
- ownership
- commercial activation gate
- synthetic smoke one-shot behavior

`httpx2` is imported lazily inside the existing provider-construction boundary. No dependency change was introduced.

## CLI behavior

Six new fixed literals are allowlisted:
- provider_openai_error_family
- provider_http_client_error_family
- provider_os_error_family
- provider_value_subclass_family
- provider_python_internal_family
- provider_exception_group_family

Unknown/internal/non-string/unhashable codes remain collapsed to:
- `smoke_failed`

No raw class name, message, traceback, body, request, URL, header, secret, MRO, cause/context, or nested ExceptionGroup member is exposed.

## Validation

User-reported:
- focal tests: 169 passed
- full suite: 849 passed, 2 skipped, 7 warnings
- exact four-file diff
- git diff --check passed
- no live smoke
- no OpenAI call

GitHub review confirms the implementation matches the approved plan and Scope Lock.

## Result

**ACCEPTED.**

No further live smoke is authorized by this acceptance. Any additional live execution requires fresh explicit user approval.
