# Phase 6F SDK Non-HTTP Exception Classification Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-sdk-non-http-exception-analysis.md — READY FOR PLAN

## Objective

Produce an implementation-ready plan that refines the remaining `provider_non_http_failure` bucket using only fixed, locally verified exception-class categories from the installed `openai==3.17.0` / `httpx2==2.13.1` stack.

Do not implement code.
Do not call OpenAI.

## Fixed evidence from analysis

The following local/no-network findings are accepted as design evidence:

- ordinary DNS/socket/TLS/proxy transport failures map through httpx2/OpenAI to existing `APIConnectionError` or `APITimeoutError`;
- HTTP failures map to existing `APIStatusError` branches;
- `json.JSONDecodeError` can escape from SDK response JSON parsing;
- `openai.APIResponseValidationError` can escape from SDK response-model validation;
- exact plain `TypeError`, `ValueError`, `RuntimeError` can escape from request-build/SDK/local paths;
- class alone does not prove pre-dispatch vs post-dispatch for those generic exceptions;
- no dependency inconsistency or justified package upgrade/downgrade was found.

## Proposed bounded codes to plan

Plan for exactly these new codes unless a local source/test contradiction is found:

- `provider_response_validation_failure`
  - only for `openai.APIResponseValidationError`

- `provider_response_json_failure`
  - only for `json.JSONDecodeError`

- `provider_sdk_type_failure`
  - only for exact plain `TypeError`

- `provider_sdk_value_failure`
  - only for exact plain `ValueError`

- `provider_sdk_runtime_failure`
  - only for exact plain `RuntimeError`

Keep `provider_non_http_failure` as the generic fallback for every other non-HTTP exception.

## Critical ordering/type requirements

The plan must explicitly enforce classification order so subclass relationships do not collapse categories.

At minimum:

1. Existing timeout/connection/HTTP/auth/quota branches remain first and unchanged.
2. `openai.APIResponseValidationError` must be checked before generic local classes.
3. `json.JSONDecodeError` must be checked before `ValueError`, because JSONDecodeError subclasses ValueError.
4. Generic local buckets should use exact-type checks:
   - `type(error) is TypeError`
   - `type(error) is ValueError`
   - `type(error) is RuntimeError`
   rather than broad `isinstance`, unless the plan justifies a safer alternative.
5. All remaining exceptions -> existing `provider_non_http_failure`.

Do not expose arbitrary class names.

## Expected Scope Lock

Exactly four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

If a fifth tracked file is required, STOP.

## Planning questions

1. Exact exception-handler ordering after existing typed HTTP/transport branches.
2. Exact use of `openai.APIResponseValidationError`.
3. Exact handling of `json.JSONDecodeError`.
4. Exact-type vs isinstance policy for TypeError/ValueError/RuntimeError.
5. How to preserve `provider_non_http_failure` for unknown subclasses and arbitrary exceptions.
6. Exact CLI allowlist additions.
7. Exact one-attempt/no-retry behavior for all five new categories.
8. Exact no-leak tests with secret/body/path/control-text messages.
9. Exact pinned-SDK no-network tests using synthetic key + MockTransport.
10. Exact regression tests for existing connection/timeout/HTTP/auth/quota categories.
11. Exact Scope Lock and validation commands.
12. Confirm no dependency/model/endpoint/schema/payload/timeout/retry/gate changes.

## Restrictions

Do not:
- call OpenAI;
- use real API key/keyring;
- access operational config/SQLite;
- install/upgrade/downgrade packages;
- change model;
- change endpoint;
- change Responses API usage;
- change Structured Outputs schema;
- change payload;
- change timeout/retry behavior;
- add transport instrumentation;
- claim pre-dispatch/post-dispatch certainty;
- log or expose raw exception text/body/request/URL/headers/secrets.

## Future implementation validation requirements

At minimum:

python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must contain exactly the four Scope-Locked files.

The offline test matrix must include:

- APIResponseValidationError -> exact validation code
- JSONDecodeError -> exact JSON code, not ValueError code
- exact plain TypeError -> exact type code
- exact plain ValueError -> exact value code
- exact plain RuntimeError -> exact runtime code
- subclass/custom exceptions -> generic provider_non_http_failure unless explicitly approved
- existing DNS/TLS/proxy synthetic RequestError/Timeout paths remain existing connection/timeout categories
- all new categories one attempt/no retry
- CLI exposes only fixed allowlisted literals
- unknown/non-string/unhashable values remain generic
- no raw injected text in adapter error, stdout, stderr, or logs

## STOP conditions

STOP if:
- a fifth file is required;
- raw exception/provider content is needed;
- dependency change is required;
- safe classification needs transport hooks or pre/post-dispatch instrumentation;
- retry semantics must change;
- live access is needed to validate.

## Deliverable

Create only:

`docs/plans/phase-6f-sdk-non-http-exception-plan.md`

Include:
- exact mapping table;
- exact exception ordering/type rules;
- exact four-file Scope Lock;
- per-file implementation steps;
- offline/no-network test matrix;
- security invariants;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F SDK non-HTTP exception classification

Push only origin/codex-work.
