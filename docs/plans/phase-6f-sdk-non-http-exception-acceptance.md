# Phase 6F SDK Non-HTTP Exception Classification Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-28

## Accepted implementation

Commit:
- `59ed7b6b0b66517208f534c39c9c969088a63d4e`

Exactly four files changed:
- `app/integrations/openai_analysis.py`
- `test/test_openai_analysis.py`
- `app/integrations/ai_smoke_cli.py`
- `test/test_ai_smoke_cli.py`

## Accepted mappings

Added exact-type bounded categories:
- `openai.APIResponseValidationError` -> `provider_response_validation_failure`
- `json.JSONDecodeError` -> `provider_response_json_failure`
- exact `TypeError` -> `provider_sdk_type_failure`
- exact `ValueError` -> `provider_sdk_value_failure`
- exact `RuntimeError` -> `provider_sdk_runtime_failure`

Ordering requirement is preserved:
- JSONDecodeError before ValueError.

Custom subclasses and every other remaining non-HTTP exception continue to map to:
- `provider_non_http_failure`

All new categories are non-transient and do not change retry behavior.

## Preserved behavior

Unchanged:
- request_schema_failure boundary
- timeout/connection handling
- auth/quota/rate handling
- typed HTTP mappings
- provider_failure fallback for anomalous APIStatusError
- request kwargs
- model/endpoint/schema/payload
- retry/deadline semantics
- commercial gate/ownership boundaries

## CLI behavior

The five new fixed literals are added to the bounded diagnostic allowlist.

Unknown/internal/non-string/unhashable codes still collapse to:
- `smoke_failed`

No raw exception class name, message, body, request, URL, header, secret, or payload is exposed.

## Validation

User-reported:
- focal tests: 141 passed
- full suite: 821 passed, 2 skipped, 7 warnings
- exact four-file diff
- git diff --check passed
- no live smoke
- no OpenAI call

GitHub review confirms the implementation matches the approved plan and Scope Lock.

## Result

**ACCEPTED.**

No further live smoke is authorized by this acceptance. Any additional live execution requires fresh explicit user approval.
