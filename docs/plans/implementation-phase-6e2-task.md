# Phase 6E2 Implementation Task — Protected Manual Email Analysis Workflow

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6E1 ACCEPTED; D16/D17 APPROVED
**Plan:** docs/plans/implementation-phase-6e2-plan.md

## Objective

Implement the approved local browser workflow for selecting an existing eligible email, manually analyzing it, and explicitly retrying only after a retryable outcome.

No live provider call is authorized during tests.

## Exact Scope Lock

Modify exactly these seven files:

1. app/persistence/repositories.py
2. app/services/email_analysis.py
3. app/web/routes.py
4. app/web/templates/status.html
5. test/test_persistence_repositories.py
6. test/test_email_analysis_service.py
7. test/test_status.py

No other tracked file may change.

## Required behavior

Implement the plan exactly.

### Selector

- GET / remains read-only.
- When operational_ready and current lock ownership are valid, display at most 20 eligible emails for server-configured IMAP account scope.
- Safe metadata only:
  - sender max 120 chars;
  - subject max 160 chars;
  - bounded timestamp;
  - state: ready/completed/in_progress/retry_required.
- Never render body, snippet, digest, run id, account scope, failure code, credential or provider data.
- Source id may be used only as protected action value; user does not type internal identifiers.

### Repository/service contracts

Implement the plan's bounded selector DTO/query, latest-run lookup and server-side current-input state derivation.

Implement atomic manual intent semantics:
- initial
- retry

Rules:
- matching reserved -> in_progress, no provider;
- matching completed -> completed_replay, no provider;
- matching current retryable latest + initial -> retry_required, no insert/provider;
- matching current retryable latest + retry -> may reserve next manual version;
- retry without matching current retryable state -> retry_not_available;
- changed current input means older retryable run does not force retry;
- no force mode;
- existing automatic/force/non-manual callers remain unchanged.

Retry distinction must be enforced server-side in repository/service logic, not only UI.

### POST routes

Add exactly:
- POST /analysis/email
- POST /analysis/email/retry

Body:
- application/json only;
- max 256 bytes;
- exact shape {"source_record_id": <positive integer>};
- reject bool, non-int, non-positive, unknown keys and malformed JSON.

Browser must not supply:
- account scope;
- request mode;
- force flag;
- provider/model/base URL;
- credential reference;
- message body;
- arbitrary payload.

Account scope comes only from server settings.

### Security/preflight order

Before analysis DB reservation/provider access:

1. existing Host protection + validate_protected_request using X-CSRF-Token;
2. operational_ready == True;
3. live operational_lock.is_owner == True;
4. commercial gate ON;
5. technical AI enabled;
6. bounded credential presence probe;
7. parse/revalidate target and invoke existing service.

Gate OFF must produce zero reservation, credential secret lookup and provider call.

Construct OpenAIAnalysis only with current:
- settings.ai;
- app credential store;
- app operational lock;
- app commercial gate.

Adapter remains final authorization authority.

### CSRF/UI

- GET / issues/reuses session CSRF token only when needed for actions.
- Token never in URL/log/provider request.
- Same-origin JS sends JSON + X-CSRF-Token with credentials=same-origin.
- No automatic retry on network failure.
- Refresh remains GET and never repeats provider action.
- ready -> Analyze button.
- retry_required -> Retry analysis button.
- completed/in_progress -> no action.
- No gate activation control.

Add:
- Cache-Control: no-store
- Referrer-Policy: no-referrer

### Bounded responses

Use only whitelisted JSON status responses per the approved plan:
- completed
- completed_replay
- in_progress
- retry_required
- retry_not_available
- blocked
- invalid_request
- invalid_target
- unavailable
- disabled
- credential_missing
- credential_unavailable
- no_analyzable_body
- failed_retryable
- stale_retryable
- invalid_security

Do not expose raw failure_code, source text, provider response, digest, run id, account scope, API key or lock details.

### Concurrency/fail closed

- Competing reservations must not cause duplicate provider attempts.
- Losing conflict returns bounded no-provider outcome as defined in the plan.
- DB/service errors fail closed.
- Target eligibility is revalidated at POST time.
- Existing provider-outside-transaction behavior and current analysis persistence semantics remain intact.

## Tests

Implement the full plan matrix, including:

- selector eligibility/scope/order/limit/no-body exposure;
- current-input state derivation;
- initial/retry matrix;
- completed/in-progress precedence;
- changed-input retry behavior;
- concurrent/competing retry behavior;
- rollback;
- existing automatic/force regressions;
- GET never analyzes;
- valid protected initial POST;
- valid protected retry POST;
- invalid/missing CSRF;
- foreign/malformed Origin/Host;
- malformed/oversize JSON;
- stale/deleted/redacted/wrong-account target;
- inert/not-ready/no-owner;
- gate OFF;
- AI disabled;
- credential missing/unavailable;
- completed_replay/in_progress/retry_required/retry_not_available;
- failed_retryable/stale_retryable;
- no raw data/secrets in UI/JSON/logs;
- no real provider/network.

Use fake provider/credential/lock only.

## Restrictions

Do not modify:
- app/main.py
- app/security/session.py
- app/integrations/openai_analysis.py
- activation gate
- credentials implementation
- models/migrations
- config
- pyproject
- docs
- any other file

Do not:
- add dependency;
- add migration/model field;
- enable commercial gate;
- expose force reanalysis;
- add scheduler/background analysis;
- use direct SQL in route;
- call OpenAI live;
- perform external mutations.

## Validation

Run:

python -m pytest test/test_persistence_repositories.py test/test_email_analysis_service.py test/test_status.py test/test_security.py test/test_startup.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly the seven Scope-Locked files.

## STOP conditions

STOP if:
- any other production/test file is required;
- migration/model/config/dependency change becomes necessary;
- retry semantics cannot be enforced atomically within current repository/service boundary;
- request parsing needs a new dependency;
- app/main.py or security/session.py must change;
- live provider access appears necessary.

## Completion

Commit:

Implement phase 6E2 protected manual analysis workflow

Push only origin/codex-work.
