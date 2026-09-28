# Phase 6F Unicode Phase Observability Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Decision:** Option A approved

## Objective

Determine the smallest technically trustworthy, non-content-bearing observation mechanism that can distinguish Unicode failures occurring:

1. before request dispatch;
2. after a response has been received;

within the installed synchronous `openai==3.17.0` / `httpx2==2.13.1` path used by `Responses.create()`.

Do not implement code.
Do not call OpenAI.

## Fixed context

The eighth live smoke returned:

`provider_unicode_error_family`

Offline analysis proved both:
- a request-side Unicode failure can occur before mock dispatch;
- a response-side Unicode failure can occur after one mock dispatch.

The current adapter catches the entire `responses.create()` call as one boundary, so exception type alone cannot identify phase.

## Required local source inspection

Inspect only local installed source and repository code.

At minimum inspect:

- `openai/_base_client.py`
- `openai/_response.py`
- `openai/_httpx2.py`
- sync `Responses.create()` call path
- `httpx2.Client.send`
- `httpx2` transport request/response lifecycle
- `httpx2.BaseTransport` / sync transport interfaces
- current client construction and any supported custom transport/http-client seams
- response parsing boundary after HTTP response object creation

## Questions to resolve

1. What is the narrowest reliable boundary that proves a request was handed to the transport?
2. What is the narrowest reliable boundary that proves an HTTP response object was received?
3. Can these boundaries be observed without reading:
   - URL
   - headers
   - body
   - request content
   - response content
   - credential
   - exception message/class identity?
4. Can observation be implemented as a boolean/enum phase state only?
5. Where must state live so it is:
   - per attempt;
   - reset before each retry;
   - thread-safe under the existing one-request lock;
   - not persisted/logged?
6. Can the mechanism be introduced through an existing SDK/httpx2 supported seam rather than monkeypatching globals?
7. Would a transport wrapper be required?
8. If a transport wrapper is required, can it:
   - mark `dispatch_started` immediately before delegating;
   - mark `response_received` immediately after delegate returns a response;
   - avoid inspecting request/response fields;
   - preserve exceptions unchanged?
9. Does SDK client construction allow injecting such a transport/http client without changing production semantics?
10. Would doing so change connection pooling, proxy behavior, TLS behavior, retries, timeouts, or environment trust semantics?
11. Can the same design preserve the current default transport behavior exactly?
12. How should Unicode failures after response receipt but before SDK return be classified?
13. What happens if Unicode failure occurs before transport delegation but after phase state initialization?
14. How should phase be reset across the adapter's own retry loop?
15. What exact Scope Lock would implementation require?
16. Can all behavior be validated offline with MockTransport/no-network?
17. If no safe mechanism exists without materially changing transport behavior, return STOP.

## Preferred architecture direction

Prefer, in order:

1. an existing supported SDK hook/callback that exposes only lifecycle phase;
2. a narrowly wrapped sync transport that delegates transparently;
3. a narrowly wrapped httpx2 client if transport-only wrapping is impossible.

Avoid:
- global monkeypatching;
- reading request/response data;
- logging;
- persistence;
- dynamic exception reflection;
- changes to dependency versions;
- changes to request semantics.

## Candidate internal state

A tiny enum/constant set is acceptable in design, e.g. conceptually:

- `before_dispatch`
- `dispatch_started`
- `response_received`

Do not approve names or implementation until source inspection confirms semantics.

The state must never be user-visible by itself. It may only inform a future fixed diagnostic mapping.

## Security restrictions

Do not expose or inspect for output:
- request URL
- request headers
- request body
- response headers
- response body
- credential
- model payload
- exception class name/module/MRO
- str/repr/args/cause/context
- traceback
- socket/TLS metadata

Do not:
- call OpenAI;
- run live smoke;
- use real keyring/API key;
- access operational config/SQLite;
- make external DNS/TLS/socket probes;
- install/update/downgrade packages;
- modify model/endpoint/schema/payload/timeout/retries.

## Local tests allowed during analysis

Only no-network tests using:
- synthetic API key;
- explicit MockTransport;
- synthetic request/response;
- local fake transport/client;
- source inspection.

You may test whether a candidate wrapper:
- observes zero-dispatch failures;
- observes one-dispatch/no-response failures;
- observes response-received failures;
- preserves exact exception propagation;
- preserves call counts;
- avoids reading request/response fields.

## Deliverable

Create only:

`docs/plans/phase-6f-unicode-phase-observability-analysis.md`

Include:
- exact source lifecycle map;
- candidate mechanisms considered;
- selected mechanism or STOP;
- proof that it does not require content inspection;
- proof of semantic transparency or identified risk;
- phase-state semantics;
- retry/reset semantics;
- exact proposed Scope Lock;
- offline/no-network test matrix;
- whether new fixed diagnostic codes are justified;
- verdict: READY FOR PLAN or STOP.

No code changes.
No live access.

Commit:

Analyze phase 6F Unicode phase observability

Push only origin/codex-work.
