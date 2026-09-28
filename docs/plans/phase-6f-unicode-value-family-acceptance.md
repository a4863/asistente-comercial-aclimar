# Phase 6F Unicode ValueError Family Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-28

## Accepted implementation

Commit:
- `312b761133cee8f1bac1d1cf4efec212870d8cd8`

Exactly four files changed:
- `app/integrations/openai_analysis.py`
- `test/test_openai_analysis.py`
- `app/integrations/ai_smoke_cli.py`
- `test/test_ai_smoke_cli.py`

## Accepted mapping

Added exactly one new bounded family classification:

- residual `UnicodeError`
  -> `provider_unicode_error_family`

Placement is preserved:
- after residual `OSError`
- before residual `ValueError`

The new category is non-transient.

## Preserved precedence and behavior

Unchanged:
- exact APIResponseValidationError
- exact JSONDecodeError
- exact TypeError
- exact ValueError
- exact RuntimeError
- residual OpenAIError
- residual httpx2.RequestError
- residual OSError
- residual ValueError fallback
- Python-internal family
- ExceptionGroup family
- provider_non_http_failure fallback
- timeout/connection/auth/quota/HTTP retry behavior
- request_schema_failure
- request kwargs/client factory arguments
- model/endpoint/schema/payload
- ownership/commercial gate/smoke one-shot behavior

## CLI behavior

Added only:
- `provider_unicode_error_family`

Unknown/internal/non-string/unhashable codes continue to collapse to:
- `smoke_failed`

No raw exception/response content or concrete class identity is exposed.

## Validation

User-reported:
- focal tests: 175 passed
- full suite: 855 passed, 2 skipped, 7 warnings
- exact four-file diff
- git diff --check passed
- local SHA matches origin/codex-work
- no live smoke
- no OpenAI call

GitHub review confirms the implementation matches the approved plan and Scope Lock.

## Result

**ACCEPTED.**

No further live smoke is authorized by this acceptance. Any additional live execution requires fresh explicit user approval.
