# Phase 6F Hook-Level Observability Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Decision:** hook-level observability approved

## Objective

Determine whether supported HTTPX2 request/response event hooks can be added to the OpenAI client used by the assistant while preserving the current production behavior of the SDK's default client.

The analysis must prove or reject semantic parity for the client configuration before any implementation is planned.

Do not implement code.
Do not call OpenAI.

## Fixed semantic contract

Only these phase meanings are allowed:

- before_request_hook
- request_hook_reached
- response_hook_reached

Do not rename them into stronger claims.

Specifically:
- request_hook_reached does NOT mean transport dispatch started;
- response_hook_reached does NOT prove provider identity or decoded response content.

## Required source inspection

Inspect only local installed source and repository code.

At minimum inspect:

- openai==3.17.0 default sync client construction
- DefaultHttpxClient
- SDK wrapping of a supplied httpx2.Client
- httpx2==2.13.1 Client constructor defaults
- event_hooks behavior and callback timing
- trust_env
- environment proxy discovery
- proxy mounts
- verify/TLS defaults
- connection limits
- timeout defaults and per-request timeout override
- redirect defaults
- client close/ownership behavior
- transport selection
- auth handling
- retry interaction
- current OpenAIAnalysis client factory construction

## Questions to resolve

1. Can the SDK default client be instantiated with request/response hooks without changing any other effective defaults?
2. Does using `openai.DefaultHttpxClient(..., event_hooks=...)` preserve:
   - trust_env
   - environment proxy discovery
   - default transport selection
   - TLS verification
   - connection limits
   - redirect behavior
   - default timeout behavior
   - connection pooling?
3. Does supplying that client through `http_client=` to `openai.OpenAI` preserve SDK ownership/lifetime expectations?
4. Would current `client_factory` test injection need semantic changes?
5. Can hooks update only a tiny attempt-local state object without reading request/response fields?
6. Can callbacks be synchronous, non-blocking and exception-free?
7. How is phase state reset before each adapter retry?
8. What state should be used if:
   - failure happens before request hook;
   - request hook fires then SDK/HTTPX2 raises before response hook;
   - response hook fires then Unicode failure occurs later during body read/JSON/model parsing?
9. Can the resulting phase be combined with `provider_unicode_error_family` to produce new fixed diagnostics without changing retry behavior?
10. What exact new codes, if any, would be justified by the evidence?
11. Can all of this be validated offline with MockTransport/no-network while also proving constructor/default parity?
12. Is there any hidden difference between the SDK-created default client and an explicitly created DefaultHttpxClient with hooks?
13. If semantic parity cannot be demonstrated, STOP.

## Preferred implementation shape if viable

Prefer:
- a tiny attempt-local phase holder;
- public request hook sets request_hook_reached;
- public response hook sets response_hook_reached;
- no request/response field access;
- no persistence/logging;
- no transport wrapper;
- no global monkeypatch;
- no private SDK/httpx2 override.

Do not approve actual implementation here.

## Security restrictions

Do not inspect/output/store:
- URL
- request headers
- response headers
- request body
- response body
- credential
- model payload
- exception message
- concrete exception class name/module/MRO
- traceback
- TLS/socket metadata

Do not:
- call OpenAI;
- run live smoke;
- use real keyring/API key;
- access operational config/SQLite;
- make external network probes;
- install/update/downgrade packages;
- change model/endpoint/schema/payload/timeout/retries.

## Local tests allowed

No-network only:
- synthetic key;
- explicit MockTransport;
- local hook callbacks;
- constructor/default comparison;
- local fake response/failure paths.

You may compare known public/default configuration values and behavior, but do not inspect secrets or external environment values beyond presence/behavior needed to prove parity.

## Deliverable

Create only:

`docs/plans/phase-6f-hook-observability-analysis.md`

Include:
- exact SDK/default-client construction map;
- parity analysis for DefaultHttpxClient + hooks;
- ownership/lifetime findings;
- retry/reset semantics;
- proposed phase-state contract;
- proposed fixed diagnostic codes, if justified;
- exact proposed Scope Lock;
- offline/no-network test matrix;
- verdict: READY FOR PLAN or STOP.

No code changes.
No live access.

Commit:

Analyze phase 6F hook observability

Push only origin/codex-work.
