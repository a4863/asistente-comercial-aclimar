# Phase 6F Provider Failure Classification Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-provider-failure-classification-analysis.md — READY FOR PLAN

## Objective

Produce an implementation-ready plan that refines generic `provider_failure` into bounded status-only and non-HTTP categories, and exposes those new fixed categories through the existing smoke CLI allowlist.

Do not implement code in this task.
Do not call OpenAI.

## Fixed classification direction

Preserve all existing categories and retry behavior.

Add these bounded categories:

- provider_bad_request      -> verified typed HTTP 400
- provider_not_found        -> verified typed HTTP 404
- provider_conflict         -> verified typed HTTP 409
- provider_unprocessable    -> verified typed HTTP 422
- provider_client_error     -> other verified typed HTTP 4xx excluding existing 401/402/403/429 mappings
- provider_non_http_failure -> remaining non-APIStatusError exceptions in the create-expression/call path after existing timeout/connection handling

Retain:
- provider_failure for malformed/unclassifiable typed status cases that do not safely fit a bucket

## Trusted classification boundary

For status-based mapping:
- require `isinstance(error, openai.APIStatusError)`;
- require `type(status) is int`;
- do not trust arbitrary objects carrying a forged `status_code`;
- do not inspect or emit provider message/body/code/param/request/url/headers;
- do not change retry semantics.

For non-HTTP mapping:
- only after existing typed timeout/connection/auth/quota/5xx branches and status-based typed HTTP mapping;
- do not imply a precise SDK/root cause.

## Expected Scope Lock

Exactly four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

If a fifth tracked file is required, STOP.

## Planning questions to resolve

1. Exact exception-handler ordering.
2. Exact `APIStatusError` type check.
3. Exact integer-status requirement and handling of bool/string/malformed status.
4. Exact mapping for 400/404/409/422.
5. Exact mapping for other typed 4xx.
6. Exact fallthrough to provider_non_http_failure.
7. Exact preservation of:
   - timeout
   - provider_transient_exhausted
   - provider_auth
   - provider_quota
   - existing 5xx behavior
   - provider_failure malformed fallback
8. Exact new CLI allowlist additions.
9. Exact tests for forged status on non-APIStatusError.
10. Exact tests for raw-message/body/URL/control-text non-disclosure.
11. Exact one-attempt/no-retry assertions for all new non-transient categories.
12. Exact Scope Lock and validation commands.
13. Confirm no model/endpoint/schema/payload/timeout/retry/gate/config changes.

## Restrictions

Do not:
- change model;
- change endpoint;
- change Responses API usage;
- change Structured Outputs schema;
- change request payload;
- change timeout/retry policy;
- change credential/keyring handling;
- change commercial gate;
- change routes/UI/persistence;
- add logging/telemetry;
- add dependencies;
- call OpenAI;
- access real keyring/config/SQLite.

Do not expose raw HTTP status in CLI output; expose only the fixed codes above.

## Future implementation validation requirements

At minimum:

python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must contain exactly the four Scope-Locked files.

## STOP conditions

STOP if:
- any fifth file is needed;
- safe classification requires raw provider body/message;
- the pinned SDK does not expose trustworthy APIStatusError behavior as analyzed;
- retry behavior would need to change;
- any model/endpoint/schema/request decision becomes necessary;
- live access is needed to validate the code.

## Deliverable

Create only:

docs/plans/phase-6f-provider-failure-classification-plan.md

Include:
- exact mapping table;
- exact exception ordering;
- exact four-file Scope Lock;
- per-file implementation steps;
- offline test matrix;
- security invariants;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F provider failure classification

Push only origin/codex-work.
