# Phase 6F Provider Failure Classification Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-28

## Accepted implementation

Commit:
- `731f1d49d0a13dd136b9dfbcd82127a48b31bc86`

Exactly four files changed:
- `app/integrations/openai_analysis.py`
- `test/test_openai_analysis.py`
- `app/integrations/ai_smoke_cli.py`
- `test/test_ai_smoke_cli.py`

## Accepted adapter behavior

Verified typed HTTP status requires:
- `isinstance(error, openai.APIStatusError)`
- `type(status_code) is int`

New bounded mappings:
- 400 -> `provider_bad_request`
- 404 -> `provider_not_found`
- 409 -> `provider_conflict`
- 422 -> `provider_unprocessable`
- other verified 4xx -> `provider_client_error`
- remaining non-APIStatusError failures -> `provider_non_http_failure`

Preserved:
- timeout handling
- connection/transient handling
- auth handling
- quota/rate handling
- 5xx retry behavior
- malformed/unclassifiable typed HTTP fallback -> `provider_failure`
- existing retry/deadline/request/schema/model/endpoint behavior

Forged `status_code` on non-APIStatusError objects is not trusted.

## Accepted CLI behavior

The six new fixed codes are added to the existing bounded diagnostic allowlist.

No raw HTTP status, SDK class name, provider message/body/code, URL, path, request, secret or arbitrary exception text is exposed.

Unknown/internal/non-string/unhashable values still collapse to `smoke_failed`.

## Validation

User-reported:
- focal tests: 116 passed
- full suite: 796 passed, 2 skipped, 7 warnings
- exact four-file diff
- no live smoke
- no OpenAI call

GitHub review confirms implementation matches the approved classification and Scope Lock.

## Result

**ACCEPTED.**

No further live smoke is authorized by this acceptance. Any additional live execution requires fresh explicit user approval.
