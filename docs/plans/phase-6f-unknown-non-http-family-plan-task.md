# Phase 6F Unknown Non-HTTP Family Classification Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-unknown-non-http-family-analysis.md — READY FOR PLAN

## Objective

Produce an implementation-ready plan for a bounded family-level refinement of the remaining `provider_non_http_failure` bucket.

Do not implement code.
Do not call OpenAI.

## Fixed evidence

The sixth live smoke still returned:

`provider_non_http_failure`

after exact classification already excluded:
- APIStatusError / HTTP mappings
- APITimeoutError
- APIConnectionError
- exact APIResponseValidationError
- exact JSONDecodeError
- exact TypeError
- exact ValueError
- exact RuntimeError

Local/no-network analysis supports a bounded family-level partition.

## Proposed family codes to plan

Plan for exactly these six new fixed literals unless a direct local-source contradiction is found:

1. `provider_openai_error_family`
   - residual `openai.OpenAIError`
   - only after all existing typed OpenAI branches

2. `provider_http_client_error_family`
   - residual `httpx2.RequestError`
   - do not use broad `httpx2.HTTPError`

3. `provider_os_error_family`
   - residual `OSError`
   - includes SSL descendants
   - must not imply DNS/TLS/firewall/proxy as root cause

4. `provider_value_subclass_family`
   - residual `ValueError` subclasses
   - exact JSONDecodeError and exact ValueError keep their existing dedicated codes
   - do not add a direct Pydantic production dependency merely for classification

5. `provider_python_internal_family`
   - only residual:
     - `TypeError` subclasses
     - `RuntimeError` subclasses
     - `AttributeError`
     - `LookupError`
     - `AssertionError`
   - exact TypeError/RuntimeError remain in their current dedicated codes
   - this must NOT become a generic catch-all for arbitrary Python exceptions

6. `provider_exception_group_family`
   - outer `ExceptionGroup` only
   - do not inspect nested members
   - do not broaden to BaseException or BaseExceptionGroup

Every remaining exception must continue to map to:
- `provider_non_http_failure`

## Critical precedence

The plan must preserve every current branch before family-level checks.

Required order:

1. existing timeout/connection/HTTP/auth/quota branches
2. existing anomalous APIStatusError -> provider_failure
3. exact APIResponseValidationError
4. exact JSONDecodeError
5. exact TypeError
6. exact ValueError
7. exact RuntimeError
8. residual openai.OpenAIError family
9. residual httpx2.RequestError family
10. residual OSError family
11. residual ValueError-subclass family
12. approved Python-internal family
13. outer ExceptionGroup
14. provider_non_http_failure fallback

If actual inheritance in installed packages creates an ordering conflict, document it and choose the narrowest safe precedence without changing prior semantics.

## Scope Lock expected

Exactly four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

A fifth tracked file is a STOP condition.

## Planning requirements

The plan must define:

1. Exact `isinstance`/exact-type rules for every new family.
2. Exact branch ordering.
3. How exact existing codes retain priority over new family codes.
4. How custom subclasses are assigned deterministically.
5. How raw `httpcore2` exceptions and unrelated exceptions remain generic fallback.
6. Exact CLI allowlist additions.
7. Exact one-attempt/no-retry semantics for all six new codes.
8. Exact no-leak invariants.
9. Exact offline/no-network test matrix.
10. Exact rollback.
11. Exact Scope Lock.
12. Confirmation that model/endpoint/schema/payload/timeout/retries/dependencies/gate are unchanged.

## Test matrix requirements

At minimum plan offline tests for:

- residual OpenAIError -> provider_openai_error_family
- residual httpx2.RequestError -> provider_http_client_error_family
- raw OSError -> provider_os_error_family
- SSL subclass -> provider_os_error_family
- UnicodeError / UnicodeDecodeError -> provider_value_subclass_family
- pydantic.ValidationError or safe synthetic ValueError subclass -> provider_value_subclass_family without requiring new production import
- TypeError subclass -> provider_python_internal_family
- RuntimeError subclass -> provider_python_internal_family
- AttributeError -> provider_python_internal_family
- KeyError / IndexError -> provider_python_internal_family through LookupError
- AssertionError -> provider_python_internal_family
- exact ExceptionGroup -> provider_exception_group_family
- raw httpcore2 exception -> provider_non_http_failure
- unrelated custom Exception -> provider_non_http_failure

Regression requirements:
- exact JSONDecodeError remains provider_response_json_failure
- exact APIResponseValidationError remains provider_response_validation_failure
- exact TypeError/ValueError/RuntimeError retain their current exact codes
- connection/timeout/HTTP/auth/quota/retry behavior unchanged
- request_schema_failure unchanged
- request kwargs unchanged
- CLI unknown/non-string/unhashable fallback unchanged

## Security restrictions

Do not expose or inspect for output:
- type(error).__name__
- type(error).__module__
- MRO
- str(error)
- repr(error)
- args
- cause/context
- nested ExceptionGroup contents
- provider body/message
- request payload
- URL/headers
- secrets

Do not:
- call OpenAI
- run live smoke
- use real keyring/API key
- access operational config/SQLite
- add dependencies
- modify package versions
- change model/endpoint/schema/payload/timeout/retries
- add transport instrumentation
- claim pre-dispatch/post-dispatch certainty

## STOP conditions

STOP if:
- a fifth file is required;
- a new dependency/import requirement is needed beyond already-installed runtime modules;
- safe classification requires dynamic class reflection;
- nested exception inspection is required;
- retry semantics must change;
- live access is needed;
- root-cause claims would exceed evidence.

## Deliverable

Create only:

`docs/plans/phase-6f-unknown-non-http-family-plan.md`

Include:
- exact mapping table;
- exact precedence;
- exact class-test rules;
- exact four-file Scope Lock;
- per-file implementation steps;
- offline/no-network tests;
- security invariants;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F unknown non-HTTP exception families

Push only origin/codex-work.
