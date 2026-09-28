# Phase 6F Hook Observability + Deterministic Client Closure Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-28

## Accepted implementation

Commit:

`5e239d08e01ca33f071964f575fa4ee5abfc21f3`

Exactly six tracked files changed:

1. `app/integrations/openai_analysis.py`
2. `test/test_openai_analysis.py`
3. `app/integrations/ai_smoke_cli.py`
4. `test/test_ai_smoke_cli.py`
5. `test/test_email_analysis_service.py`
6. `test/test_security.py`

## Accepted client construction

Production uses:
- `openai.DefaultHttpxClient`;
- same approved base URL;
- one calculated initial remaining-deadline timeout;
- public request/response event hooks only;
- no explicit transport.

The supplied HTTP client is passed through `http_client=` while preserving:
- API key handling;
- base URL;
- SDK `max_retries=0`;
- timeout semantics.

No transport wrapper or private SDK/HTTPX2 API is introduced.

## Accepted hook semantics

Attempt-local states:

- `before_request_hook`
- `request_hook_reached`
- `response_hook_reached`

State resets before every adapter-level provider attempt.

These labels are intentionally weak and MUST NOT be interpreted as:
- request dispatched;
- provider contacted;
- provider received request;
- provider-generated response;
- response decoded.

## Accepted Unicode mapping

Residual Unicode failures map to:

- before_request_hook
  -> `provider_unicode_before_request_hook`
- request_hook_reached
  -> `provider_unicode_request_hook_reached`
- response_hook_reached
  -> `provider_unicode_response_hook_reached`
- defensive untrusted/no-state fallback
  -> existing `provider_unicode_error_family`

All other classification precedence remains unchanged.

## Accepted deterministic lifetime

Exactly one SDK client is created per `_execute()` and reused across adapter retries.

After successful SDK client construction:
- close is attempted exactly once at operation end;
- no close occurs between retries.

If SDK client construction fails after the HTTP client exists:
- the HTTP client is closed once;
- `provider_unavailable` is preserved;
- ordinary cleanup failures are suppressed.

Close-failure policy:
- primary bounded failure already exists -> preserve primary failure;
- otherwise successful operation + ordinary close failure -> `provider_client_close_failure`;
- no retry or additional provider call caused by close failure.

## CLI

Added bounded diagnostics:

- `provider_unicode_before_request_hook`
- `provider_unicode_request_hook_reached`
- `provider_unicode_response_hook_reached`
- `provider_client_close_failure`

Existing `provider_unicode_error_family` and generic fallback remain.

## Validation

User-reported:

- focal tests: **268 passed**
- full suite: **874 passed, 2 skipped**
- exact six-file Scope Lock
- `git diff --check`: PASS
- tracked state clean
- local and origin commit: `5e239d08e01ca33f071964f575fa4ee5abfc21f3`
- no OpenAI call
- no live smoke

GitHub review confirms the production changes match the approved architecture and Scope Lock.

## Result

**ACCEPTED.**

This acceptance does not authorize a ninth live smoke. Any further live synthetic execution requires fresh explicit user authorization.
