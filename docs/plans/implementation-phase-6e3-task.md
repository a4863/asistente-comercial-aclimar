# Phase 6E3 Implementation Task — Security Regression and Rollback Validation

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6E2 ACCEPTED
**Plan:** docs/plans/implementation-phase-6-plan.md

## Objective

Perform the final offline adversarial regression for Phase 6 web/manual-analysis activation and close any security gaps found within a tightly bounded Scope Lock.

This phase must not add new product behavior. It validates and hardens:
- fail-closed request protection;
- no unintended provider disclosure;
- no duplicate retry path;
- rollback/recovery behavior;
- no secret/source leakage;
- no gate bypass;
- no inert-instance execution.

No live OpenAI call is authorized.

## Exact Scope Lock

Modify only if required:

1. test/test_security.py
2. test/test_status.py
3. test/test_email_analysis_service.py
4. test/test_persistence_repositories.py
5. app/web/routes.py
6. app/services/email_analysis.py
7. app/persistence/repositories.py

No other tracked file may change.

If no production fix is needed, production files should remain unchanged.

## Required adversarial coverage

Add focused tests proving at minimum:

### Request/security boundary

1. GET never reserves or calls AI.
2. POST with:
   - missing session/CSRF;
   - invalid/tampered session cookie;
   - wrong CSRF;
   - foreign Origin;
   - null Origin;
   - scheme mismatch;
   - port mismatch;
   - malformed Host;
   - misleading Host suffix/userinfo;
   fails before DB analysis access, credential probe or provider call.
3. No Referer fallback authorizes a protected action.
4. CSRF token from one app/session cannot authorize another.
5. stale/expired session cookie cannot authorize action.
6. request bodies with duplicate keys, nested objects, booleans, negative/zero IDs, huge integers, unknown keys, invalid UTF-8, oversize body, wrong content-type fail bounded.
7. browser cannot inject account scope, provider/model/base URL, credential ref, request_mode or force.

### Operational/gate boundary

8. inert create_app cannot analyze.
9. not-ready operational app cannot analyze.
10. lost lock ownership before route call prevents reservation/provider.
11. gate OFF prevents reservation, secret lookup and provider call.
12. gate revoked after route preflight but before adapter attempt is still caught by adapter and results bounded.
13. AI disabled prevents reservation/provider.
14. missing/unavailable credential prevents reservation/provider.
15. no route can enable/disable gate.

### Target/retention boundary

16. unknown, wrong-account, deleted/redacted, unresolved or superseded target never reaches provider.
17. target becomes stale between selector and POST -> invalid_target/no provider.
18. target changes after reservation/provider -> stale_retryable with no unsafe derived writes.
19. selector omits ineligible target and never exposes body/snippet/digest/internal IDs beyond action value.
20. safe metadata truncation/control-character normalization remains bounded and HTML-escaped.

### Replay/retry/concurrency

21. duplicate initial after failed_retryable -> retry_required, no second provider call.
22. retry without matching retryable -> retry_not_available.
23. completed replay -> no provider.
24. in-progress -> no provider.
25. concurrent initial requests cannot produce two provider calls.
26. concurrent retry requests cannot produce two provider calls.
27. changed input after retryable permits new initial and does not incorrectly require retry.
28. repeated retry action after a retry itself fails retryably requires another explicit retry action; no automatic loop.
29. automatic/force legacy semantics remain unchanged outside web path.

### Leakage and rollback

30. raw provider error, API key, request body, response body, source body, digest, run id, account scope, lock handle/path do not appear in HTTP response or logs.
31. failure after reservation persists only approved bounded retryable state.
32. failure before reservation leaves no AnalysisRun.
33. persistence failure/rollback cannot leave partial derived rows.
34. no ApprovalDecision/ExecutionResult/external action authority is created by analysis.
35. no real network, keyring backend, IMAP, CRM, Calendar or external mutation occurs in tests.

## Production fixes

If a test exposes a real gap:
- apply the smallest fix only in the three approved production files;
- preserve existing public contracts;
- no new route, migration, dependency, config or UI feature;
- do not broaden statuses or authorization semantics.

If fixing requires another production file or design change, STOP.

## Restrictions

Do not modify:
- app/main.py
- app/security/session.py
- OpenAI adapter
- activation.py
- credentials
- templates
- models/migrations
- config
- pyproject
- docs

Do not:
- call OpenAI live;
- enable commercial authorization by default;
- add any gate control;
- add scheduler/background work;
- add dependency;
- add migration;
- add new user-facing feature.

## Validation

Run:

python -m pytest test/test_security.py test/test_status.py test/test_email_analysis_service.py test/test_persistence_repositories.py test/test_startup.py test/test_openai_analysis.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must be a subset of the seven Scope-Locked files.

## STOP conditions

STOP if:
- a fix needs app/main.py, session.py, adapter, template, config, model/migration or dependency changes;
- a new functional decision is required;
- safe concurrency cannot be maintained under current schema;
- live provider access appears necessary.

## Completion

Commit:

Harden phase 6E3 manual analysis security regressions

Push only origin/codex-work.
