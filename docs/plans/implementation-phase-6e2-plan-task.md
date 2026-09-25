# Phase 6E2 Planning Task — Protected Manual Analysis UI and Retry Contract

**Status:** READY FOR PLAN
**Date:** 2026-09-25
**Depends on:** Phase 6E1 ACCEPTED; D16 and D17 APPROVED
**Analysis:** docs/plans/phase-6e2-trigger-analysis.md
**Decisions:** D1, D2, D6, D8, D9, D12, D13, D16, D17

## Objective

Produce an implementation-ready plan for a protected local browser workflow that:

1. lists a bounded set of existing eligible emails using safe metadata;
2. lets the user explicitly analyze one selected email;
3. requires a distinct explicit retry action after a retryable outcome;
4. reuses existing analysis orchestration and authorization boundaries;
5. introduces no migrations, new dependency, gate-activation UI, scheduler or force reanalysis.

This task is READ-ONLY planning.

## Decisions already fixed

### Target selection — D16

- Browser selector/list of existing eligible emails.
- No manual entry of account/source internal IDs.
- Safe metadata only.
- Explicit repository/service read contract.
- No ad-hoc SQL in route.
- Repository + repository-test scope expansion is allowed if needed.

### Retry semantics — D17

- Initial Analyze is non-force manual analysis.
- A retryable prior outcome must not be retried by a repeated normal Analyze POST.
- A distinct explicit Retry analysis POST/action is required.
- Retry may create a new run/version but remains non-force.
- completed replay and in-progress remain no-new-provider outcomes.
- No persistent request identity/migration.

## Planning questions to resolve exactly

Inspect current repository/service/model contracts and specify:

1. Exact repository method for listing selectable emails:
   - eligibility rules;
   - account scope behavior;
   - ordering;
   - result limit;
   - safe metadata fields;
   - analysis-state derivation.
2. Exact repository/service method needed to determine whether initial Analyze or Retry is allowed for a selected target.
3. Whether retry-policy enforcement belongs in the route, service, or repository; prefer a server-side domain/service boundary rather than UI-only checks.
4. Exact route paths and HTTP methods for:
   - list/status page;
   - initial Analyze POST;
   - Retry POST.
5. Exact JSON/request body fields and CSRF transport.
6. Exact response model/status mapping for:
   - accepted/completed;
   - completed_replay;
   - in_progress;
   - retry_required;
   - blocked gate;
   - disabled;
   - unavailable ownership/readiness;
   - missing credential;
   - provider failure;
   - stale/invalid target.
7. How POST/redirect/GET or JSON update avoids browser refresh causing unintended provider calls.
8. Exact way GET obtains and renders CSRF token without putting it in URL/log/provider payload.
9. Exact readiness/ownership/gate preflight ordering before DB reservation/credential lookup/provider use.
10. Exact composition of `OpenAIAnalysis` with:
    - app credential store;
    - operational lock;
    - commercial gate.
11. Exact way account scope is derived for each listed target so the browser does not invent it.
12. Exact behavior if the listed target becomes deleted/redacted/unresolved between GET and POST.
13. Exact bounded list size and deterministic ordering.
14. Whether template JavaScript is required. Prefer ordinary HTML forms if current dependencies can parse safely; if form parsing requires unavailable dependency, choose a no-new-dependency request mechanism and state why.
15. Exact production/test Scope Lock.
16. Full offline test matrix, including duplicate/retry race cases.

## Required security invariants

- No GET causes analysis.
- No cross-origin or invalid-CSRF POST causes DB/credential/provider access.
- Gate OFF stops before credential/provider call and must not create a retryable analysis run merely because provider authorization is absent.
- Operational readiness + live ownership required.
- Browser cannot supply provider/model/base URL/credential reference/message body.
- Browser-supplied internal source id, if present in a form, must be revalidated against server-side eligibility/account scope.
- Initial Analyze cannot act as Retry when latest outcome is retryable.
- Retry cannot act on a target that is not currently in retryable state.
- No force mode.
- No raw provider errors, source bodies, digests, API key or lock handles in UI.
- Existing adapter remains final authorization authority against races.
- No real OpenAI call in implementation tests.

## Scope expectations

The final plan may include, if justified by current code:
- app/persistence/repositories.py
- app/services/email_analysis.py
- app/web/routes.py
- app/web/templates/status.html
- app/main.py only if composition strictly requires it
- matching focused tests

Do not include models/migrations/config/dependencies unless analysis proves unavoidable; if any are required, STOP instead.

## STOP conditions

STOP if:
- a migration/model change is required;
- safe selector cannot be implemented through current persistence model;
- retry distinction cannot be enforced without persistent request identity;
- form/request parsing requires a new dependency and no safe existing JSON/native alternative fits;
- another unresolved functional decision appears.

## Deliverable

Create only:

`docs/plans/implementation-phase-6e2-plan.md`

The plan must include:
- exact UX flow;
- exact repository/service contracts;
- exact routes and request/response semantics;
- exact preflight ordering;
- exact Scope Lock;
- per-file changes;
- ordered implementation steps;
- test matrix;
- rollback/fail-closed behavior;
- STOP findings;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6E2 protected manual analysis workflow

Push only origin/codex-work.
