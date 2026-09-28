# Phase 6F Provider Failure Classification Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY
**Trigger:** second live synthetic smoke returned `smoke_failed:provider_failure`

## Objective

Determine the smallest safe offline correction that decomposes the adapter's generic `provider_failure` category into bounded actionable categories for common non-transient OpenAI HTTP/SDK failures, without exposing raw provider details.

Do not call OpenAI.

## Current known behavior

The adapter currently maps:

- timeout -> timeout
- connection/5xx/most 429 -> provider_transient_exhausted
- 401/403/authentication -> provider_auth
- 402/quota-specific 429 -> provider_quota
- all other provider exceptions -> provider_failure

The second live smoke reached `provider_failure`.

## Questions to resolve

1. Which OpenAI SDK exception classes/status codes can currently fall into `provider_failure`?
2. At minimum inspect behavior for:
   - HTTP 400 / BadRequestError
   - HTTP 404 / NotFoundError
   - HTTP 409 / ConflictError
   - HTTP 422 / UnprocessableEntityError
   - other APIStatusError 4xx
   - SDK-local TypeError/validation errors from request construction
3. Which bounded categories are safe and useful to add, e.g.:
   - provider_bad_request
   - provider_not_found
   - provider_conflict
   - provider_unprocessable
   - provider_client_error
   Do not assume these names; justify exact vocabulary.
4. Can status-only mapping be performed without inspecting/printing provider body/message?
5. Should SDK-local request construction errors be distinguishable from HTTP provider errors?
6. Which new codes would need to be added to the smoke CLI allowlist later?
7. Can the correction be limited to:
   - app/integrations/openai_analysis.py
   - test/test_openai_analysis.py
   - app/integrations/ai_smoke_cli.py
   - test/test_ai_smoke_cli.py
   or can it be smaller?
8. What tests prove no body/message/secret leakage?
9. Can all analysis and validation be performed entirely with fake SDK errors/statuses?
10. Confirm no change to model, endpoint, schema, retry, timeout, payload or commercial gate is justified yet.
11. Review current official OpenAI API/SDK semantics for Responses + Structured Outputs and current model availability only as evidence, not as permission to alter config.
12. Define STOP conditions if a safe category cannot distinguish likely causes without raw provider content.

## Restrictions

Do not:
- call OpenAI;
- access real keyring/config/SQLite;
- print/log raw provider exceptions, bodies or messages;
- change model;
- change endpoint;
- change Structured Outputs schema;
- change request payload;
- change timeout/retry policy;
- change commercial gate;
- add telemetry/persistence;
- add dependencies.

## Deliverable

Create only:

`docs/plans/phase-6f-provider-failure-classification-analysis.md`

Include:
- exact current fallthrough paths to provider_failure;
- recommended bounded status/exception classification;
- security rationale;
- exact proposed Scope Lock;
- offline test matrix;
- whether CLI allowlist must change;
- verdict: READY FOR PLAN or STOP.

No code changes.
No provider call.

Commit:

Analyze phase 6F provider failure classification

Push only origin/codex-work.
