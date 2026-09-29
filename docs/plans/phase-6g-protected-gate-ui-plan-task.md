# Phase 6G Protected Commercial Gate UI Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-29
**Mode:** READ-ONLY / NO COMMERCIAL PROVIDER CALL

## Authority

Depends on:
- docs/plans/phase-6g-commercial-activation-analysis.md — READY FOR DECISION
- docs/plans/phase-6g-commercial-processing-decision.md — Global + protected localhost UI selected

## Objective

Produce an implementation-ready plan for operator-controlled enable/revoke of the existing process-local `CommercialActivationGate` through the protected localhost UI.

The plan must add only the missing operator control. It must not change gate semantics, commercial analysis semantics, provider request behavior, persistence, or data minimization.

## Required source inspection

Inspect at minimum:

- app/main.py
- app/security/activation.py
- app/security/session.py
- app/web/routes.py
- app/web/templates/status.html
- test/test_status.py
- test/test_security.py
- test/test_startup.py if needed to prove restart-OFF behavior
- accepted 6B1, 6B2, 6E1, 6E2, 6E3 and 6G analysis/decision docs

## Required behavior

### Enable action

Add one explicit operator action in the existing localhost UI to enable the current live worker's commercial gate.

Requirements:
- POST only;
- same-process mutation of the existing gate instance;
- existing signed session required;
- valid CSRF required;
- strict loopback Host/Origin required;
- operational readiness required;
- exclusive ownership required;
- bounded result only;
- no request body field may carry commercial content;
- no provider call;
- no credential lookup;
- no analysis reservation;
- no persistence of authorization.

### Disable action

Add one explicit POST action to revoke the same process-local gate.

Requirements:
- same security boundary as enable;
- idempotent;
- no provider call;
- no credential lookup;
- no persistence;
- visible bounded result;
- prevents new commercial attempts/retries according to existing adapter semantics;
- does not claim cancellation or deletion of an already-sent request.

### UI/status

The status page must:
- show the current bounded gate state;
- render explicit enable/disable controls appropriate to the current state;
- never display secrets, IDs, raw errors or commercial content;
- never imply that Global processing is EU-resident/ZDR;
- make clear that authorization resets OFF on restart.

Do not add a persistent consent flag. The user's Global decision is project documentation, not runtime gate persistence.

## Preserve existing security

Do not modify semantics of:
- CommercialActivationGate;
- adapter gate rechecks;
- operational lock;
- startup recovery;
- session signing;
- CSRF;
- Origin/Host validation;
- manual analysis route;
- retry semantics;
- credential handling;
- provider request;
- diagnostics;
- minimization;
- decoder/evidence/provenance.

The activation POST itself must not call OpenAI.

## Candidate Scope Lock

Determine whether implementation can remain within exactly:

1. `app/web/routes.py`
2. `app/web/templates/status.html`
3. `test/test_status.py`
4. `test/test_security.py`

Only if strictly necessary to prove restart-OFF behavior may the plan request:

5. `test/test_startup.py`

No production fifth file is authorized.

If production changes outside routes/template are required, verdict must be STOP and explain why.

## Required offline test matrix

At minimum cover:

### Enable
- valid local session + CSRF + Origin + Host + ownership + readiness -> gate enabled;
- provider not called;
- credential store not read;
- no analysis run reserved;
- repeated enable is bounded/idempotent or otherwise safely defined;
- status reflects authorized.

### Disable
- valid protected request -> gate disabled;
- repeated disable safe;
- status reflects blocked;
- no provider/credential/analysis mutation;
- adapter remains responsible for preventing new attempts/retries.

### Security failures
For both enable and disable:
- missing session;
- invalid session;
- missing CSRF;
- invalid CSRF;
- bad Origin;
- bad Host;
- not ready;
- ownership missing/lost.

All fail before gate mutation and before any credential/provider/analysis work.

### Restart
- fresh `create_app()` / fresh operational process has gate OFF regardless of prior process state;
- no cookie/session or prior UI action can persist authorization across restart.

### UI
- blocked state offers enable;
- authorized state offers disable;
- state text is bounded;
- no secret/raw commercial data;
- no EU/ZDR claim.

## First-commercial-call boundary

The plan must explicitly state that implementation acceptance does NOT authorize a commercial call.

After implementation acceptance, a separate one-shot rollout authorization will be required for exactly one operator-selected eligible email using the existing protected analysis route.

## Deliverable

Create only:

`docs/plans/phase-6g-protected-gate-ui-plan.md`

Include:
- route/action design;
- exact security ordering;
- dependency injection/current gate access;
- idempotency behavior;
- exact Scope Lock;
- per-file changes;
- offline acceptance matrix;
- restart-OFF proof;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

No code changes.
No live provider call.
No commercial data transmission.

Commit:

Plan phase 6G protected commercial gate UI

Push only origin/codex-work.
