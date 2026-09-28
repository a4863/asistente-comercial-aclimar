# Phase 6F Local vs SDK Diagnostic Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-28

## Accepted implementation

Commit:
- `96a5084`

Exactly four files changed:
- `app/integrations/openai_analysis.py`
- `test/test_openai_analysis.py`
- `app/integrations/ai_smoke_cli.py`
- `test/test_ai_smoke_cli.py`

## Accepted behavior

A new bounded diagnostic category is introduced:

- `request_schema_failure`

It is emitted only when local per-attempt response-schema/request-kwargs construction raises before `client.responses.create()` is invoked.

The SDK call is now isolated as:

`client.responses.create(**request_kwargs)`

and preserves the existing exception classification and retry/deadline behavior, including:
- timeout
- connection/transient
- quota/rate
- auth
- typed HTTP mappings
- provider_failure
- provider_non_http_failure

No pre-dispatch/post-dispatch claim is added for exceptions raised by the SDK call.

## CLI behavior

The synthetic smoke CLI allowlist adds only:
- `request_schema_failure`

Expected bounded output:
- `smoke_failed:request_schema_failure`

Unknown/internal/non-string/unhashable values still collapse to `smoke_failed`.

## Validation

User-reported:
- focal tests: 119 passed
- full suite: 799 passed, 2 skipped, 7 warnings
- exact four-file diff
- git diff --check passed
- no live smoke
- no OpenAI call

GitHub review confirms the implementation matches the approved phase boundary and Scope Lock.

## Result

**ACCEPTED.**

No further live smoke is authorized by this acceptance. Any additional live execution requires fresh explicit user approval.
