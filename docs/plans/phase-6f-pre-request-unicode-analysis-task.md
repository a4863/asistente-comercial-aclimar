# Phase 6F Pre-Request-Hook Unicode Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Trigger:** ninth live smoke returned `provider_unicode_before_request_hook`

## Objective

Identify the realistic Unicode-raising operations that can occur inside the installed synchronous OpenAI/HTTPX2 stack **after entering `Responses.create()` but before the public HTTPX2 request hook fires**, using the exact fixed synthetic smoke request.

Do not inspect the real API key.
Do not call OpenAI.

## Established evidence

The ninth live smoke matched:
- residual UnicodeError;
- hook phase `before_request_hook`.

Therefore the failure occurred before the public request hook callback executed.

Prior offline analysis already demonstrated that a synthetic non-ASCII credential can produce a pre-hook Unicode failure, but that does NOT prove the live credential is the cause.

## Required local source inspection

Inspect only installed local source and repository code.

Trace exact synchronous execution from:

`client.responses.create(**request_kwargs)`

through:
- request transformation;
- SDK request option construction;
- auth/header construction;
- default headers;
- idempotency/request identifiers if any;
- URL/base_url joining;
- JSON serialization;
- HTTPX2 Request construction;
- timeout/auth preparation;
- Client.send() entry;
- code executed before request event hooks.

At minimum inspect:
- openai==3.17.0 Responses.create
- openai._base_client request/build path
- openai auth/default-header logic
- openai request serialization helpers
- openai.DefaultHttpxClient / HTTPX2 Client.build_request / send
- httpx2 header normalization/encoding
- URL/request model construction
- auth flow setup before request hook

## Questions to resolve

1. Exactly which operations execute before the public request hook?
2. Which of those can naturally raise a UnicodeError?
3. Which are impossible for the fixed ASCII model/base_url/route/instructions/schema/payload?
4. Can header encoding raise UnicodeEncodeError before the hook?
5. Which header values are dynamic in the real smoke path?
6. Is the Authorization header constructed before the request hook?
7. Does HTTPX2 require header values to be ASCII or another limited byte encoding?
8. Can a syntactically valid but non-ASCII API key reproduce the exact pre-hook Unicode family offline?
9. Can whitespace/newline/control characters in a synthetic key lead to another bounded category instead?
10. Can the same pre-hook Unicode state be produced by any non-credential value under the exact fixed request?
11. Can the likely cause be narrowed further **without reading the real credential value**?
12. Is there a safe local validation of the credential's structural character class that does not expose, log, hash, persist, or transmit the credential?
13. If such validation would inspect the real key, STOP and propose an operator-side remediation instead of code instrumentation.
14. Is any code change actually justified, or is this now an operational credential issue candidate?
15. If evidence points to credentials as the only realistic variable pre-hook Unicode source, state that as a bounded hypothesis, not a proven fact.

## Required offline reproductions

Using only synthetic credentials and no-network clients/transports, test at minimum:

- ASCII synthetic key control;
- Unicode code point outside header encoding range;
- accented Latin-1-like character;
- emoji;
- leading/trailing spaces;
- newline/control character if safely testable;
- fixed request values unchanged.

Record only predetermined labels and bounded categories; do not print key content or raw exceptions.

Determine whether each case fails:
- before request hook;
- at request hook;
- later.

## Security restrictions

Do not:
- inspect/read/print/hash the real credential;
- call keyring;
- use real API key;
- call OpenAI;
- run live smoke;
- access operational config/SQLite;
- make external DNS/TLS/socket probes;
- install/update/downgrade packages;
- print exception class/message/module/MRO;
- print headers, request body, URL, credential, response body;
- add production code;
- alter model/endpoint/schema/payload/timeout/retries.

## Preferred outcome

If local source + synthetic tests show that all fixed request fields are safe and only a dynamic credential/header value plausibly explains the pre-hook Unicode path, recommend the smallest operator-side next step.

That next step may be:
- delete/reset credential through the existing secure CLI;
- set a freshly copied API key interactively;
- re-check only presence;
- require fresh authorization before any further smoke.

Do NOT inspect the key to prove this.

If multiple non-credential pre-hook Unicode sources remain plausible, return a bounded decision rather than guessing.

## Deliverable

Create only:

`docs/plans/phase-6f-pre-request-unicode-analysis.md`

Include:
- exact pre-hook lifecycle map;
- realistic Unicode sources;
- synthetic reproduction matrix;
- fixed vs dynamic inputs;
- whether credential corruption/character encoding is the leading bounded hypothesis;
- whether code changes are justified;
- operator remediation recommendation if appropriate;
- whether another live synthetic smoke could be justified after remediation;
- verdict: READY FOR PLAN, OPERATOR ACTION, or STOP.

No code changes.
No live access.

Commit:

Analyze phase 6F pre-request Unicode failure

Push only origin/codex-work.
