# Phase 6 — Safe AI activation analysis

**Status:** BLOCKED — design decisions required; analysis only.
**Authority:** `docs/plans/implementation-phase-6-analysis-task.md` and the approved Phase 5 decisions.
**Date:** 2026-09-24.

## 1. Objective, context, and interpretation

Determine a controlled path from the accepted, disabled Phase 5 OpenAI adapter to operational use, separating application composition, local status, credential provisioning, a separately approved synthetic live smoke, commercial-data authorization, and rollback. This report is not approval to enable AI, provision a key, call a provider, or transmit customer data. The user-authorized exception to READ-ONLY is creation and publication of this report only.

## 2. Documentation consulted

- `AGENTS.md`; `skills/analyze-task/SKILL.md`; the Phase 6 analysis task.
- `docs/functional-spec.md`, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, and `docs/plans/remote-ai-data-policy.md`.
- `docs/plans/phase-5-ai-provider-decisions.md` and `docs/plans/implementation-phase-5-plan.md`.
- Read-only inspection of `app/main.py`, `app/web/routes.py`, `app/web/templates/status.html`, `app/config.py`, `app/security/credentials.py`, `app/integrations/openai_analysis.py`, `app/services/email_analysis.py`, `app/persistence/models.py`, `app/persistence/repositories.py`, `app/audit.py`, and relevant startup/status/provider/service/security tests.

No required document above is missing. No tests, provider calls, credential lookups, migrations, or external integrations were executed.

## 3. Current-state findings

1. `app/main.py` is a small FastAPI composition root: `create_app()` loads or receives `Settings`, enforces `127.0.0.1`, saves settings in `app.state`, and includes the web router. A module-level `app = create_app()` exists. It constructs no analysis service, credential store, database session factory, scheduler, or provider client.
2. `app/web/routes.py` exposes only `/health` and `/`; the latter renders a minimal `status.html`. Neither is an analysis trigger. No production route or scheduler currently invokes `analyze_email_in_thread()`; its caller supplies an `AIService` explicitly. Thus installing a provider object into `app.state` alone would not constitute operational activation, but adding a trigger without a gate could transmit commercial content.
3. `AISettings.enabled` defaults to `False`, with model `gpt-6-sol`; `OpenAIAnalysis.analyze()` rejects disabled use before credential lookup. When enabled, it projects bounded data, then looks up a secret through `CredentialStore`, imports the SDK lazily, and invokes Responses. The adapter has an instance-level settings snapshot, one in-process request lock, at most one retry, and a soft 60-second overall budget. It has no dynamic cancellation/kill-switch contract.
4. `CredentialStore` and `KeyringCredentialStore` expose only `get_secret(service, account)`. There is no approved application `set`, `delete`, rotation, or non-disclosing presence API. `app/main.py` cannot infer credential presence without invoking that read boundary. No real secret was inspected.
5. `AnalysisRun` persists lifecycle (`reserved`, `completed`, `stale_retryable`, `failed_retryable`), bounded failure code, timestamps and local linkage, but not provider/model, retries, latency, bytes, endpoint class, smoke result, or activation authorization. `AuditEvent` has a generic bounded event/outcome shape; `app/audit.py` currently offers only `APPLICATION_STARTED` as an allowed log event. Existing persistent `reserved` runs can return `in_progress`; no visible startup recovery path resolves an interrupted provider call.
6. Existing Phase 5 tests prove the adapter-to-service seam offline with fake client/keyring and synthetic SQLite. Normal startup and default tests do not request OpenAI. No live synthetic smoke or commercial-data activation has been authorized.
7. The approved Phase 5 decision requires verified EU processing for real commercial data unless the user separately approves Global processing. It records that the current API project does **not** expose EU residency. Neither an EU endpoint string nor a successful synthetic call would establish residency. Commercial-data activation is therefore blocked under the current decision.

## 4. A–H analysis and alternatives requiring a decision

### A. Composition and trigger

The smallest *composition-only* candidate is to provide an explicitly constructed `OpenAIAnalysis` to the existing `AIService` seam; `app/main.py` is an apparent composition root. But there is no production analysis entry point to call it. Two reasonable operational architectures remain:

- **A1 — explicit local user-triggered analysis only:** add a localhost action path that checks the activation gate immediately before invoking the existing service. This keeps AI opt-in per invocation but requires route/UI and request-security review.
- **A2 — scheduled analysis after activation:** add a scheduler/coordinator path that checks the gate before each call. This supports background processing but creates a larger startup, queue, concurrency, cancellation, and recovery surface.

A third possibility is a local CLI/operator command instead of a web route; it avoids UI changes but does not integrate with the eventual dashboard workflow. No option is chosen. Wiring must never create a call during import, startup, status inspection, or merely by setting `enabled=true`.

### B. Local-only status/health

Candidate presentations are **B1** extend the existing localhost status page/route, **B2** a dedicated local status object queried by a later UI/CLI, or **B3** inspect non-secret config only. B3 cannot answer key presence or persisted smoke outcome; B1 has the smallest visible UI surface but needs safe local response handling. The status vocabulary should distinguish configured/enabled, endpoint class (`global`, `eu`, `unknown`), credential *reference* and presence (never value), activation authorization, last synthetic smoke if intentionally persisted, and degraded reason. `/health` must not call OpenAI or become an externally exposed diagnostics endpoint. Credential presence may require a narrowly scoped keyring lookup; deciding when that occurs and what errors mean is still necessary.

### C. Credential provisioning

The existing abstraction cannot write or delete a key. Two reasonable paths are **C1** a small local interactive CLI/helper with no key in arguments, environment, command history, stdout, logs, browser, screenshots, TOML, Git or SQLite; or **C2** documented manual Windows Credential Manager/keyring procedure outside the app, with a non-disclosing presence check. Both need exact service/account reference alignment, replace/rotate/delete, missing/revoked behavior, and a safe operator verification step. C1 adds a write/delete surface and tests; C2 minimizes code but is more error-prone and depends on platform procedure. No new secret store is justified. No credential was created or accessed.

### D. Separately approved synthetic live smoke

Reasonable forms are **D1** a dedicated explicitly invoked local CLI/script, **D2** a pytest live marker excluded from the default suite, or **D3** a local UI/CLI command. A dedicated CLI/script appears easier to separate from ordinary pytest/startup, but choosing its executable interface and secret lookup is still a design decision. Any future smoke must use synthetic non-commercial input, a separately approved task and credential, no IMAP/CRM/Calendar/production SQLite, no tools/functions, `store=false`, and a bounded spend/time budget. It should verify key lookup, DNS/TLS/base URL, model acceptance, Responses strict schema, decoder, and observed timeout/retry behavior without claiming that every retry branch was provoked. A successful smoke does not authorize commercial data or prove EU residency, retention, training controls or ZDR. Record only bounded outcome/timestamp if persistence is approved.

### E. Commercial-data activation gate

All prerequisites must be independently true: accepted Phase 6 wiring; valid provider/model and endpoint configuration; a configured credential; a separately approved successful synthetic smoke; verified account/project processing mode and retention controls; explicit user authorization for that mode; tested rollback; and unchanged no-auto-send/no-external-action authority. Under current Phase 5 decision, no commercial call can pass until verified EU eligibility or a **separate explicit** approval for Global processing. Two gate representations remain reasonable: **E1** non-secret local config plus a separate explicit authorization artifact/confirmation checked at each request, or **E2** a persisted local activation record with provenance, mode, timestamp, and revocation. E1 is simpler but weak for audit/revocation; E2 may require data-model and migration approval. A startup-only check is insufficient. Merely setting `AISettings.enabled=true` must never bypass the commercial gate.

### F. Rollback/kill switch

The current adapter reads settings captured at construction; changing TOML cannot stop a running process immediately. Two policies need approval: **F1** disable-and-restart (simple but any already-running request may finish before shutdown), or **F2** a runtime gate/kill switch checked before each call, with a defined in-flight policy (allow already-sent requests to finish or attempt best-effort cancellation). Neither can guarantee recall of data already transmitted; the 60-second deadline is soft. Pending `reserved` runs need an explicit safe transition/recovery rule after shutdown or interruption; current `interrupted` failure code exists but no automatic startup recovery is visible. Post-disable tests should prove zero *new* fake client calls, including repeated/retry paths and startup.

### G. Observability and audit

Minimum non-sensitive event fields may include fixed outcome/failure code, bounded latency, retry count, provider/model identifiers, request/response byte counts, timestamp, and a local run ID where useful. Prohibit API key, headers, raw provider error, request/response body, email text, and raw payload digests in logs or status. `AnalysisRun` stores lifecycle but not this telemetry. Existing `AuditEvent` is generic; whether event-only audit is sufficient or a dedicated provider-operation record is needed is a data-governance decision. Persistence of last smoke outcome also requires a retention and schema/location decision; do not overload commercial `AnalysisRun` with a smoke against synthetic data without explicit approval.

### H. Validation

Offline tests with synthetic SQLite, fake clock, fake credential store/client and no sockets must cover: import/startup/status produce zero provider calls; disabled and unauthorized modes fail before key lookup; Global remains blocked absent its explicit decision; manual vs scheduled triggers (once selected); gate rechecked per call and retry; no key/raw body in UI/log/audit/repr; credential missing/rotation; status endpoint class and safe presence; smoke command excluded from default pytest; rollback with in-flight/pending-run policy; no action/approval/execution from AI output; existing replay, stale, 30,000-character/six-prior, evidence, and prompt-injection regressions. A separate, user-approved live synthetic smoke is the only potential real call and must not be part of `python -m pytest`.

## 5. Candidate future files and dependencies

These are candidates, **not an approved implementation Scope Lock**:

- Composition/trigger: `app/main.py`, a narrowly scoped new activation/composition module or `app/services/email_analysis.py` only if separately justified, `app/web/routes.py` and associated tests; possibly `app/web/templates/status.html` for a chosen UI. No current scheduler module for analysis was found.
- Status/presence: `app/web/routes.py`, `app/web/templates/status.html`, `app/security/credentials.py` only if its interface is explicitly extended, and `test/test_status.py`, `test/test_credentials.py`, `test/test_startup.py`.
- Provisioning: a new local operator helper/CLI and its isolated tests **or** documentation of a manual OS procedure; no path should be fixed before the C decision.
- Synthetic smoke: a new opt-in CLI/script with isolated tests **or** a separately marked live test, decided under D. Its real execution is outside this analysis and requires a further approval.
- Gate/audit persistence: `app/config.py` and tests if config carries part of the gate; model/migration/repository files only after an explicit E/G data-model decision. Current storage cannot answer all requested historical telemetry as-is.
- Internal dependencies: `AISettings`, `OpenAIAnalysis`, `CredentialStore`, `AIService`, `analyze_email_in_thread()`, `AnalysisRepository`, and localhost app lifecycle. External dependencies are OpenAI's endpoint and Windows Credential Manager only in later authorized phases; none were used here.

## 6. Proposed small subphases and provisional Scope Locks

Each proposal is conditional on the decisions below and requires its own approved task. Do not implement these locks as written.

| Subphase | Provisional IN SCOPE | OUT OF SCOPE / restriction | Validation |
| --- | --- | --- | --- |
| 6A — gate and composition | Chosen gate module, chosen composition root, directly related tests | No route/scheduler provider call on startup; no credential provisioning or live use | Offline gate, startup-zero-call, disabled/unauthorized cases |
| 6B — status/presence | Chosen local status surface, non-disclosing credential-presence boundary, related tests | No secret value, provider call, public endpoint, or live smoke | Offline status/error/redaction tests |
| 6C — operator provisioning and synthetic smoke tooling | Chosen provisioning interface and separate opt-in smoke entrypoint, isolated tests | No automatic execution, commercial content, production SQLite/IMAP/CRM/Calendar | Default pytest remains offline; fake smoke contract tests; later approved one-shot synthetic live task |
| 6D — rollback, recovery, security regression | Chosen kill-switch/recovery layer and tests; schema only if separately approved | No unapproved action authority, scheduler, UI, or live call | Offline in-flight/pending-run, retry, logs and zero-new-call tests; full suite |
| 6E — commercial-data activation (optional) | Exact files defined only after a separate processing-mode and data-governance decision | No activation under current no-EU/no-Global-approval state | Explicit gate proof, synthetic-only preflight, no external action authority |

## 7. Risks

- **Critical — unauthorized disclosure:** `enabled=true` or wiring alone could be mistaken for consent. Gate must fail closed before any commercial request, and no startup/scheduler path may bypass it.
- **Critical — region/retention misstatement:** current project has no verified EU option; endpoint hostname and successful smoke do not prove data residency or ZDR.
- **High — secret exposure:** command-line arguments, shell history, browser status, logs, exceptions, audit payloads, screenshots and raw keyring errors.
- **High — rollback race:** config snapshot and in-flight requests mean a one-step disable does not automatically stop a request already sent or prevent a retry unless the chosen runtime gate covers it.
- **High — stuck reservations:** process interruption can leave `reserved` analysis runs blocking a later attempt until recovery is defined.
- **High — prompt injection and action confusion:** source email and provider output are untrusted, and provider proposals must not become approvals or execution.
- **Medium — misleading status/telemetry:** presence is not credential validity; smoke success is not permission; operational metrics can leak content if raw payloads/errors are recorded.
- **Medium — scope growth:** choosing scheduled activation would require substantially more orchestration than the current Phase 5 seam; a broad refactor is prohibited by the task.

## 8. Ambiguities, STOP points, and decisions requested

**STOP — BLOCKED.** At least two reasonable activation architectures remain. The task and approved documents do not choose among them. Resolve these before an implementation plan:

1. **Trigger/composition:** explicit localhost user action or CLI only, versus background scheduled analysis after activation. Confirm whether Phase 6 should build an operational trigger at all or only a gated composition foundation.
2. **Activation authorization and state:** non-secret config plus a separately recorded manual approval, versus a persisted local authorization record; define its mode, provenance, revocation, and the exact point of per-call enforcement. Real commercial use remains blocked until verified EU processing or separately approved Global processing.
3. **Status presentation:** extend current localhost page/route, use a dedicated local status object, or config-only inspection; decide whether last synthetic smoke and credential presence must be persisted/displayed and who may inspect it.
4. **Credential operator path:** small interactive local helper/CLI versus documented manual Windows Credential Manager procedure; current `CredentialStore` only reads.
5. **Synthetic smoke form:** dedicated opt-in CLI/script versus live-marked pytest versus local command; specify the later approval, synthetic input, spend/time ceiling, and where (if anywhere) bounded result metadata is retained.
6. **Kill-switch semantics:** restart-only versus runtime gate; define treatment of in-flight requests, retries and `reserved` runs after interruption.
7. **Telemetry persistence:** existing generic audit/lifecycle only versus a dedicated provider-operation/smoke record, including retention and any separately approved migration.

No architecture, model, framework or provider change is selected in this analysis. No approved Scope Lock for implementation can be final while these choices remain open.

## 9. Out-of-scope discoveries

- `docs/architecture.md` still says no AI provider/model is selected; later approved Phase 5 decisions and code selected OpenAI/`gpt-6-sol`. This historical statement should be reconciled under a separately authorized documentation task, not silently edited here.
- `app/audit.py` exposes only `APPLICATION_STARTED` as a controlled code; richer AI events would require a separately scoped change.
- No production analysis route/scheduler exists; this is a baseline finding, not permission to add one during analysis.

## 10. Result

**BLOCKED.** The report is ready for a user decision on the seven points above, not for implementation or commercial-data activation. The only authorized artifact from this task is this analysis file.
