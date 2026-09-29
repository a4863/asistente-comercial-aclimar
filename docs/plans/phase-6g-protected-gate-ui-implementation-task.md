# Phase 6G Protected Commercial Gate UI Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-29
**Depends on:** docs/plans/phase-6g-protected-gate-ui-plan.md — READY FOR IMPLEMENT

## Objective

Implement the protected localhost operator controls for the existing process-local `CommercialActivationGate`.

This task adds only enable/revoke controls. It does not authorize a commercial OpenAI call.

## Exact Scope Lock

Modify exactly these four tracked files:

1. app/web/routes.py
2. app/web/templates/status.html
3. test/test_status.py
4. test/test_security.py

No fifth tracked file may change.

## Routes

Add exactly:

- POST /commercial-activation/enable
- POST /commercial-activation/disable

Both endpoints:

- accept no parameters;
- require empty body;
- use existing local Host protection;
- require valid signed session;
- require valid CSRF token;
- require same-origin Origin;
- require operational readiness;
- require live exclusive ownership;
- mutate only request.app.state.commercial_gate;
- do not access provider, credential store, analysis service, DB/session factory, repositories or selector;
- return bounded JSON only.

### Enable

On valid request:

- call existing commercial_gate.enable()
- return HTTP 200:
  {"status":"authorized"}

Repeated enable must be safe/idempotent.

### Disable

On valid request:

- call existing commercial_gate.disable()
- return HTTP 200:
  {"status":"blocked"}

Repeated disable must be safe/idempotent.

## Security ordering

For both endpoints:

1. Host protection
2. validate_protected_request(session + CSRF + Origin)
3. _operational_lock() readiness/ownership check
4. verify empty request body
5. mutate gate
6. bounded response

No gate mutation may occur before all checks pass.

Any nonempty request body:

- HTTP 400
- {"status":"invalid_request"}
- do not parse, log, persist or echo body

Security failure:

- preserve existing bounded 403 behavior
- no gate mutation

Unavailable readiness/ownership:

- HTTP 503
- {"status":"unavailable"}
- no gate mutation

Unexpected internal failure:

- HTTP 503
- {"status":"unavailable"}
- no raw exception

## Status page

Preserve existing bounded status and email-analysis controls.

When operational ownership/readiness is valid, issue/reuse the existing CSRF token even if:

- there are no actionable email entries; or
- selector read fails safely.

Render:

When blocked:
- text that Global processing is selected;
- gate resets OFF on restart;
- explicit button: "Enable commercial analysis (Global)"

When authorized:
- explicit button: "Disable commercial analysis"
- text that disabling prevents new attempts/retries but cannot recall an already-sent request.

Do not claim:
- EU residency;
- ZDR;
- persistent authorization;
- cancellation/deletion of already transmitted data.

Gate controls must:

- send bodyless same-origin POST;
- send X-CSRF-Token;
- contain no source_record_id, email content, provider data or arbitrary fields;
- display only bounded result;
- refresh/reload status after action.

## Preserve existing behavior

Do not change:

- app/main.py
- CommercialActivationGate implementation
- session signing
- startup/recovery
- adapter ownership/gate rechecks
- commercial analysis route
- initial/retry semantics
- credential handling
- provider request
- persistence
- diagnostics
- minimization
- decoder/evidence/provenance
- model/endpoint/retries/hooks/close

Authorization remains process-local and OFF on every fresh app/worker.

## Required offline tests

### Enable

- valid Host + Origin + session + CSRF + ownership + readiness + empty body -> authorized
- repeated enable -> authorized
- status reflects authorized
- zero provider calls
- zero credential reads
- zero DB/session/repository/analysis reservation work

### Disable

- valid protected request -> blocked
- repeated disable -> blocked
- status reflects blocked
- zero provider calls
- zero credential reads
- zero persistence/analysis work

### Security failures for both actions

- missing session
- invalid/expired/forged session
- missing CSRF
- invalid CSRF
- bad/missing/malformed Origin
- invalid Host
- not ready
- no lock
- lost ownership
- nonempty body

All must fail before mutation and before provider/credential/persistence work.

### Restart/process-local behavior

Prove in test/test_status.py:

- one app instance can be enabled;
- a fresh app instance starts blocked;
- copied prior-process cookie/session does not authorize the fresh process;
- GET/status/startup does not enable gate.

### UI

Verify:

- blocked state renders enable control only;
- authorized state renders disable control only;
- Global wording present;
- restart-OFF warning present;
- no EU/ZDR claim;
- no secrets/raw email/internal IDs in gate control;
- selector/manual analysis behavior unchanged.

## Validation

Run:

python -m pytest test/test_status.py test/test_security.py test/test_startup.py test/test_activation.py test/test_openai_analysis.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must be exactly the four files listed above.

## STOP conditions

STOP if:

- a fifth tracked file is needed;
- app/main.py or CommercialActivationGate must change;
- session/security primitives must change;
- provider/credential/DB access is required by gate control;
- authorization persistence is needed;
- commercial call is needed for validation.

## Completion

Commit:

Implement phase 6G protected commercial gate UI

Push only origin/codex-work.

Do not execute any commercial OpenAI call.
