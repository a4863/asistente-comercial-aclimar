# Phase 6F Unicode Path Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Trigger:** eighth live smoke returned `provider_unicode_error_family`

## Objective

Determine which Unicode-related paths can realistically raise a `UnicodeError` from installed `openai==3.17.0` `Responses.create()` using the fixed synthetic request, and whether offline evidence can safely distinguish response-decoding from request-preparation or other Unicode processing without exposing raw content.

Do not call OpenAI.

## Evidence already established

The eighth live smoke matched:
- residual `isinstance(error, UnicodeError)`

after exact and higher-priority categories had already been excluded.

A prior no-network reproduction showed that a 200 `application/json` response containing invalid UTF-8 bytes can propagate a Unicode-family exception through the SDK with the exact fixed synthetic request.

That reproduction is plausible evidence, not proof of the live cause.

## Required local inspection

Using only installed source/metadata, repository code, and no-network synthetic tests, inspect Unicode operations in the exact synchronous path for:

- request text encoding/serialization
- URL/header encoding
- OpenAI request construction
- httpx2 request serialization
- response byte decoding
- `Response.json()`
- stdlib `json.loads(bytes)`
- response text decoding
- model parsing/transformation
- any truststore/IDNA/string-normalization path
- any SDK helper that may decode/encode text

## Required questions

1. Which concrete Unicode subclasses can realistically escape `Responses.create()` in this fixed request path?
2. Which request-side Unicode operations are already completed before the SDK-call boundary and therefore cannot explain the live category?
3. Which SDK/httpx2 response-side operations can naturally raise UnicodeError without first becoming JSONDecodeError, RequestError, APIError, or OSError?
4. Can invalid UTF-8/UTF-16/UTF-32 BOM/content patterns be reproduced with the exact request and MockTransport?
5. Does `httpx2.Response.json()` delegate bytes directly to stdlib JSON in this installed version, and what Unicode exceptions escape?
6. Could headers/content-type/charset produce a UnicodeError in this path?
7. Could a Unicode error occur during SDK response-model parsing after JSON decode?
8. Are there request-side UnicodeEncodeError paths possible with the actual fixed request values?
9. Can a bounded next diagnostic safely distinguish:
   - response Unicode decoding family
   - request/build Unicode encoding family
   without exposing class names/content?
10. If such distinction cannot be proven without instrumentation or raw content, return STOP.
11. Does any dependency change become justified? If yes, STOP; do not modify packages.

## Preferred direction

Only if local source/tests justify it, consider a minimal phase distinction such as:
- provider_response_unicode_failure
- provider_request_unicode_failure

Do not adopt these names unless the boundaries can be proven locally.

Do not expose:
- concrete class name/module
- MRO
- str/repr/args
- cause/context
- response bytes/body
- request payload
- URL/headers
- fingerprints

## Restrictions

- READ-ONLY.
- No code changes.
- No package install/update/downgrade.
- No real keyring/API key.
- No operational config/SQLite.
- No external DNS/TLS/socket/provider probe.
- No live smoke.
- No OpenAI call.
- No model/endpoint/schema/payload/timeout/retry change.
- No raw exception/content disclosure.

Local tests may use:
- synthetic API key;
- explicit MockTransport/no-send;
- synthetic byte responses;
- monkeypatched local Unicode exceptions;
- installed source inspection.

## Deliverable

Create only:

`docs/plans/phase-6f-unicode-path-analysis.md`

Include:
- exact Unicode operations in the fixed request path;
- which request-side paths are impossible/already outside the SDK boundary;
- which response-side paths are realistically reachable;
- no-network reproductions;
- bounded next diagnostic recommendation or STOP;
- proposed Scope Lock;
- offline/no-network test matrix;
- whether another live synthetic diagnostic is justified;
- verdict: READY FOR PLAN or STOP.

No code changes.
No provider call.

Commit:

Analyze phase 6F Unicode paths

Push only origin/codex-work.
