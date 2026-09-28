# Phase 6F ValueError-Subclass Narrowing Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Trigger:** seventh live smoke returned `provider_value_subclass_family`

## Objective

Determine the smallest safe bounded partition of residual `ValueError` subclasses that can realistically escape installed `openai==3.17.0` `Responses.create()`, without exposing arbitrary class names, messages, reprs, tracebacks, provider bodies, URLs, headers, request payloads, or secrets.

Do not call OpenAI.

## Evidence already established

The seventh live smoke matched:
- residual `isinstance(error, ValueError)`

after exact branches had already excluded:
- exact `json.JSONDecodeError`
- exact `ValueError`

and higher-priority families had excluded:
- OpenAI timeout/connection/status/auth/quota
- exact APIResponseValidationError
- residual OpenAIError
- residual httpx2.RequestError
- residual OSError

Therefore the live exception is a ValueError subclass not already captured above.

## Required local inspection

Using only installed source/metadata, repository code, and synthetic/no-network tests, identify realistic residual ValueError subclasses from the current stack.

At minimum inspect and test family relationships for:

- `UnicodeError` and concrete Unicode subclasses
- `pydantic.ValidationError`
- pydantic-core validation errors/exceptions
- any URL/parsing/config/request-model ValueError subclasses used by:
  - openai 3.17.0
  - httpx2 2.13.1
  - httpcore2 2.13.1
  - jiter
  - idna
  - truststore
  - standard library paths exercised by Responses.create
- SDK transformation/serialization/model-construction helpers
- response parsing paths
- request preparation paths

## Required questions

1. Which concrete ValueError-subclass families can realistically escape `Responses.create()` in the installed stack?
2. Which are normally wrapped before reaching the adapter?
3. Which can be reproduced locally with the exact synthetic request and explicit no-network transports?
4. Could `pydantic.ValidationError` escape outside the existing APIResponseValidationError wrapping boundary?
5. Could a Unicode-related ValueError subclass arise from request construction, header/URL handling, serialization, response decoding, or model parsing?
6. Are there library-specific ValueError subclasses worth a fixed family code?
7. Can a small fixed family partition materially narrow the next live attempt without arbitrary class reflection?
8. What precedence is required so existing exact JSON/ValueError codes remain unchanged?
9. If safe narrowing is impossible without identifying the concrete class dynamically, return STOP rather than inventing categories.
10. Is any dependency change justified? If yes, STOP; do not modify packages.

## Preferred bounded direction

Only if justified by local source/tests, consider fixed families conceptually equivalent to:

- provider_unicode_error_family
- provider_pydantic_validation_family
- provider_value_other_family

Do not adopt these names unless the analysis supports them.

Do not expose:
- `type(error).__name__`
- `type(error).__module__`
- MRO
- hashes/fingerprints of class identity
- `str(error)`
- `repr(error)`
- `args`
- cause/context
- response/provider bodies

## Restrictions

- READ-ONLY.
- No code changes.
- No package install/update/downgrade.
- No real API key/keyring.
- No operational config/SQLite.
- No network/DNS/TLS/socket probe.
- No live smoke.
- No OpenAI call.
- No request/model/endpoint/schema/payload/timeout/retry change.

Local tests may use:
- synthetic key;
- explicit MockTransport/no-send;
- monkeypatched exception injection;
- installed source inspection.

## Deliverable

Create only:

`docs/plans/phase-6f-value-subclass-analysis.md`

Include:
- relevant ValueError subclass hierarchy;
- realistic escape paths;
- which families are wrapped vs residual;
- locally reproducible no-network cases;
- bounded classification recommendation or STOP;
- exact precedence;
- proposed Scope Lock;
- offline/no-network test matrix;
- whether another live synthetic diagnostic would be justified;
- verdict: READY FOR PLAN or STOP.

No code changes.
No provider call.

Commit:

Analyze phase 6F ValueError subclasses

Push only origin/codex-work.
