# Phase 6G — Protected commercial gate UI plan

**Date:** 2026-09-29

**Status:** READY FOR IMPLEMENT — planning only

## Authority and objective

The approved [6G processing decision](phase-6g-commercial-processing-decision.md) selects Global processing and a protected localhost UI control. It permits this plan and a separately approved offline implementation, **not** a real commercial OpenAI call. The process-local gate remains OFF. This plan adds only an explicit enable/revoke control to the existing web worker; it neither changes the commercial-analysis POST nor persists consent.

Sources inspected: the 6G task, analysis and approved decision; accepted 6B1, 6B2, 6E1, 6E2 and 6E3 records; `app/main.py`, `app/security/activation.py`, `app/security/session.py`, `app/web/routes.py`, `app/web/templates/status.html`, and relevant status, security and startup tests. Current `create_app()` constructs a fresh OFF gate and a fresh signed-session secret. `_operational_lock()` already requires both readiness and live exclusive ownership. `validate_protected_request()` already validates local Host, same-origin Origin and a CSRF token bound to the signed session. The manual-analysis route already has its own gate/ownership checks.

## Exact route and action contract

Add two fixed, parameter-free endpoints in `app/web/routes.py`:

| Method/path | Successful operation | Bounded response |
| --- | --- | --- |
| `POST /commercial-activation/enable` | Call `request.app.state.commercial_gate.enable()` on the existing live worker. | HTTP 200, `{"status":"authorized"}`. |
| `POST /commercial-activation/disable` | Call `request.app.state.commercial_gate.disable()` on that same instance. | HTTP 200, `{"status":"blocked"}`. |

Both operations are idempotent: repeating enable leaves the gate ON; repeating disable leaves it OFF. They do not accept source IDs, mode, credentials, project IDs, arbitrary JSON or commercial text. Require an empty request body: reject any nonempty streamed content with HTTP 400 and `{"status":"invalid_request"}` without retaining or reflecting it. Do not use a GET, query parameter, form action, startup flag or environment variable to mutate the gate. Responses use the existing `Cache-Control: no-store` and `Referrer-Policy: no-referrer` headers; unexpected internal failure maps to a fixed `{"status":"unavailable"}`/503, never an exception string.

For **each** POST, perform checks in this order:

1. Router-level `require_local_host` rejects invalid Host; then call `validate_protected_request(request, request.headers.get("x-csrf-token"))`. The latter requires a valid signed-session-bound CSRF value and matching local Origin. Missing/expired/forged session, missing/wrong token or bad Origin yields fixed `invalid_security`/403. No gate read or mutation precedes this check.
2. Call the existing `_operational_lock(request.app)`. It must return a live owner with `operational_ready is True`; otherwise return `unavailable`/503 without gate mutation. Do not alter the lock, startup recovery or readiness contract.
3. Confirm the request body is empty, with bounded streaming/early rejection. A nonempty body returns `invalid_request`/400. Neither action parses, logs, persists or echoes submitted content.
4. Mutate only `request.app.state.commercial_gate` via its existing `enable()` or `disable()`, then return the fixed bounded state. Do not construct `OpenAIAnalysis`, query credential presence/secret, open a database session, reserve an `AnalysisRun`, or call any provider. A concurrent loss of ownership after the route check cannot authorize a provider attempt because the adapter still independently rechecks ownership and the gate before each attempt/retry.

The route is not a processing-mode selector. The Global decision is an approved document, not a request parameter or a persisted flag. The UI must not imply Global is EU-resident or zero-data-retention. Authorization is process-local and is lost on every new `create_app()`/worker process.

## Status page and session-token contract

The status page continues to show only the bounded gate state `blocked` or `authorized`. When `_operational_lock()` succeeds, issue/reuse the existing `issue_csrf_token(request.session)` **regardless of whether the email selector has actionable entries or its read fails**. The current code issues that token only when an email is `ready`/`retry_required`, which would otherwise make activation/revocation unavailable with an empty selector. This creates/reuses a signed session cookie; it is not authorization persistence. Inactive/unowned status must not offer a gate action.

Render one explicit button appropriate to current state: `Enable commercial analysis (Global)` when blocked, or `Disable commercial analysis` when authorized. The accompanying text states that Global processing is selected, the gate resets OFF on restart, disable prevents new attempts/retries, and it cannot recall an already-sent request. Do not claim EU residency or ZDR. The button must require an intentional click and send only a bodyless same-origin POST with `X-CSRF-Token`; no email/provider content can choose the path or trigger it. Keep the analysis buttons and their initial/retry semantics unchanged. On success, show/reload the server-reported bounded state and swap the available control; on failure, show only the fixed safe code and refresh status before another action. Do not render the session secret, credential value, request/response body, internal source IDs, raw error or a persistent-consent claim.

The page's current credential-presence display and bounded email selector remain separate **GET status** behavior. The existing selector carries an internal `source_record_id` in the protected analysis action payload; the gate controls must neither use nor add such an identifier, and no ID is to be shown as gate-control text. Neither activation POST may call the status credential logic or read keyring. The CSRF token itself may be delivered to same-origin page script as it already is for manual analysis, but must not be logged or exposed in URL/third-party navigation.

## Exact Scope Lock and per-file work

Only these four files may be changed in the future implementation task:

| File | Planned change |
| --- | --- |
| `app/web/routes.py` | Add the two fixed POSTs and one shared private protected-gate handler; reuse existing Host/session/CSRF/Origin and `_operational_lock`; issue the current CSRF token for an owned ready status even without actionable email options; pass only bounded gate-action state to the template. |
| `app/web/templates/status.html` | Display Global/reset/revocation caveats and one state-appropriate enable/disable button; submit bodyless same-origin POST using the existing session token; show bounded result and refresh current state. Preserve existing analysis controls. |
| `test/test_status.py` | Offline route/UI tests for authorized/blocked/empty-selector states, idempotency, no provider/credential/DB work by POST, restart OFF and bounded feedback. |
| `test/test_security.py` | Adversarial POST tests for both actions: session/cookie, CSRF, Origin, Host, ownership/readiness and untrusted body rejection; zero gate mutation or external/persistence work on failure. |

`test/test_startup.py` is **not** required: existing startup tests already prove fresh app composition and lock lifecycle, while `test/test_status.py` can prove that a new app/worker gate is OFF despite an earlier enabled app and copied cookie. No fifth file, especially no fifth production file, is included. No change to `app/main.py`, `app/security/activation.py`, `app/security/session.py`, adapter, service, repositories, models, config, credentials, migration or dependency is planned. If the four-file contract cannot be met, STOP and request a new scope decision rather than expanding it.

## Offline acceptance matrix

Use isolated `TestClient`/fake lock and synthetic session data; never use operational SQLite, real keyring or OpenAI. The implementation task should run at least `python -m pytest test/test_status.py test/test_security.py test/test_startup.py test/test_activation.py test/test_openai_analysis.py`, then `python -m pytest`, followed by `git diff --name-only` and `git diff --check`.

| Case | Required observation |
| --- | --- |
| Valid enable | Signed local session, correct CSRF, Host/Origin, ready live owner and empty body produce `authorized`; status shows ON and disable control. No provider, credential read, session factory or reservation. |
| Repeated enable | Same fixed successful state; no additional side effect or analysis call. |
| Valid/repeated disable | Fixed `blocked`; status shows OFF and enable control; no provider, credential read, DB work or claim of cancelling an in-flight call. |
| Missing/forged/expired session; missing/wrong CSRF | Both POSTs fail closed before mutation or other work; copied prior-worker cookie is invalid for a fresh process. |
| Missing/foreign/null/malformed Origin or invalid Host | Both POSTs fail closed before mutation; Host may be rejected by router dependency with its existing bounded response. |
| Not ready, no lock, lost owner | Both POSTs return `unavailable` and leave gate unchanged. Adapter continues to fail closed if ownership is lost after a successful enable. |
| Any nonempty body, including commercial text or mode field | Both POSTs return `invalid_request`, do not parse/echo input, and do not mutate the gate. |
| No eligible email or selector failure | Ready owned status still creates a usable protected gate token/control; gate POST does not query selector or database. |
| Restart/new app | New gate is OFF; old session/cookie cannot activate it. No startup/GET/provider side effect turns it ON. |
| UI/security regression | Only the appropriate gate control appears; it introduces no secret, raw content or ID; no EU/ZDR claim; the existing bounded email selector and manual POST retain their protections, gate and explicit initial/retry intent. |

Tests must use fakes to assert no call to `OpenAIAnalysis`, credential methods or persistence factory from gate POSTs. A request whose gate is disabled during a retry delay remains governed by the existing adapter tests; do not modify retry mechanics.

## Rollback and later commercial-call boundary

The operator's immediate rollback is the protected disable POST and confirmation that status reports `blocked`. If the worker loses ownership/readiness and that POST cannot be completed, stop the operational worker after any in-flight provider work has settled, then restart: the fresh gate is OFF. Restart does not retract already transmitted data. A persistent or failed gate-control response, bypass of any protection, provider/credential/DB call from the control, inability to revoke, or any need for an extra production file is a STOP before rollout.

Acceptance of this UI implementation **will not authorize a commercial call**. A separately approved one-shot rollout must perform the operational preflight and select exactly one existing eligible email through the protected manual analysis route. No live call, smoke, commercial transmission, scheduler, or background analysis is part of this plan or its offline validation.

## Result

**READY FOR IMPLEMENT.** The approved Global and protected-localhost-UI decisions remove the prior choice ambiguity. The four-file Scope Lock is sufficient to add an operator control without changing existing gate, session, provider, persistence or manual-analysis semantics.
