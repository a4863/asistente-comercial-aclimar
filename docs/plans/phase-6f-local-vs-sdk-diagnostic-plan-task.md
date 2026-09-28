# Phase 6F Local Construction vs SDK Call Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-non-http-failure-analysis.md — READY FOR PLAN

## Objective

Plan the smallest bounded diagnostic change that separates:
1. local schema/request-argument construction failure;
2. non-HTTP exception raised by `responses.create()`.

Do not implement code.
Do not call OpenAI.

## Evidence boundary

Use only the reproducible local findings from the accepted analysis:
- installed SDK version is `openai==3.17.0`;
- `response_schema()` succeeds and is JSON-serializable;
- exact synthetic kwargs transform/serialize successfully;
- exact request passes through the pinned SDK with synthetic key and explicit no-network mock transport.

Do not rely on public-web documentation for design decisions in this task.

## Fixed direction

Introduce exactly one new bounded code:

`request_schema_failure`

Meaning:
- an unexpected exception occurred while evaluating/building the local response schema or request-format object before invoking `client.responses.create()`.

Keep:
- `provider_non_http_failure` for remaining non-HTTP exceptions raised from the SDK call path.

Do not claim pre-dispatch/post-dispatch distinction inside `responses.create()`.

## Expected Scope Lock

Exactly four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

If a fifth tracked file is required, STOP.

## Planning questions

1. Exact code extraction point for `response_schema()` and local `text` object construction.
2. Exact bounded try/except that maps only local construction exceptions to `request_schema_failure`.
3. How to guarantee `client.responses.create()` is not entered on local construction failure.
4. How to preserve all existing timeout/auth/quota/HTTP/retry classifications.
5. How to ensure `provider_non_http_failure` remains limited to non-HTTP exceptions from the SDK call path.
6. Exact CLI allowlist addition for `request_schema_failure`.
7. Exact no-leak tests.
8. Exact no-network SDK mock test using synthetic key/transport.
9. Exact regression tests proving request kwargs are unchanged.
10. Exact Scope Lock and validation commands.

## Restrictions

Do not:
- change model;
- change endpoint;
- change Responses API usage;
- change Structured Outputs schema semantics;
- change payload;
- change max_output_tokens;
- change timeout/retry behavior;
- change SDK version/dependencies;
- change keyring/credentials;
- change commercial gate;
- change routes/UI/persistence;
- add logging/telemetry;
- call OpenAI;
- access real keyring/config/SQLite.

## Validation requirements for future implementation

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
- a fifth file is required;
- raw exception/provider content would be needed;
- design requires distinguishing pre-dispatch from post-dispatch inside the SDK call;
- retry/model/endpoint/schema semantics must change;
- live access is needed to validate.

## Deliverable

Create only:

`docs/plans/phase-6f-local-vs-sdk-diagnostic-plan.md`

Include:
- exact phase boundary;
- exact new code semantics;
- exact four-file Scope Lock;
- per-file steps;
- offline/no-network tests;
- security invariants;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F local vs SDK diagnostics

Push only origin/codex-work.
