# Phase 6 — Safe AI activation implementation plan

**Status: BLOCKED — STOP; not approved for implementation.**
**Date:** 2026-09-24.
**Authority:** `docs/plans/implementation-phase-6-plan-task.md`, `docs/plans/phase-6-activation-decisions.md`, and the Phase 6 analysis.
**This task's exact Scope Lock:** create this file only. No implementation, provider call, credential access, migration, or configuration change.

## 1. Objective, context, and interpretation

Plan the smallest separately reviewable increments from the accepted, disabled Phase 5 OpenAI adapter to safe local operation. The approved Phase 6 decisions fix manual localhost triggering, a distinct fail-closed commercial-data gate, the existing status surface, an interactive credential CLI, an opt-in synthetic smoke CLI, per-attempt kill-switch checks, and minimal telemetry. This document must not itself authorize commercial transmission. An exact implementation plan cannot yet be issued because material security and recovery choices remain open (Section 10).

## 2. Documentation consulted

- `AGENTS.md`; `skills/analyze-task/SKILL.md`; `docs/plans/implementation-phase-6-plan-task.md`.
- `docs/plans/phase-6-activation-analysis.md`; approved `docs/plans/phase-6-activation-decisions.md`; `docs/plans/phase-5-ai-provider-decisions.md`; `docs/plans/implementation-phase-5-plan.md`.
- Relevant sections of `docs/functional-spec.md`, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`.
- Read-only contracts in `app/main.py`, `app/web/routes.py`, `app/web/templates/status.html`, `app/config.py`, `app/security/credentials.py`, `app/security/session.py`, `app/integrations/openai_analysis.py`, `app/services/email_analysis.py`, `app/persistence/database.py`, `app/persistence/models.py`, `app/persistence/repositories.py`, and related startup/status/config/provider tests.

No required document is missing. No tests or code were executed, no real provider or credential was accessed, and no production data was read.

## 3. Current state and approved boundaries

- `create_app()` is the only visible composition root. It validates loopback, stores settings, includes two read-only routes, and constructs no AI provider, gate, session factory, or scheduler. The module-level `app = create_app()` makes import/startup side effects especially important.
- The web UI is a minimal status template. There is no manual analysis form/POST. `app/security/session.py` has CSRF token helpers, but the inspected app has no session middleware, authenticated local request context, or origin enforcement for a new state-changing route. Localhost alone is not an authorization/CSRF defense under `docs/security.md`.
- `AISettings.enabled=False` is a technical switch, not consent. `OpenAIAnalysis` holds settings at construction, makes at most two attempts, and has no runtime gate hook. A wrapper around the service alone cannot prevent the adapter's internal retry after the gate is disabled.
- `CredentialStore` and `KeyringCredentialStore` expose only `get_secret`; set/delete/presence are not implemented. Status and CLI must never echo a key. The existing `app/config.py` carries logical credential service/account names, default model `gpt-6-sol`, and no authorization state.
- `AnalysisRun` supports `reserved`, `completed`, `stale_retryable`, `failed_retryable`; the repository accepts `failed_retryable/interrupted`. A matching `reserved` run returns `in_progress`, but no process-safe interruption recovery protocol is visible. No new telemetry table or migration is approved solely for metrics.
- Phase 5/6 approvals do not authorize real commercial-data processing. The actual project's EU eligibility is unverified/unavailable as recorded in Phase 5; Global commercial processing needs a separate explicit user decision. Synthetic smoke is separate and requires its own live-execution approval.

## 4. Approved decisions mapped to candidate components

These mappings identify impact; they are **not executable Scope Locks** until Section 10 is resolved.

| Decision | Candidate files/components | Non-negotiable contract |
| --- | --- | --- |
| D1 manual local trigger | `app/main.py`, `app/web/routes.py`, possibly a dedicated service boundary, related route/startup tests | Explicit action only; no scheduler and zero calls on import/startup/status/configuration |
| D2 commercial gate | New narrowly scoped gate module, `app/integrations/openai_analysis.py`, composition and fake-client tests | Separate from `AISettings.enabled`; check before each commercial attempt and internal retry; OFF by default |
| D3 local status | `app/web/routes.py`, `app/web/templates/status.html`, `test/test_status.py`, possibly credential-presence adapter | Local-only; non-sensitive enabled/provider/model/endpoint class/presence/smoke/gate state; no OpenAI request |
| D4 credential CLI | New local CLI module, `app/security/credentials.py` or a separate keyring operator adapter, related tests | Non-echoing input; set/replace/status/delete; no key in argv, TOML, Git, SQLite, logs or browser |
| D5 synthetic smoke CLI | New explicit CLI module and isolated fake-client tests | Literal synthetic input only; no production DB, IMAP, CRM, Calendar, or default-pytest live call |
| D6 disable/recovery | Gate, adapter retry boundary, run-recovery repository/service, tests | No new call/retry after disable; already-sent request may finish; interrupted reservations reconciled safely |
| D7 minimal telemetry | Existing bounded `AnalysisRun`/audit mechanisms if sufficient; no new metrics model | No bodies, secrets, raw errors, headers or new telemetry-only migration |
| Approved documentation correction | Separately scoped `docs/architecture.md` edit | Reconcile historical “no provider selected” with Phase 5 OpenAI/`gpt-6-sol`; do not edit in this task |

## 5. Provisional sequence and Scope Lock envelopes

The sequence below follows the approved staging, but file lists are **conditional proposals**, not exact approved implementation locks. In particular, no manual commercial trigger may be exposed before the web-security and gate decisions in Section 10.

| Subphase | Proposed IN SCOPE | OUT OF SCOPE / restriction | Planned validation |
| --- | --- | --- | --- |
| 6A1 — gate and adapter check | New gate module, `app/integrations/openai_analysis.py`, gate/adapter tests | No route, CLI, status, real key, provider call or commercial authorization | `python -m pytest test/test_openai_analysis.py` then `python -m pytest`; check disabled-before-secret and disable-before-retry |
| 6A2 — composition foundation | `app/main.py`, `test/test_startup.py`; optionally a small dedicated composition module only if separately scoped | No automatic trigger, scheduler, provider call on import/startup or `AISettings.enabled` alone | `python -m pytest test/test_startup.py test/test_openai_analysis.py` then `python -m pytest` |
| 6B — status and safe presence | `app/web/routes.py`, `app/web/templates/status.html`, `test/test_status.py`; credential boundary/test only if needed and explicitly scoped | No secret value, call to OpenAI, public diagnostics or activation toggle | `python -m pytest test/test_status.py test/test_credentials.py` then `python -m pytest` |
| 6C — interactive keyring CLI | New local credential CLI, credential adapter if required, CLI/credential tests | No new secret store, key in argv/env/output/logs, or browser provisioning | `python -m pytest test/test_credentials.py` plus new CLI test, then `python -m pytest` |
| 6D — synthetic smoke tooling | Dedicated explicit smoke CLI and its offline fake-client tests | No real call in default tests; no production DB/IMAP/CRM/Calendar access; no commercial input | Smoke CLI fake-client tests plus `test/test_openai_analysis.py`, then `python -m pytest` |
| 6E — manual trigger, rollback/recovery and security regression | Exact route/session/recovery/gate files to be determined by Section 10; tests in startup/status/service/security/repository areas | No scheduler, automated transmission, action execution, or schema change without separate approval | Focal route/recovery/security tests with isolated SQLite and fakes, then `python -m pytest` |
| 6F — optional one-shot live synthetic smoke | Exact separately approved command and run record; no implicit code change | Never default pytest; no commercial data; no claim of EU residency/ZDR | One explicitly approved synthetic call, bounded output and spend; record non-sensitive outcome |
| 6G — optional commercial-data activation | Exact separate authorization/processing-mode task after new decision | Blocked under current no-EU/no-Global-approval state | Prove gate, credential, smoke, rollback and legal/data controls before any commercial call |
| Documentation-only correction | `docs/architecture.md` alone under its own Scope Lock | No behavior/config/code change | Review exact diff and alignment with Phase 5 decisions; no tests needed for prose-only edit |

The preferred order is 6A1 → 6A2 → 6B → 6C → 6D → 6E, with the documentation correction separately scoped; 6F and 6G require new explicit approvals and never merge into one task. Each implementation increment needs its own approved task and exact 2–4-file Scope Lock where feasible. The proposed 6E cannot be finalized until its security and recovery decisions are made.

## 6. Required behavior and acceptance constraints for the eventual plan

1. The runtime gate must be independent of `AISettings.enabled` and default to commercial OFF. The provider-facing path must recheck authorization immediately before the first commercial request and before any retry, after any delay. The gate must deny when authorization is unknown, expired, revoked, inconsistent with processing mode, or absent. A provider request already transmitted may finish; no recall or hard-kill claim is permitted.
2. Normal import, `create_app()`, status render, and normal pytest must make zero provider/network calls. Simply enabling provider settings, provisioning a key, or passing smoke cannot authorize commercial content.
3. Manual analysis must be initiated by a concrete localhost user action and pass through the existing `analyze_email_in_thread()` seam, preserving reservation, replay, stale-source validation, provenance, and no external-action authority. A new state-changing web path must meet `docs/security.md` session/origin/CSRF requirements before it is exposed.
4. Status may show only `enabled`, configured provider/model, endpoint class (`global`/`eu`/`unknown`), credential `present`/`missing`/`unavailable`, bounded smoke state if explicitly retained, and commercial gate `blocked`/`authorized`. Credential presence is not validity; EU-looking host and smoke success do not prove EU processing. `/health` should remain network-free and should not become a credential leak.
5. Credential CLI must accept set/replace via a non-echoing interactive prompt, perform status without printing the value, and delete/rotate through Windows Credential Manager under configured `credential_service`/`credential_account`. It must avoid secret-bearing argv, environment, files, repr, exceptions and logs; fake-keyring tests must cover failures.
6. Synthetic smoke CLI must construct all input from fixed synthetic literals and never open production SQLite or import IMAP/CRM/Calendar clients. It should invoke the existing Responses adapter/strict decoder through a separately authorized synthetic-only path, check `store=false`, no tools/functions, bounded timeout/retry, and emit only bounded result metadata. A successful call is a transport/schema check, not commercial-data consent.
7. Rollback must be one-step and fail closed: prevent all new calls and retries; define user-visible state and safe handling of already-sent requests and pending `reserved` runs. No provider raw text or commercial content may be logged to prove this.
8. No new data-model or migration work is necessary for the **currently OFF** gate or minimal status if smoke history is not persisted. A durable authorization record, persisted smoke history, or new provider telemetry cannot be silently added; each would require a separately approved model decision and migration Scope Lock.

## 7. Dependencies, risks and out-of-scope discoveries

Internal dependencies are the Phase 5 projection/adapter, `AIService`, Phase 4 run repository and data-selection contracts, localhost FastAPI routes, settings, keyring abstraction, and existing CSRF helpers. Automated validation must use fake clients, fake keyring, and synthetic isolated SQLite. No new third-party package is identified by planning; if a session or operator design requires one, STOP for approval.

Main risks: accidental commercial disclosure from startup/status/retry; unauthorized Global processing; secret exposure during provisioning/status; status falsely presenting credential presence as validity or endpoint class as residency; a browser-origin forged manual action; stuck `reserved` runs after interruption; a rollback race with an in-flight request; prompt injection; and AI proposals being mistaken for approved external actions. Default tests must remain entirely offline. No code, migration, configuration, credential, provider, IMAP, Calendar or CRM mutation is part of this planning task.

**OUT-OF-SCOPE DISCOVERY:** `docs/architecture.md` still says no provider/model was selected despite approved Phase 5. The correction is approved only as a separately scoped documentation task; this file does not edit it.

## 8. STOP — unresolved implementation architectures

The Phase 6 decisions resolve the *operational shape* but do not choose all security-relevant mechanisms needed for an exact Scope Lock. At least two reasonable architectures remain in each item:

1. **Commercial authorization state and synthetic bypass.** A process-local, default-OFF revocable gate (authorization lost on restart) versus a durable local authorization record with provenance/revocation. The latter needs an approved data model/migration; the former needs an explicit rule for who may turn it ON and how the synthetic CLI can use the adapter without providing a general bypass for commercial content. Decide the representation, authorization provenance, restart behavior and synthetic-only capability before an activation path is implementable. Until then, commercial remains OFF.
2. **Protection of the manual web trigger.** `app/security/session.py` supplies token helpers, but no session middleware or origin-checking route exists. A server-side session mechanism versus a signed local cookie/session middleware (or a separately approved non-web local invocation) have different secret-storage, CSRF and request-identity consequences. D1 requires a local UI action, but does not specify its session/origin contract. Decide the mechanism and required files before adding a POST that can transmit commercial content. Do not infer that localhost makes CSRF safe.
3. **Interrupted `reserved` run recovery.** Reconcile at controlled process startup before any manual trigger versus an explicit offline operator recovery step. Both can use the existing `failed_retryable/interrupted` transition, but concurrency/process-liveness checks and the handling of a genuinely in-flight request differ. Decide the recovery trigger, ownership/liveness proof and atomicity before a service or repository Scope Lock is final.
4. **Smoke result retention.** Status can show `pending` without persistence, but `passed/failed` across restarts requires a chosen safe retention mechanism. No telemetry table/migration was approved. Decide transient per-process status versus a bounded existing-mechanism record, including timestamp, reset/expiry and whether a successful smoke is a gate prerequisite across restarts.

These are not coding preferences: each changes authority, persistence, or security behavior. The plan may be finalized only after the user approves those choices. No live call is needed to resolve them.

## 9. Result and approval gate

**BLOCKED.** The proposed staging and offline validation above are suitable for discussion, but not yet an executable `Implement Task` plan. Request decisions on the four STOP items, then update this plan with exact per-subphase file Scope Locks and acceptance tests. Even a later `READY FOR APPROVAL` plan would require separate explicit approval for each implementation subphase, a separately approved synthetic live call, and a still later processing-mode decision before commercial-data activation.
