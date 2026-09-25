# Phase 6E2 — Manual commercial-analysis trigger analysis

**Result: STOP.** This is an analysis, not implementation approval. No commercial POST, provider call, credential access, migration, or test execution occurred.

## 1. Objective

Define a user-initiated, locally protected request that analyzes one existing email through the approved service without granting commercial authorization or creating duplicate unintended runs.

## 2. Context and interpretation

Phase 6 is local and single-user. D1 requires an explicit browser action; D2/D8 keep commercial authorization separate, process-local, and OFF by default; D9 requires a valid session, CSRF, and Host/Origin checks. 6E1 supplies those primitives. 6E2 would add a manual trigger, not a scheduler, a gate switch, a direct provider-payload endpoint, or force reanalysis.

## 3. Documentation consulted

`AGENTS.md`; `skills/analyze-task/SKILL.md`; `docs/plans/implementation-phase-6e2-analysis-task.md`; `docs/plans/implementation-phase-6-plan.md`; `docs/plans/phase-6-activation-decisions.md` (D1, D2, D6, D8, D9, D12, D13); `docs/functional-spec.md`; `docs/data-model.md`; `docs/architecture.md`; `docs/security.md`; `docs/testing-strategy.md`. The five core documents exist. No contradiction among them was found on manual triggering; the exact UI and repeat-request policy remain unspecified.

## 4. Current state

- `app/web/routes.py` exposes only `GET /health` and `GET /`; `status.html` displays bounded status and has no email list or action form. There is no commercial POST.
- `create_app()` installs `LocalSessionMiddleware`, a default-OFF `CommercialActivationGate`, and a credential store. Only the operational lifespan acquires `SingleInstanceLock`, completes cutover/recovery, and then sets `operational_ready=True`. Inert app creation is not an execution capability.
- `app/security/session.py` provides a signed host-only local session cookie, reusable CSRF token, Host validation, same-origin Origin validation, and `validate_protected_request(request, token)`. That helper returns a boolean; the future route must reject `False` before accessing analysis data.
- `OpenAIAnalysis(settings.ai, credential_store, ownership=operational_lock, commercial_gate=commercial_gate)` is the existing adapter composition. `analyze()` checks technical enablement, live ownership, and gate before credential lookup or provider access, including before retries. The route must also check readiness and live ownership before constructing/calling it; the adapter remains the final authority.
- `analyze_email_in_thread(factory, adapter, account_scope, source_record_id, request_mode="manual", force_reanalysis=False)` is the existing orchestration. It validates target eligibility and current conversation, reserves a run, calls the provider outside a DB session, revalidates the input, and returns bounded statuses. It does not need browser-supplied message content, model, endpoint, credentials, or force mode.
- `AnalysisRepository.reserve_run` returns `completed_replay` for a matching completed non-force run and `in_progress` for a matching reserved run. After `failed_retryable` or `stale_retryable`, a subsequent same-input request can reserve a new version and call the provider again. The route cannot treat that case as already deduplicated.

## 5. Candidate UI/request designs and rejected shortcuts

**A — Manual internal-key entry on the status page.** Enter `account_scope` plus `source_record_id`; submit JSON with browser JavaScript and a CSRF header to a local POST. This fits the existing six-file 6E2 plan and needs no form-parser dependency, but the current UI gives the operator no way to discover or verify either internal key. Guessing a key is not a safe, user-meaningful selection contract. A fixed account scope from configuration also does not by itself expose which source ID is intended.

**B — Select a displayed existing email.** A bounded, locally queried list can show safe identifying metadata and carry a server-owned source ID into the action. It is more meaningful and reduces wrong-target risk, but no such read/list contract or repository method exists in the current web surface. Defining it may require repository and repository-test changes beyond the approved 6E2 plan Scope Lock. Direct ad-hoc SQL in the route would violate the preferred service/repository boundary and should not be silently chosen.

Rejected: a GET that analyzes; putting the CSRF token in a URL; raw message-body/provider-payload upload; a commercial CLI; a gate-ON control; force mode; hidden automatic scheduling; `Referer` as Origin fallback; `application/x-www-form-urlencoded` or multipart parsing if it requires an added dependency.

## 6. Conditional request, security, and response contract

The target-selection choice must precede a final route/path and payload contract. A narrow candidate is `POST /analysis/email` with bounded JSON containing only an approved target identifier, no commercial text or provider settings; a same-origin browser script can put the session-bound CSRF token in `X-CSRF-Token`. `GET /` may issue the token into a protected local page only for a form/action, not into a URL, status diagnostic, log, or provider request. This is a candidate, **not** an approved exact route.

Before creating an adapter or session factory, a POST must require `validate_protected_request(...)`, `operational_ready is True`, and current `operational_lock.is_owner is True`. Gate OFF and technical AI disabled must give a bounded blocked/unavailable response with zero credential lookup and zero provider calls. Gate state must never be changed by the request. When permitted, the route must pass the current app credential store, lock, and gate to `OpenAIAnalysis` and invoke the existing service in manual, non-force mode. The adapter independently rechecks gate and ownership before each provider attempt. Browser response must whitelist a small status set, with no raw provider error, API key, body, digest, internal lock handle, or provider details. The status page must remain a read-only GET.

A bounded JSON response or POST/redirect/GET could both work, but neither alone resolves duplicate POSTs after retryable failure. There is no basis yet to choose HTTP status mapping or whether a repeated explicit click means retry. `completed_replay` and `in_progress` should be surfaced as bounded non-new outcomes, not reimplemented in the route.

## 7. Ambiguities and decisions required — STOP

1. **Target selection:** approve either (A) manual entry of internal account/source identifiers despite the absence of a discoverable UI, or (B) a bounded email selector, with an explicitly enlarged read-side repository/test Scope Lock if needed. Specify the operator-visible fields and which account scope is selectable. Without this, no safe user-meaningful target or exact payload can be fixed.
2. **Repeated request after retryable outcome:** decide whether every subsequent deliberate submit may start a new attempt, or whether the UI must require a separate explicit “retry” action / request identity. Current service prevents completed and reserved replay, **not** repeat attempts after `failed_retryable` or `stale_retryable`. A redirect or disabled button alone is not durable idempotency. If a persisted request identity is required, that would conflict with the migration-free/Scope-Locked 6E2 plan and needs a separate approval.

These are functional/security decisions, not implementation details. Do not convert either into a default by convention.

## 8. Dependencies and proposed Scope Lock

Internal dependencies: 6E1 session/Host/Origin/CSRF helper; operational lock and startup recovery; process-local gate; existing credential store; `OpenAIAnalysis`; `analyze_email_in_thread`; existing run reservation and target validation. No new external integration is needed. A JSON request body can be parsed with existing FastAPI/Starlette capabilities; no new dependency is intrinsically required. The work can remain config-schema-free and migration-free **only if** the approved repeat policy needs no new persistent request identity.

**Conditional IN SCOPE (current 6E2 plan):** `app/main.py`, `app/web/routes.py`, `app/web/templates/status.html`, `test/test_status.py`, `test/test_email_analysis_service.py`, `test/test_security.py`. If option B requires a repository query contract, its production/test files must be separately approved before implementation. **OUT OF SCOPE:** OpenAI adapter, commercial gate policy, credentials implementation, models/migrations, IMAP/CRM/Calendar, scheduler, automatic or force analysis. **RESTRICTIONS:** no real provider call in tests; no real commercial data; no gate-ON UI; no direct external mutation; no unapproved file, dependency, persistence, or configuration change.

## 9. Risks

- Wrong internal source ID or account scope can select the wrong commercial email; a browser field with no reviewable target metadata amplifies that risk.
- Duplicate submits after retryable failure can produce multiple provider disclosures and runs, even though completed/reserved replay is guarded.
- Creating a run before discovering gate OFF can persist a retryable provider failure; route preflight should avoid that, while adapter checks remain authoritative against races.
- Localhost is not browser authorization: missing session/CSRF/Origin/Host must fail before DB or credential access.
- Source body and embedded instructions remain untrusted data; only existing projection/schema/evidence rules may determine what reaches the provider.
- A second or inert instance must never present an executable path; readiness and live ownership need adversarial testing.

## 10. Offline test matrix and acceptance criteria

Once decisions are approved: valid local session/Host/Origin/CSRF; missing/tampered cookie or token; foreign/malformed Origin/Host; GET and reload never analyze; absent/invalid/wrong-account/deleted/redacted/unresolved target; gate OFF/technical disabled/missing credential/owner lost; fake authorized success; fake provider failure; stale input; `completed_replay`; `in_progress`; retryable-result duplicate policy; no raw secrets/source text/digests in responses/logs; no gate mutation; no real provider, mailbox, CRM, or Calendar access. Assert zero credential/provider calls for failures that must stop at route preflight. Run focused web/service/security tests and the full offline suite only in a later approved implementation task.

## 11. Out-of-scope discoveries

`docs/architecture.md` still contains a historical no-provider-selected statement despite the approved Phase 5 OpenAI selection, already recorded in D1–D13 decision documentation. It is a separate documentation correction, not a 6E2 change.

## 12. Verdict

**STOP / BLOCKED FOR PLAN.** Resolve the two decisions in §7 before fixing an exact route, UI, request/response contract, or implementable Scope Lock. This analysis creates no implementation authority.
