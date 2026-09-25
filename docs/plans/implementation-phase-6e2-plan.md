# Phase 6E2 implementation plan — Protected manual email analysis

**Status: READY FOR IMPLEMENT**
**Authority:** `implementation-phase-6e2-plan-task.md`; approved D1, D2, D6, D8, D9, D12, D13, D16, D17 in `phase-6-activation-decisions.md`; `phase-6e2-trigger-analysis.md`. Implementation still requires its own approved task and Scope Lock.

## 1. Objective and current boundary

Add a local, explicit browser action for one retained email, with a separate explicit retry action. The existing `GET /` is status-only; there is no selector or commercial POST. 6E1 already provides a signed local session, `issue_csrf_token`, `validate_protected_request`, and a Host dependency. The operational lifespan alone holds `SingleInstanceLock` and completes reserved-run recovery before readiness. `OpenAIAnalysis.analyze()` is the final ownership/gate check, including retries. `analyze_email_in_thread` already owns canonical input selection, reservation, provider isolation, revalidation, result persistence, completed replay, and in-progress handling. No browser-supplied email body or provider setting is needed.

## 2. Exact UI and request flow

1. `GET /` remains the sole status/list page. It never invokes the provider or reserves a run. When and only when `operational_ready is True` and the current lock reports `is_owner is True`, it reads a fixed maximum of **20** eligible emails for the configured `settings.imap.account_scope`. Gate OFF does not hide local records. An inert/not-ready app shows no actionable selector.
2. Each row shows only sender (maximum 120 characters), subject (maximum 160 characters), message timestamp (UTC ISO-8601 or a neutral unknown marker), and one bounded current-input analysis state: `ready`, `completed`, `in_progress`, or `retry_required`. Empty sender/subject become neutral labels. Control characters are replaced with spaces and Jinja autoescaping remains on. No body, snippet, account scope, digest, run ID, raw failure code, or provider data is rendered. The source ID is present only as an action value, not as an operator-editable field.
3. `ready` shows **Analyze**; `retry_required` shows **Retry analysis**; `completed` and `in_progress` show no action. The server revalidates every action, so stale browser state grants nothing. No force button or gate-ON control appears.
4. The page issues/reuses `issue_csrf_token(request.session)` only for the action UI. Put the token in a hidden DOM value readable by the same-origin page script; never in a URL, diagnostic/status field, log, provider input, or external request. The session cookie stays HttpOnly, SameSite=Strict, host-only. Add `Cache-Control: no-store` and `Referrer-Policy: no-referrer` to this page and action responses.
5. A small same-origin script sends `fetch` with `Content-Type: application/json`, `X-CSRF-Token: <token>`, and `credentials: same-origin`. This avoids `request.form()`/multipart and any new parser dependency. It does not automatically resend on network error. It renders only a fixed status label returned by the server; browser refresh remains a GET and cannot repeat a POST. Disable the clicked button while its request is outstanding; this is UX, not the server-side idempotency guarantee.

### Endpoints and payload

| Method/path | Input | Purpose |
| --- | --- | --- |
| `GET /` | No target, no analysis parameters | Status + bounded selector + action CSRF token; no analysis. |
| `POST /analysis/email` | JSON `{"source_record_id": <positive integer>}` | Initial non-force manual analysis. |
| `POST /analysis/email/retry` | Same JSON shape | Explicit non-force retry, legal only for a matching current-input retryable run. |

The two POSTs accept exactly one JSON key, reject booleans and non-positive/non-integer IDs, reject unknown keys, and reject bodies above **256 bytes**. Read a bounded request stream before JSON parsing; require `Content-Type: application/json` (optional UTF-8 charset only). Neither endpoint accepts account scope, request mode, force, provider URL/model, credential reference, message text, or an idempotency override. The account scope always comes from server settings; the service/repository verify the source belongs to it. Both POSTs require an Origin header; `Referer` is not a fallback. Response is bounded JSON `{"status": "<whitelisted code>"}`, never a raw exception or `AnalysisResult` serialization.

## 3. Selector read contract

Add `AnalysisRepository.list_eligible_email_refs(account_scope: str, *, limit: int = 20) -> tuple[SelectableEmailRef, ...]`. The caller owns a read-only Session/transaction. Reject invalid scope or limit outside `1..20`; route never accepts limit from browser. Query `SourceRecord` + `EmailMessage` + `ConversationMembership` + `Conversation` with:

- source type `email_message`; source scope equals configured account scope; `retention_state='active'`; `deleted_or_redacted_at IS NULL`;
- normalized body is non-NULL (empty string remains eligible under the existing domain contract);
- exactly the current membership; conversation scope equals account scope, `legacy_status='resolved'`, and `superseded_at IS NULL`.

Order by `coalesce(EmailMessage.sent_at, EmailMessage.received_at, SourceRecord.source_timestamp, SourceRecord.ingested_at)` descending, then `SourceRecord.id` descending, `LIMIT 20`. Fetch only ID, scope, sender, subject and dates; never select body, MIME, attachments, locations, recipient list, or credentials for the selector query. Return an immutable internal DTO. `SourceRecord.id` is unique and membership has a unique source key, so no duplicate row should be rendered.

Add `AnalysisRepository.latest_run_for_target(account_scope, source_record_id) -> AnalysisRun | None`, ordered by `run_version DESC`, for server-side state derivation; do not expose the ORM row to the template. Add `list_manual_analysis_options(session_factory, account_scope, *, limit=20) -> tuple[ManualAnalysisOption, ...]` in `app/services/email_analysis.py`. In a read-only transaction it obtains repository refs, calls existing `select_analysis_input` for each bounded candidate to compute the **current** canonical digest, and compares it with latest run and existing `replay_lookup`. It emits only safe, bounded metadata and state; candidates that become ineligible while reading are omitted. This local canonicalization does not call AI or write a run. State precedence: matching reserved → `in_progress`; existing completed replay for current digest/versions → `completed`; latest matching retryable → `retry_required`; otherwise → `ready`. The POST recomputes/revalidates all of this; GET state is advisory only.

## 4. Atomic initial/retry policy

The route must not infer retry permission from the displayed row. Extend the **service and repository reservation boundary**, not just UI labels:

- Add an optional `manual_intent: Literal["initial", "retry"] | None = None` keyword to `analyze_email_in_thread`. Existing callers with `None` keep their present behavior. Reject non-`None` intent unless `request_mode="manual"` and `force_reanalysis=False`.
- Add `AnalysisRepository.reserve_manual_run(..., intent: Literal["initial", "retry"]) -> AnalysisReservation` (or equivalent exact wrapper) in the same caller-owned transaction as canonical input selection. Reuse `reserve_run` for actual insertion. This method must validate target/account/conversation and decide using current digest, contract version and policy version; do not add a persistent request identity or a new `request_mode` value.
- Precedence, before any new insert: a matching `reserved` run returns `in_progress` for either intent; existing normal `completed_replay` returns that no-new-provider outcome for either intent. If the latest run for that target matches the current digest/versions and is `failed_retryable` or `stale_retryable`, `initial` returns `retry_required` with no insert and `retry` may reserve a new `manual` version. If there is no matching retryable latest run, `retry` returns `retry_not_available` with no insert. Otherwise `initial` may reserve a new `manual` version. A retryable run for an **older/different current input** does not force a retry action for a now-changed input.
- Extend `AnalysisReservation`/`AnalysisResult` only as needed for the two bounded no-write outcomes; no model/table/constraint changes. The service must return before provider invocation on either outcome. Preserve `completed_replay`, `in_progress`, force and automatic semantics for existing callers.
- Reservation conflicts under concurrent POSTs must roll back the losing transaction and return a bounded non-provider outcome (`in_progress` if a matching reservation can be confirmed; otherwise `unavailable`), never fall through to a second provider attempt. SQLite uniqueness remains the backstop. A second explicit retry **after a prior retry has itself finished retryably** is a new operator action under D17; repeated browser refresh is not, because the browser never resubmits automatically. No guarantee of deduplicating arbitrary malicious/manual replay of the retry endpoint is claimed without a persistent request identity.

## 5. POST preflight, composition and responses

Order for **both** POSTs:

1. Existing router Host dependency and `validate_protected_request(request, X-CSRF-Token)`; if invalid, stop before DB, credential store or provider. No token in query. Require a signed session containing the issued token and exact same-origin local Origin.
2. Check `operational_ready is True` and the current `operational_lock.is_owner is True`; any exception/unavailable lock fails closed. Inert app never analyzes.
3. Check process-local commercial gate ON; OFF → `blocked`, with **no credential lookup, reservation or provider call**. Do not enable it here. Check technical `settings.ai.enabled`; OFF → `disabled`, also no reservation. Gate takes precedence if both are OFF.
4. Probe credential **presence only** through current store after gate/readiness checks; `missing`/`unavailable` stop before reservation. Do not fetch or expose secret in route. A subsequent credential race is handled by the adapter and becomes a bounded provider failure.
5. Validate bounded JSON ID; use `settings.imap.account_scope` server-side. Construct `OpenAIAnalysis(settings.ai, app.state.credential_store, ownership=app.state.operational_lock, commercial_gate=app.state.commercial_gate)`. Build a new session factory for the existing service, call with `request_mode="manual"`, `force_reanalysis=False`, `manual_intent="initial"` or `"retry"`; dispose the engine on completion/error. No route-level SQL or direct provider call. The service revalidates target/conversation/current input and the adapter independently rechecks live gate and ownership before any provider attempt/retry.

| Bounded response status | HTTP | Exact condition / side effect |
| --- | ---: | --- |
| `completed` | 200 | New run completed. |
| `completed_replay` | 200 | Existing matching completed run; no new provider call. |
| `in_progress` | 202 | Matching reservation already exists; no new provider call. |
| `retry_required` | 409 | Initial endpoint sees matching retryable latest run; no new run/call. |
| `retry_not_available` | 409 | Retry endpoint has no matching retryable latest run; no new run/call. |
| `blocked` | 403 | Commercial gate OFF. |
| `invalid_request` | 400 | Malformed/oversize/non-JSON body, wrong shape, missing/invalid ID. |
| `invalid_target` | 404 | No longer eligible, wrong account, redacted/deleted, unresolved/superseded conversation, or unknown ID; no provider call. |
| `unavailable` | 503 | No readiness/ownership, DB or reservation conflict not safely classified, or other bounded operational failure. |
| `disabled` | 503 | Technical AI switch OFF after gate ON. |
| `credential_missing` / `credential_unavailable` | 503 | Presence probe fails after authorization preflight; no reservation. |
| `no_analyzable_body` | 422 | Existing service finds no analyzable target body; no provider call. |
| `failed_retryable` / `stale_retryable` | 200 | Service persisted a bounded failed/stale outcome; next initial action requires distinct Retry if current input still matches. Never include its raw `failure_code` or source digest. |
| `invalid_security` | 403 | Missing/invalid CSRF, session or Origin; no DB/credential/provider access. Foreign Host remains the existing 400. |

No raw error, source text, provider response, credential, digest, run ID, internal account scope or lock handle appears in the response. For an already-sent provider call, gate disable prevents new retries but cannot recall that call. Source changes between GET and POST or between reservation and completion are handled by the existing domain/revalidation path, producing `invalid_target` or `stale_retryable` as applicable. A result status is not an external action approval.

## 6. Exact Scope Lock and per-file work

**IN SCOPE — modify exactly these seven files:**

1. `app/persistence/repositories.py` — immutable selector ref, bounded eligible query, latest-run read, atomic manual-intent reservation wrapper and bounded no-write outcomes.
2. `app/services/email_analysis.py` — safe selector projection/current-input state, optional manual intent in existing orchestration, no-provider early outcomes, conflict classification.
3. `app/web/routes.py` — GET selector composition, two protected POSTs, bounded request parsing/preflight/response mapping, adapter+factory lifetime. Preserve `/health`.
4. `app/web/templates/status.html` — bounded selector, action buttons and same-origin JSON/CSRF script; no raw data or gate control.
5. `test/test_persistence_repositories.py` — selector ordering/eligibility/limit, manual-intent matrix and transaction/concurrency cases.
6. `test/test_email_analysis_service.py` — selector projection, current-input state, early no-provider outcomes, retry/changed-input/replay and rollback tests.
7. `test/test_status.py` — browser GET and POST mapping, CSRF/Origin/Host, readiness/gate/credential preflight, fake adapter/service only, no real network.

`app/main.py` need not change: existing app state already has settings, lock, gate and credential store. `test/test_security.py` need not change if security route cases are covered in `test/test_status.py`; 6E3 retains a separately scoped adversarial regression. **OUT OF SCOPE:** all other files, including `app/security/session.py`, `app/integrations/openai_analysis.py`, models, migrations, configuration, credentials, dependencies and documentation. **RESTRICTIONS:** no new external calls in tests, no scheduler, no commercial gate activation UI, no force mode, no direct route SQL, no database identity migration, no external mutation, no automatic email send.

## 7. Ordered implementation and validation

1. Add repository read DTO/query and tests for scope, active retention, resolved/non-superseded conversation, no body exposure, null metadata, 20-row bound and deterministic ties.
2. Add atomic manual-intent reservation policy and repository tests for current-input matching, completed/in-progress precedence, retry required/not available, changed digest, automatic/force regression, rollback and competing retry requests.
3. Add service selector and explicit intent handling; verify no provider call for no-write states and existing result/transaction semantics.
4. Add GET selector and two POSTs; validate no action before session/CSRF/Origin/Host, readiness/ownership/gate/technical/credential preflight; use fake provider/store/lock only.
5. Add template controls and offline UI tests: no analysis from GET/refresh; correct action label; no body/digest/secret/error leakage; JavaScript sends JSON/header and never auto-retries.
6. Run `python -m pytest test/test_persistence_repositories.py test/test_email_analysis_service.py test/test_status.py test/test_security.py test/test_startup.py`, then `python -m pytest`, then `git diff --name-only` and `git diff --check`; verify only the seven Scope-Locked files changed before any separately authorized commit/push.

## 8. Rollback, risks and STOP findings

Feature rollback is to stop exposing both POST actions while retaining historical `AnalysisRun` records; never delete or rewrite run history. Runtime disable is immediate via the independent gate; the adapter rechecks before each attempt/retry. Failed/stale runs remain retryable through a separate operator action; no UI response grants provider or external-action authority.

Principal risks: stale selector view, wrong target, source changes, repeated retry requests, gate/owner revocation, provider/credential failure, cross-origin request, secret/content leakage, and embedded instructions in email. Repository/service revalidation, browser/request protection, bounded outputs and existing AI projection/evidence checks address these within the approved scope. GET may locally read canonical source text to derive current state but never renders or transmits it.

**STOP findings: none.** Current tables and constraints support the approved distinction between initial and retry without a new persistent identity; existing FastAPI/Starlette and standard JSON parsing suffice without a new dependency. If implementation reveals a need for a migration, model/config/dependency change, or another file, STOP rather than expand this plan silently.
