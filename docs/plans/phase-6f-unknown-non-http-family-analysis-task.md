# Phase 6F Unknown Non-HTTP Exception Family Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Trigger:** sixth live smoke still returned `provider_non_http_failure` after exact-class refinement

## Objective

Determine the smallest safe family-level classification that can identify the remaining live exception without exposing arbitrary class names, messages, reprs, tracebacks, provider bodies, URLs, headers, payloads, or secrets.

Do not call OpenAI.

## Evidence already established

The current adapter separately classifies:
- request_schema_failure before SDK call;
- OpenAI timeout/connection/API status branches;
- exact APIResponseValidationError;
- exact JSONDecodeError;
- exact TypeError;
- exact ValueError;
- exact RuntimeError.

The sixth live smoke still reached `provider_non_http_failure`.

The dashboard previously showed the API key as Active with Last used: Never and $0 spend after repeated smoke attempts. Treat that as strong but not conclusive evidence that provider processing may not have been reached.

## Required local inspection

Using only local installed source, metadata, repository code, and no-network synthetic tests, inspect realistic remaining exception families from:
- openai 3.17.0
- httpx2 2.13.1
- httpcore2 2.13.1
- pydantic / pydantic-core
- truststore / ssl
- Python 3.13 runtime

At minimum evaluate family membership and escape feasibility for:
- openai.OpenAIError / APIError subclasses not already classified
- httpx2.HTTPError / RequestError / ProtocolError / DecodingError families
- httpcore2 exception families that could escape wrapping
- pydantic.ValidationError / pydantic-core validation exceptions
- OSError / ssl.SSLError / SSLCertVerificationError
- UnicodeError
- AttributeError
- KeyError
- IndexError
- AssertionError
- LookupError
- ExceptionGroup / BaseExceptionGroup where catchable by Exception
- any SDK-specific response/parsing exception found locally

## Required questions

1. Which of the above families can realistically escape `Responses.create()` in the installed stack and reach the adapter fallback?
2. Which are normally wrapped and therefore unlikely unless raised outside the ordinary wrapped region?
3. Which are subclasses of built-ins already checked with exact-type and therefore intentionally missed?
4. Can a small family-level mapping use `isinstance` safely without collapsing existing typed categories?
5. What precedence would avoid misclassification?
6. Can fixed family codes materially narrow the next live failure without exposing arbitrary class names?
7. Are there locally reproducible candidates using only synthetic/no-network tests?
8. Is a one-time safe exception fingerprint necessary? If so, STOP and explain the minimum design; do not implement or expose it under this task.
9. Does any evidence justify changing dependencies? If yes, STOP; do not change them.
10. Define exact Scope Lock and offline test matrix for the next plan if READY FOR PLAN.

## Preferred design direction

Prefer a small bounded family vocabulary only if justified by local source/tests, for example categories conceptually equivalent to:
- provider_openai_error_family
- provider_http_client_error_family
- provider_os_error_family
- provider_validation_error_family
- provider_runtime_lookup_failure

Do not use these names unless the analysis supports them.

Do not expose:
- `type(error).__name__`
- `type(error).__module__`
- MRO
- arbitrary hash/fingerprint derived from class name
- str/repr/args/cause/context

If class identity cannot be safely narrowed using pre-approved family checks, return STOP rather than inventing a diagnostic.

## Restrictions

- READ-ONLY.
- No code modification.
- No package install/update/downgrade.
- No real keyring/API key.
- No operational config/SQLite.
- No DNS/TLS/socket/provider probe.
- No live smoke.
- No OpenAI call.
- No raw exception content.
- No model/endpoint/schema/payload/timeout/retry change.

Local tests may use:
- synthetic key;
- explicit MockTransport/no-send;
- monkeypatched local exception injection;
- installed source inspection.

## Deliverable

Create only:

`docs/plans/phase-6f-unknown-non-http-family-analysis.md`

Include:
- installed exception-family hierarchy relevant to the path;
- which families can/cannot realistically escape;
- subclass relationships explaining why exact-type diagnostics missed them;
- bounded family-level classification recommendation or STOP;
- precedence rules if applicable;
- exact proposed Scope Lock;
- offline/no-network test matrix;
- whether any safe further live diagnostic is justified;
- verdict: READY FOR PLAN or STOP.

No code changes.
No provider call.

Commit:

Analyze phase 6F unknown non-HTTP exception families

Push only origin/codex-work.
