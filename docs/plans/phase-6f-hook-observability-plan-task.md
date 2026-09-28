# Phase 6F Hook Observability + Deterministic Client Closure Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-28

## Objective

Produce an implementation-ready plan that combines:

1. supported public HTTPX2 request/response hooks;
2. deterministic OpenAI client closure per `_execute()`;
3. attempt-local hook phase state;
4. bounded Unicode diagnostics derived only from that phase state.

Do not implement code.
Do not call OpenAI.

## Approved hook semantics

Only these meanings are permitted:

- `before_request_hook`
- `request_hook_reached`
- `response_hook_reached`

They must never be described as:
- request dispatched;
- provider contacted;
- provider received request;
- provider generated response;
- response decoded.

## Approved lifetime semantics

Exactly one SDK client per `_execute()`:
- reused across adapter retries;
- closed exactly once after operation completion/failure;
- never closed between adapter attempts.

The plan must define close behavior for:
- success;
- non-transient failure;
- transient exhausted failure;
- timeout;
- authorization revocation;
- invalid/provider output;
- unexpected bounded failure after client construction.

## Close-failure policy — must be decided in plan

The plan must choose and justify a bounded policy for `client.close()` failure.

Preferred direction:
- if a primary bounded operation failure already exists, preserve that primary failure;
- if the operation otherwise succeeded but close fails, return a fixed bounded close category rather than raw exception data;
- never retry because of close failure;
- never leak exception content.

If a different policy is proposed, justify it explicitly.

## Client construction parity

Plan must use:
- `openai.DefaultHttpxClient`;
- same base URL;
- same initial timeout;
- public event hooks only;
- no explicit transport;
- no plain httpx2.Client substitution.

The plan must preserve:
- trust_env;
- environment proxy discovery;
- default transport selection;
- TLS verification defaults;
- SDK connection limits/pooling defaults;
- redirects;
- per-request timeout override;
- SDK max_retries=0.

## Phase state

Plan an ephemeral attempt-local monotonic state:
- reset before each adapter attempt;
- request hook sets request_hook_reached;
- response hook sets response_hook_reached;
- callbacks ignore their arguments;
- callbacks do not raise/log/block;
- no persistence.

Redirect/auth multiple hook firings must only escalate state.

## Unicode diagnostic mapping

The plan must decide exact fixed codes for Unicode failures by hook phase.

Preferred bounded names from prior analysis:

- `provider_unicode_before_request_hook`
- `provider_unicode_request_hook_reached`
- `provider_unicode_response_hook_reached`

Keep `provider_unicode_error_family` as fallback if no trustworthy phase state is available.

The plan must preserve all existing higher-priority classifications and retry behavior.

## Exact proposed Scope Lock

Planning must verify whether implementation can remain within exactly these six files:

1. `app/integrations/openai_analysis.py`
2. `test/test_openai_analysis.py`
3. `app/integrations/ai_smoke_cli.py`
4. `test/test_ai_smoke_cli.py`
5. `test/test_email_analysis_service.py`
6. `test/test_security.py`

If a seventh tracked file is required, verdict must be STOP.

## Required per-file plan

Define exact changes in each of the six files, including:
- construction of `DefaultHttpxClient` with hooks;
- passing it through `OpenAI(http_client=...)`;
- deterministic client close;
- fake client close contract;
- attempt-local phase reset;
- Unicode mapping;
- CLI allowlist;
- tests.

## Offline/no-network acceptance matrix

At minimum:

### Client parity/lifetime
- one client per `_execute()`;
- same client reused across adapter retry;
- close exactly once on success;
- close exactly once on each failure family after construction;
- no close before retry loop ends;
- close on authorization revocation during retry;
- fake factories follow same contract;
- no double-close.

### Hook phases
- Unicode failure before request hook -> before_request_hook code;
- request hook fires, no response hook -> request_hook_reached code;
- response hook fires, later Unicode failure -> response_hook_reached code;
- redirect/auth multiple hook events only escalate state;
- phase reset before next adapter retry;
- no hook argument inspection.

### Regression
- exact JSONDecodeError unchanged;
- exact ValueError unchanged;
- residual non-Unicode ValueError unchanged;
- OpenAI/HTTP/auth/quota/timeout/connection codes unchanged;
- request_schema_failure unchanged;
- request kwargs unchanged;
- model/endpoint/schema/payload unchanged;
- deadline/retry/sleep behavior unchanged;
- request lock released;
- commercial gate/ownership unchanged.

### Close failure
Plan exact tests for:
- primary failure + close failure;
- success + close failure;
- bounded/no-leak output;
- no retry caused by close failure.

### CLI
- exact new diagnostic literals if approved by plan;
- existing fallback for unknown/non-string/unhashable unchanged.

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
- concrete exception class identity
- traceback
- TLS/socket metadata

Do not:
- call OpenAI;
- run live smoke;
- use real keyring/API key;
- access operational config/SQLite;
- make external network probes;
- change packages/dependencies;
- wrap/replace transport;
- use private SDK/httpx2 APIs;
- change model/endpoint/schema/payload/timeout/retry semantics.

## Deliverable

Create only:

`docs/plans/phase-6f-hook-observability-plan.md`

Include:
- exact architecture;
- exact lifetime/close policy;
- exact phase-state semantics;
- exact diagnostic mapping;
- exact six-file Scope Lock;
- per-file steps;
- offline/no-network test matrix;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F hook observability

Push only origin/codex-work.
