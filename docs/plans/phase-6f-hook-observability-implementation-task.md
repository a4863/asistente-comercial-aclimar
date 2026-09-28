# Phase 6F Hook Observability + Deterministic Client Closure Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-hook-observability-plan.md — READY FOR IMPLEMENT

## Objective

Implement exactly the approved hook-level observability and deterministic client lifetime contract.

This task does not authorize any live provider call.

## Exact Scope Lock

Modify exactly these six tracked files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py
5. test/test_email_analysis_service.py
6. test/test_security.py

No seventh tracked file may change.

## Client construction

Use:
- openai.DefaultHttpxClient
- same approved base_url
- same single calculated initial remaining-deadline timeout
- public event_hooks only
- no explicit transport

Pass it through:
- http_client=

to the existing OpenAI client factory while preserving:
- api_key
- base_url
- max_retries=0
- timeout

Do not change:
- trust_env
- verify
- proxy behavior
- mounts
- limits
- follow_redirects
- auth
- SDK/private internals

## Lifetime contract

Exactly one SDK client per _execute().

Reuse it across all adapter-level attempts.

Close exactly once after the operation completes/fails.

Never close between retries.

If DefaultHttpxClient is constructed but SDK factory construction fails:
- close the HTTP client once;
- preserve provider_unavailable;
- suppress ordinary Exception from cleanup.

After SDK client construction:
- close the SDK client exactly once in final cleanup.

## Close failure policy

If a primary bounded operation failure already exists:
- preserve that original failure;
- suppress ordinary Exception from close;
- do not log or expose close exception data.

If the operation otherwise succeeded and close raises ordinary Exception:
- fail with exactly:
  provider_client_close_failure
- non-transient
- no retry
- no extra provider call

Do not catch BaseException merely to convert it into close failure.

## Hook state

Implement attempt-local ephemeral monotonic phase:

- before_request_hook
- request_hook_reached
- response_hook_reached

Reset to before_request_hook immediately before every Responses.create() attempt.

Request hook:
- ignore argument
- if before_request_hook -> request_hook_reached
- never demote response_hook_reached
- never inspect/log/retain request

Response hook:
- ignore argument
- set response_hook_reached
- never inspect/log/retain response

Callbacks must be synchronous, constant-time, non-blocking, non-raising.

## Unicode mapping

Preserve every existing classification and precedence.

Change only the residual UnicodeError family mapping:

- before_request_hook
  -> provider_unicode_before_request_hook

- request_hook_reached
  -> provider_unicode_request_hook_reached

- response_hook_reached
  -> provider_unicode_response_hook_reached

- no trustworthy phase state
  -> existing provider_unicode_error_family

All four are non-transient.

Do not phase-suffix any other error category.

Do not imply dispatch/provider contact/provider-origin/decoding.

## CLI

Add exactly these four bounded codes:

- provider_unicode_before_request_hook
- provider_unicode_request_hook_reached
- provider_unicode_response_hook_reached
- provider_client_close_failure

Keep:
- provider_unicode_error_family
- all existing codes
- generic smoke_failed fallback for unknown/non-string/unhashable values.

## Required tests

### openai adapter

Prove offline/no-network:

- one SDK client per _execute()
- same SDK client reused across adapter retry
- close exactly once on success
- close exactly once on all post-construction failures
- no close between retries
- supplied HTTP client closed exactly once on SDK factory failure
- no double close
- close on authorization revocation during retry
- close on timeout
- close on invalid output
- close on transient exhaustion
- close on non-transient failure

### close failure

- successful operation + close failure
  -> provider_client_close_failure
- primary bounded failure + close failure
  -> original failure preserved
- factory failure + HTTP-client cleanup failure
  -> provider_unavailable
- no raw close exception text in adapter/CLI/logs
- close failure never triggers retry/provider call

### hooks / Unicode

- pre-hook Unicode -> provider_unicode_before_request_hook
- request hook only -> provider_unicode_request_hook_reached
- response hook -> provider_unicode_response_hook_reached
- defensive no-state case -> provider_unicode_error_family
- repeated request/response hooks are monotonic
- second adapter attempt resets phase
- hook arguments are never accessed

Use objects that fail on attribute access where useful.

### regressions

Preserve:
- exact JSONDecodeError
- exact ValueError
- residual non-Unicode ValueError
- APIResponseValidationError
- OpenAI/HTTP/OS families
- auth/quota/rate/timeout/connection
- request_schema_failure
- request kwargs
- fixed smoke payload
- deadline/retry/sleep
- gate/ownership
- request lock
- one-shot smoke

### other test files

Update every affected fake module/client_factory to:
- accept http_client
- expose close()
- own/close supplied HTTP client exactly once
- preserve prior service/security assertions

No production-only bypass.

## Security restrictions

Do not inspect/store/log:
- URL
- request headers
- response headers
- request body
- response body
- credential
- model payload
- exception text
- concrete exception class/module/MRO
- traceback
- TLS/socket metadata

Do not:
- call OpenAI
- execute live smoke
- use real keyring/API key
- access operational config/SQLite
- make network/DNS/TLS/socket probes
- change dependencies/packages
- use transport wrapper
- use global/private monkeypatch in production
- change model/endpoint/schema/payload/output tokens/timeout/retry semantics

## Validation

Run focal tests covering:

- test/test_openai_analysis.py
- test/test_ai_smoke_cli.py
- test/test_email_analysis_service.py
- test/test_security.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must be exactly the six files listed above.

## STOP conditions

STOP if:
- a seventh tracked file is needed;
- dependency/package change is needed;
- public hooks cannot be used without transport replacement;
- close policy requires exposing raw exception content;
- request/retry/deadline semantics must change;
- live/provider access is needed to validate.

## Completion

Commit:

Implement phase 6F hook observability

Push only origin/codex-work.
