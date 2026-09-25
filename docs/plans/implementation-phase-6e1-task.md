# Phase 6E1 Implementation Task — Local Session, CSRF and Origin/Host Protection

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6D ACCEPTED
**Plan:** docs/plans/implementation-phase-6-plan.md
**Decision:** D9

## Objective

Establish the local web security boundary required before any state-changing commercial POST is added.

Implement local session integrity, CSRF validation, and localhost Host/Origin enforcement. This task does **not** add the manual analysis trigger.

## Exact Scope Lock

Modify only:

1. app/security/session.py
2. app/main.py
3. app/web/routes.py
4. test/test_security.py
5. test/test_startup.py
6. test/test_status.py

No other tracked file may change.

## Required behavior

### Session boundary

Use the existing session helpers where possible.

The operational/local web app must have a cryptographically unpredictable process-local session secret generated at runtime.

Requirements:
- not hardcoded;
- not persisted;
- not read from env/TOML/keyring for this phase;
- new process/startup gets a new secret;
- secret never appears in routes, HTML, logs, repr or status;
- inert import must not perform external IO.

Use existing FastAPI/Starlette capabilities already available; add no dependency.

### CSRF

Provide a reusable request validation path for future state-changing POSTs.

Requirements:
- CSRF token bound to the local session;
- token generated/reused per session;
- constant-time comparison where applicable;
- missing/invalid token fails closed;
- validation API is reusable by 6E2;
- GET/status/health remain non-mutating and do not require CSRF;
- do not add any commercial POST in this task.

### Host validation

Reject requests whose Host is not an approved loopback form.

Allowed target is the local application only.

Support the configured loopback host/port and practical localhost forms needed by TestClient/local browser without broad wildcard trust.

Do not trust arbitrary Host merely because the TCP listener is loopback.

### Origin validation

For future state-changing requests, reusable validation must require a same-origin local Origin when Origin is present/required by the chosen POST policy.

Reject:
- foreign origins;
- malformed origins;
- scheme/host/port mismatch;
- opaque/null origin unless explicitly and safely justified.

Do not use Referer as a permissive substitute.

The exact helper/middleware design should be the smallest that 6E2 can call reliably.

### Middleware/composition

Wire session/host protection in `app/main.py` without:
- touching OpenAI;
- enabling commercial gate;
- reading credentials;
- changing startup recovery order;
- weakening single-instance ownership.

Inert `create_app()` must remain usable in tests.

### Current routes

Preserve:
- `GET /health`
- `GET /` status

No new state-changing endpoint in 6E1.

Status page must not reveal session secret or CSRF internals.

## Tests

Prove at minimum:

1. app/session secret is not a hardcoded constant reused across separately created app instances/process-local compositions;
2. session cookie is local HTTP-session state and does not contain the raw secret;
3. CSRF token is stable/reused within one session as currently designed;
4. missing/invalid CSRF validation fails;
5. valid CSRF passes;
6. comparison does not use naive direct equality if existing helper can be hardened;
7. approved loopback Host reaches GET routes;
8. arbitrary/foreign Host is rejected;
9. Host with misleading suffix/userinfo/malformed port is rejected;
10. same-origin local Origin validation passes;
11. foreign/malformed/null Origin validation fails for protected-action helper;
12. origin scheme/port mismatch fails;
13. /health remains provider/keyring-free;
14. status remains readable and does not leak session secret/token;
15. import/create_app performs no network/provider/keyring IO;
16. operational startup lock/recovery tests remain green;
17. no commercial POST route exists after this task.

## Restrictions

Do not modify:
- OpenAI adapter/smoke
- activation gate
- credentials
- persistence/models/repositories/migrations
- config schema/defaults
- pyproject
- templates unless absolutely required (if required, STOP because outside Scope Lock)
- docs

Do not:
- add the manual analysis POST;
- enable commercial authorization;
- call OpenAI;
- add authentication/multi-user functionality;
- add dependency;
- persist session secrets/tokens.

## Validation

Run:

python -m pytest test/test_security.py test/test_startup.py test/test_status.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/security/session.py
- app/main.py
- app/web/routes.py
- test/test_security.py
- test/test_startup.py
- test/test_status.py

## STOP conditions

STOP if:
- secure session composition requires a new dependency;
- a template change is required;
- another production/test file is required;
- Host/Origin policy cannot be expressed unambiguously from current configured loopback host/port;
- startup/recovery ordering would need broader changes.

## Completion

Commit:

Implement phase 6E1 local web request protection

Push only origin/codex-work.
