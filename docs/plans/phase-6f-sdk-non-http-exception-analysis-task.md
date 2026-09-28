# Phase 6F SDK Non-HTTP Exception Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Trigger:** fifth live smoke returned `provider_non_http_failure` after local schema/kwargs separation

## Objective

Determine which concrete exception classes can escape from installed `openai==3.17.0` during `Responses.create()` without being an `APIStatusError`, `APIConnectionError`, or `APITimeoutError`, and define the smallest safe bounded classification needed to identify the live failure class on a future separately authorized smoke.

Do not call OpenAI.

## Evidence already established

- The operational interpreter is Python 3.13.
- Installed SDK is `openai==3.17.0`.
- Exact synthetic request schema/kwargs build successfully offline.
- Exact request serializes and passes through the installed SDK using an explicit no-network mock transport.
- The fifth live smoke still returns `provider_non_http_failure`.
- The failure occurs inside `client.responses.create(**request_kwargs)`.

## Required local inspection

Inspect only local installed source/metadata and repository code.

At minimum inspect:
1. `openai/_exceptions.py`
2. base client request/send/response parsing paths used by Responses.create
3. the installed HTTP transport dependency and exception hierarchy actually used by this SDK version
4. response parsing/model validation code paths
5. any Python 3.13-specific compatibility paths visible in installed dependencies
6. exception translation boundaries: which underlying transport/parser exceptions are wrapped, and which can escape unwrapped

## Questions to resolve

1. Enumerate the realistic non-HTTP exception classes that can escape `Responses.create()` in this pinned SDK.
2. Which arise:
   - before network dispatch,
   - during transport,
   - after receiving a response,
   while avoiding claims that cannot be proven from source.
3. Which of those are already subclasses of APIConnectionError/APITimeoutError and therefore should never reach provider_non_http_failure?
4. Which response parsing/validation exceptions can reach the catch unwrapped?
5. Can Python 3.13 + installed transport/package versions create a compatibility exception not wrapped by OpenAI?
6. Is the locally installed OpenAI dependency graph internally consistent?
7. Can a synthetic local HTTP server or explicit mock transport reproduce candidate unwrapped exceptions without external network?
8. What fixed diagnostic vocabulary is safe to expose?
   Prefer exact known exception-class buckets, not arbitrary class-name reflection.
9. Can classification be implemented without reading/printing exception messages, repr, response body, URL, request payload, key, or headers?
10. What exact Scope Lock would be needed?
11. Would any dependency upgrade/downgrade be justified by local evidence? If yes, STOP and report; do not change dependencies under this task.
12. Define tests that prove each bounded class and no-leak behavior offline.

## Preferred direction

If source inspection identifies a small known set of unwrapped exception classes, propose fixed codes such as:
- provider_response_validation_failure
- provider_transport_local_failure
- provider_sdk_internal_failure

Do not adopt these names unless justified by exact source paths.

Avoid exposing arbitrary Python class names directly.

## Restrictions

Do not:
- call OpenAI;
- use real API key/keyring;
- access operational SQLite;
- change model/endpoint/schema/payload/timeout/retries;
- install/upgrade/downgrade packages;
- expose raw exception strings/repr/tracebacks;
- add telemetry or persistence.

Local synthetic tests may use:
- synthetic API key;
- explicit no-network transport;
- in-process fake/local responses;
- installed package source inspection.

## Deliverable

Create only:

`docs/plans/phase-6f-sdk-non-http-exception-analysis.md`

Include:
- exact installed dependency versions relevant to this path;
- exception translation map;
- realistic unwrapped exception classes;
- likely bounded classification strategy;
- whether dependency inconsistency exists;
- exact proposed Scope Lock;
- offline/no-network test matrix;
- verdict: READY FOR PLAN or STOP.

No code changes.
No provider call.

Commit:

Analyze phase 6F SDK non-HTTP exceptions

Push only origin/codex-work.
