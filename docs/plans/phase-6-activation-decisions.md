# Phase 6 Activation Decisions

**Status:** APPROVED
**Date:** 2026-09-24
**Analysis:** docs/plans/phase-6-activation-analysis.md

## D1 — Operational trigger

Approved:
- Phase 6 will use **explicit manual user-triggered analysis from the local interface**.
- No background scheduler or automatic analysis trigger in this phase.
- Starting the app, loading status, or enabling provider configuration must not itself cause an OpenAI call.
- Any future scheduler/background automation requires a separate analysis, Scope Lock and approval.

## D2 — Activation authorization gate

Approved:
- `AISettings.enabled` is only a technical/provider availability switch.
- It is **not** authorization to transmit commercial data.
- A separate runtime activation gate must be checked immediately before every real provider call involving commercial data.
- The gate must fail closed.
- Commercial-data authorization is currently **OFF**.
- Under the accepted Phase 5 policy, commercial data remains blocked until either:
  1. EU processing eligibility is verified for the actual account/project, or
  2. the user gives a separate explicit decision accepting Global processing.
- Merely configuring `api.openai.com`, `eu.api.openai.com`, or passing a smoke test does not grant commercial-data authorization.

## D3 — Local status presentation

Approved:
- Extend the existing localhost status surface rather than create a separate public or remote diagnostics service.
- Status may show only non-sensitive state, including:
  - AI enabled/disabled;
  - configured provider/model;
  - endpoint class: global/eu/unknown;
  - credential present/missing;
  - synthetic smoke pending/passed/failed if retained;
  - commercial-data gate blocked/authorized.
- Status inspection must not call OpenAI.
- Secret values, headers, request/response bodies, provider raw errors and email content must never be shown.

## D4 — Credential operator workflow

Approved:
- Provide a **small local interactive CLI/helper** for API-key provisioning.
- Secret input must be non-echoing and must not be passed as a command-line argument.
- Support operator actions:
  - set/replace;
  - presence/status check without revealing the value;
  - delete.
- Reuse Windows Credential Manager/keyring; no new secret store.
- The API key must never be stored in TOML, Git, SQLite, logs, browser output, screenshots or shell history by design.
- Exact service/account identifiers must remain aligned with `AISettings.credential_service` / `credential_account`.

## D5 — Synthetic live smoke

Approved:
- Use a **dedicated explicit local CLI command** for synthetic live smoke.
- It must not be part of default pytest.
- It must use synthetic non-commercial content only.
- It may perform a real provider call only under a separately approved execution step.
- It must not read IMAP, CRM, Calendar, production SQLite content or real commercial messages.
- It must verify the configured credential, endpoint connectivity, model acceptance, Responses API, strict Structured Outputs, decoder path and bounded operational behavior.
- It must send `store=false` and expose no tools/functions/web/browser/computer/code-execution capability.
- A successful smoke does not authorize commercial-data processing and does not prove EU residency, ZDR or retention guarantees.

## D6 — Kill switch and runtime disable semantics

Approved:
- Use a runtime gate that is rechecked before each new provider call and before any retry.
- Disabling the gate must prevent all **new** provider calls and retries.
- An already-sent provider request may be allowed to finish; Phase 6 will not introduce process/thread termination machinery.
- No claim of recalling data already transmitted.
- Define and test recovery semantics for `AnalysisRun` records left `reserved` after interruption.
- The rollback path must be simple and fail closed.

## D7 — Telemetry and persistence

Approved:
- Keep telemetry minimal in Phase 6.
- Do **not** introduce a new provider-telemetry table or migration solely for OpenAI metrics.
- Persist only what is required for safe operation using existing mechanisms where appropriate.
- Detailed latency/retry/byte telemetry may be revisited later after operational experience.
- Never persist:
  - API key;
  - authorization headers;
  - raw provider error;
  - request/response body;
  - email content solely for telemetry;
  - secret-bearing payloads.

## Documentation correction

Approved for inclusion in a separately scoped documentation correction:
- `docs/architecture.md` contains a historical statement that no AI provider/model has been selected.
- Phase 5 has selected OpenAI and default model `gpt-6-sol`.
- The stale statement should be reconciled in a controlled documentation task or in the Phase 6 implementation plan if the Scope Lock explicitly includes it.
- Do not modify it silently outside an approved scope.

## Frozen constraints

Phase 6 must preserve:
- local-only single-user architecture;
- no automatic email sending;
- proposal -> explicit approval -> revalidation -> execution -> audit for irreversible actions;
- no automatic commercial-data transmission on startup/import/status;
- existing 30,000-character and six-prior disclosure limits;
- no attachment transmission;
- prompt-injection boundary;
- evidence/provenance validation;
- no Global commercial-data processing without a later explicit decision.

## Planning direction

Prepare an implementation plan with small, independently reviewable subphases. Preferred sequence:

- 6A — runtime activation gate + safe composition foundation;
- 6B — local status + credential presence;
- 6C — interactive credential CLI;
- 6D — synthetic live-smoke CLI tooling, still offline-tested;
- 6E — rollback/recovery + security regression;
- 6F — optional one-shot live synthetic smoke, separately approved at execution time;
- 6G — optional commercial-data activation, only after a separate processing-mode decision.

No subphase is automatically approved by this decision record.


## D8 — Commercial authorization state

Approved:
- Commercial authorization is **process-local**, revocable, and defaults to OFF.
- Authorization does not persist across application restarts.
- No authorization table or migration is introduced in this phase.
- Restarting the application resets commercial authorization to OFF.
- Synthetic smoke must use a separate synthetic-only execution path and must not provide a general bypass capable of carrying arbitrary commercial content.
- Turning the provider technical switch on does not turn commercial authorization on.

## D9 — Manual web trigger protection

Approved:
- The commercial manual trigger remains a local web/UI action.
- A state-changing analysis POST must require:
  - a valid local session;
  - CSRF protection;
  - origin/host validation appropriate to the localhost-only application.
- Localhost alone is not treated as sufficient CSRF/authorization protection.
- No commercial-analysis POST may be exposed before these controls exist and are covered by offline tests.
- No CLI-based commercial trigger is introduced as a substitute in this phase.

## D10 — Interrupted reserved-run recovery

Approved:
- Recovery of orphaned `AnalysisRun(status=reserved)` records is performed in a controlled startup recovery step before manual analysis becomes available.
- Recovery must use the existing bounded state `failed_retryable / interrupted`.
- Recovery must not blindly convert every reserved run.
- The implementation must define and test an ownership/liveness/age rule sufficient to avoid marking a genuinely active request as interrupted.
- Because the application is local single-user, prefer the smallest safe rule without introducing distributed coordination machinery.
- Recovery must be atomic and idempotent.
- If a safe orphan-detection rule cannot be derived from existing data, STOP rather than inventing one.

## D11 — Synthetic smoke result retention

Approved:
- Synthetic smoke state is **transient and process-local** in Phase 6.
- Do not persist smoke passed/failed history to SQLite.
- No telemetry/smoke-history table or migration.
- Status may display current-process `pending/passed/failed` only if the implementation can do so without creating a new persistence layer.
- A previous successful smoke does not survive restart as an authorization fact.
- Re-run the smoke when operationally required before a later commercial activation decision.

## Consequence for the implementation plan

The Phase 6 plan may now be finalized around these choices:
- process-local commercial gate, OFF on restart;
- protected localhost web trigger with local session + CSRF + origin/host validation;
- startup orphaned-reservation recovery using existing run states and a proven safe detection rule;
- transient smoke result only;
- no new migration solely for authorization, smoke history, or provider telemetry.

The remaining planning task is to produce exact per-subphase Scope Locks and STOP if the existing schema cannot safely distinguish orphaned reserved runs.


## D12 — Single-instance operational ownership

Approved:
- The assistant is local, single-user and non-distributed; Phase 6 will prefer an **exclusive single-instance operational lock** over adding per-run process ownership fields.
- Only one operational application instance may own the analysis execution capability at a time.
- The operational instance must hold an exclusive local/OS-level lock for its entire lifetime.
- A second instance must fail closed and must not expose manual analysis or call the provider.
- No provider call may occur unless the current process/runtime proves ownership of the operational lock.
- After acquiring the lock during controlled startup, and before enabling the manual trigger, inherited `AnalysisRun(status=reserved)` rows from the previous operational instance may be transitioned atomically/idempotently to `failed_retryable / interrupted`.
- This design avoids adding PID/creation-time/heartbeat/lease fields to `AnalysisRun` unless single-instance ownership cannot be proven safely.
- No migration is approved by this decision.
- The design must be verified specifically on Windows and with the project's Uvicorn startup/reload behavior.
- Do not assume that the reloader parent, child worker, or module import process is the correct lock owner without proving it.
- If the Uvicorn/Windows process model prevents unambiguous lifetime ownership, STOP and return to a separately approved persistent per-run ownership design.
- Any implementation must include tests for:
  - second-instance refusal;
  - zero provider calls without ownership;
  - clean release on normal shutdown;
  - restart reacquisition;
  - startup recovery only after ownership is acquired;
  - no duplicate recovery;
  - interaction with development reload mode.


## D13 — Windows single-instance lock mechanism

Approved following `docs/plans/phase-6-single-instance-analysis.md`:

- Use an exclusive Windows file handle opened with no sharing as the operational single-instance lock.
- Implement with Windows APIs available through the Python standard library/ctypes; no new third-party locking dependency.
- Lock identity must derive from the canonical absolute SQLite database identity, not working directory, application port or PID.
- The lock handle must be non-inheritable and strongly held by the actual serving worker for the entire operational lifetime.
- A stale sidecar filename has no ownership meaning; ownership is the live exclusive OS handle.
- Failure to derive a safe canonical identity, open the lock location, or acquire exclusivity must fail startup closed for operational analysis.
- The reloader parent must never count as operational owner.
- Operational AI mode does not support Uvicorn `--reload` or multiple workers.
- Development reload remains allowed only with operational AI/manual commercial analysis disabled.
- No provider attempt or retry may occur without valid operational lock ownership plus the independent commercial authorization gate.
- Startup recovery of inherited `reserved` runs may execute only after the operational lock is successfully acquired.
- Shutdown must stop new analysis and ensure no provider work remains before releasing the lock.
- A replacement process must acquire the OS lock before any recovery; delayed OS release after abnormal termination means temporary startup refusal, never permission to bypass the lock.
- Before the first deployment of the lock-aware build, all pre-lock application instances/provider calls must be quiescent. Legacy ownerless reservations must not be swept merely because the new lock was acquired unless a separately approved quiescent recovery rule covers them.
- If these constraints cannot be enforced or verified in implementation tests, STOP and fall back to separately approved persistent per-run ownership.

This decision does not authorize live provider calls or commercial-data processing.


## D14 — Persistent lock-aware cutover marker

Approved:
- Reuse the existing `ConfigurationReference` model as the persistent marker for the transition into the lock-aware runtime era.
- No new table, column or migration is introduced for this purpose.
- The marker must contain only bounded non-sensitive configuration metadata.
- The marker may be created only while the process holds the exclusive operational single-instance lock.
- First lock-aware startup behavior:
  1. acquire the operational lock;
  2. check for the cutover marker;
  3. if marker is absent, inspect `AnalysisRun(status='reserved')`;
  4. if any reserved row exists, fail startup closed and modify no analysis run;
  5. if zero reserved rows exist, create the cutover marker atomically.
- Once the marker exists, any later startup that successfully acquires the operational lock may treat inherited `reserved` rows as belonging to a prior lock-aware instance and transition them atomically/idempotently to `failed_retryable / interrupted`.
- Do not use age, PID, heartbeat, timeout or other heuristics to infer orphanhood.
- Marker absent + any reserved row = operator intervention required; automatic recovery is prohibited.
- Before the first lock-aware cutover attempt, the operator must stop and verify that all pre-lock application instances/provider calls are quiescent.
- The cutover marker is not commercial authorization, not AI enablement, not provider consent and not a smoke-test result.
- Marker creation and recovery must be covered by isolated SQLite tests.
- If `ConfigurationReference` cannot support this safely under its existing constraints/repository access, STOP and request a new data-model decision instead of repurposing another table.

This decision supersedes the earlier assumption that first deployment could rely on an operator-only quiescence invariant without a persistent boundary marker.


## D15 — Synthetic smoke public boundary

Approved:
- Add a dedicated `OpenAIAnalysis.smoke()` public method with **no caller-supplied payload, AnalysisInput, mode, token or arbitrary text argument**.
- `smoke()` constructs one fixed immutable non-commercial synthetic `AnalysisInput` internally.
- Commercial `OpenAIAnalysis.analyze(AnalysisInput)` remains unchanged as the commercial entry point and continues to require operational ownership plus commercial gate ON.
- Smoke must **never read, enable or mutate** the commercial activation gate.
- Smoke requires technical AI enabled and valid operational single-instance ownership.
- Smoke reuses the same private provider execution mechanics as commercial analysis: endpoint allowlist, configured model, credential reference, request-size limits, strict Responses JSON Schema, decoder, max output tokens, store=false, no tools/functions, bounded timeout/retry/error handling.
- Ownership is rechecked before the first smoke provider attempt and before every retry after any delay.
- The smoke method is one-shot per adapter instance; a second call fails with a bounded local code.
- The exact synthetic payload is fixed in adapter code and snapshot-tested. It contains no IMAP/CRM/Calendar/SQLite commercial source data and no externally supplied fields.
- The dedicated CLI acquires the same `SingleInstanceLock(settings.database_url)`; if another operational owner exists, smoke fails closed.
- The CLI accepts no request content/data argument and does not read commercial SQLite rows or source selectors.
- Smoke result is transient/process-local only and is not persisted.
- A successful smoke does not imply EU residency, ZDR, retention guarantees, compliance approval or permission for commercial-data processing.
- Real live smoke execution remains separately authorized under Phase 6F; Phase 6D implementation and pytest remain offline/faked.
- No environment-variable bypass, public synthetic flag, temporary commercial-gate enablement, caller-constructible token or duplicate provider implementation is permitted.
