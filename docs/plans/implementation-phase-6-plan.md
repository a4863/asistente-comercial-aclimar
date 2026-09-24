# Phase 6 — Safe AI activation implementation plan

**Status: BLOCKED — STOP; safe orphaned-reservation recovery cannot be proved from existing data.**
**Date:** 2026-09-24.
**Authority:** `docs/plans/implementation-phase-6-plan-finalization-task.md`, `docs/plans/phase-6-activation-decisions.md` (D1–D11), and the Phase 6 analysis.
**This task's exact Scope Lock:** update this file only. No implementation, provider call, credential access, migration, or configuration change.

## 1. Objective, context, and interpretation

Plan the smallest separately reviewable increments from the accepted, disabled Phase 5 OpenAI adapter to safe local operation. Approved D8–D11 resolve process-local commercial authorization, a protected manual web action, controlled startup recovery direction, and transient smoke status. This document must not itself authorize commercial transmission. An exact, whole-Phase-6 implementation plan cannot yet be issued because the current `AnalysisRun` data do not permit safe identification of orphaned `reserved` rows (Section 8).

## 2. Documentation consulted

- `AGENTS.md`; `skills/analyze-task/SKILL.md`; `docs/plans/implementation-phase-6-plan-task.md`; `docs/plans/implementation-phase-6-plan-finalization-task.md`.
- `docs/plans/phase-6-activation-analysis.md`; approved `docs/plans/phase-6-activation-decisions.md`; `docs/plans/phase-5-ai-provider-decisions.md`; `docs/plans/implementation-phase-5-plan.md`.
- Relevant sections of `docs/functional-spec.md`, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`.
- Read-only contracts in `app/main.py`, `app/web/routes.py`, `app/web/templates/status.html`, `app/config.py`, `app/security/credentials.py`, `app/security/session.py`, `app/integrations/openai_analysis.py`, `app/services/email_analysis.py`, `app/persistence/database.py`, `app/persistence/models.py`, `app/persistence/repositories.py`, and related startup/status/config/provider tests.

No required document is missing. No tests or code were executed, no real provider or credential was accessed, and no production data was read.

## 3. Current state and approved boundaries

- `create_app()` is the only visible composition root. It validates loopback, stores settings, includes two read-only routes, and constructs no AI provider, gate, session factory, or scheduler. The module-level `app = create_app()` makes import/startup side effects especially important.
- The web UI is a minimal status template. There is no manual analysis form/POST. `app/security/session.py` has CSRF token helpers, but the inspected app has no session middleware, authenticated local request context, or origin enforcement for a new state-changing route. Localhost alone is not an authorization/CSRF defense under `docs/security.md`.
- `AISettings.enabled=False` is a technical switch, not consent. `OpenAIAnalysis` holds settings at construction, makes at most two attempts, and has no runtime gate hook. A wrapper around the service alone cannot prevent the adapter's internal retry after the gate is disabled.
- `CredentialStore` and `KeyringCredentialStore` expose only `get_secret`; set/delete/presence are not implemented. Status and CLI must never echo a key. The existing `app/config.py` carries logical credential service/account names, default model `gpt-6-sol`, and no authorization state.
- `AnalysisRun` supports `reserved`, `completed`, `stale_retryable`, `failed_retryable`; the repository accepts `failed_retryable/interrupted`. A matching `reserved` run returns `in_progress`. The row has `updated_at`, but no owner process identity, lease, heartbeat, or liveness proof. The service closes its reservation transaction before the provider call; `app/main.py` enforces neither singleton process ownership nor a startup recovery lock. No new telemetry table or migration is approved solely for metrics.
- Phase 5/6 approvals do not authorize real commercial-data processing. The actual project's EU eligibility is unverified/unavailable as recorded in Phase 5; Global commercial processing needs a separate explicit user decision. Synthetic smoke is separate and requires its own live-execution approval.

## 4. Approved decisions mapped to candidate components

These mappings identify impact; they are **not executable Scope Locks** while Section 8 is unresolved.

| Decision | Candidate files/components | Non-negotiable contract |
| --- | --- | --- |
| D1 manual local trigger | `app/main.py`, `app/web/routes.py`, possibly a dedicated service boundary, related route/startup tests | Explicit action only; no scheduler and zero calls on import/startup/status/configuration |
| D2 commercial gate | New narrowly scoped gate module, `app/integrations/openai_analysis.py`, composition and fake-client tests | Separate from `AISettings.enabled`; check before each commercial attempt and internal retry; OFF by default |
| D3 local status | `app/web/routes.py`, `app/web/templates/status.html`, `test/test_status.py`, possibly credential-presence adapter | Local-only; non-sensitive enabled/provider/model/endpoint class/presence/smoke/gate state; no OpenAI request |
| D4 credential CLI | New local CLI module, `app/security/credentials.py` or a separate keyring operator adapter, related tests | Non-echoing input; set/replace/status/delete; no key in argv, TOML, Git, SQLite, logs or browser |
| D5 synthetic smoke CLI | New explicit CLI module and isolated fake-client tests | Literal synthetic input only; no production DB, IMAP, CRM, Calendar, or default-pytest live call |
| D6 disable/recovery | Gate, adapter retry boundary, run-recovery repository/service, tests | No new call/retry after disable; already-sent request may finish; interrupted reservations reconciled safely |
| D7 minimal telemetry | Existing bounded `AnalysisRun`/audit mechanisms if sufficient; no new metrics model | No bodies, secrets, raw errors, headers or new telemetry-only migration |
| D8 process-local authorization | New gate module and composition tests | Default OFF and revocable; restart resets OFF; no authorization persistence or general-purpose synthetic bypass |
| D9 protected manual action | Existing localhost route, local session/CSRF/origin safeguards and security tests | No POST before controls exist; no CLI commercial trigger |
| D10 controlled startup recovery | `AnalysisRun` repository/startup recovery, **after a separately approved ownership datum or equivalent invariant** | Must not convert an active request; atomic/idempotent `failed_retryable/interrupted` only |
| D11 transient smoke status | Process-local smoke state and status tests | No SQLite smoke history, migration or authorization inference from smoke success |
| Approved documentation correction | Separately scoped `docs/architecture.md` edit | Reconcile historical “no provider selected” with Phase 5 OpenAI/`gpt-6-sol`; do not edit in this task |

## 5. Provisional sequence and Scope Lock envelopes

The sequence below follows the approved staging, but file lists remain **conditional proposals**, not exact approved implementation locks. The finalization task requires STOP, rather than invented Scope Locks, when safe orphan detection cannot be proved from existing data. D8, D9 and D11 settle the earlier choices; D10's recovery trigger is fixed at startup, but its ownership test is not implementable from the present row.

| Subphase | Proposed IN SCOPE | OUT OF SCOPE / restriction | Planned validation |
| --- | --- | --- | --- |
| 6A1 — gate and adapter check | New gate module, `app/integrations/openai_analysis.py`, gate/adapter tests | No route, CLI, status, real key, provider call or commercial authorization | `python -m pytest test/test_openai_analysis.py` then `python -m pytest`; check disabled-before-secret and disable-before-retry |
| 6A2 — composition foundation | `app/main.py`, `test/test_startup.py`; optionally a small dedicated composition module only if separately scoped | No automatic trigger, scheduler, provider call on import/startup or `AISettings.enabled` alone | `python -m pytest test/test_startup.py test/test_openai_analysis.py` then `python -m pytest` |
| 6B — status and safe presence | `app/web/routes.py`, `app/web/templates/status.html`, `test/test_status.py`; credential boundary/test only if needed and explicitly scoped | No secret value, call to OpenAI, public diagnostics or activation toggle | `python -m pytest test/test_status.py test/test_credentials.py` then `python -m pytest` |
| 6C — interactive keyring CLI | New local credential CLI, credential adapter if required, CLI/credential tests | No new secret store, key in argv/env/output/logs, or browser provisioning | `python -m pytest test/test_credentials.py` plus new CLI test, then `python -m pytest` |
| 6D — synthetic smoke tooling | Dedicated explicit smoke CLI and its offline fake-client tests | No real call in default tests; no production DB/IMAP/CRM/Calendar access; no commercial input | Smoke CLI fake-client tests plus `test/test_openai_analysis.py`, then `python -m pytest` |
| 6E1 — protected manual trigger foundation | `app/web/routes.py`, `app/security/session.py`, composition/template and route/security tests, exact split deferred | Keep POST unavailable until both controls **and 6E2 recovery** are proved; no automatic analysis | Focal route/session/security tests with fake provider, then `python -m pytest` |
| 6E2 — controlled startup recovery | Repository/model/migration/startup and isolated SQLite tests **only after ownership decision** | No age-only or all-reserved sweep; no conversion of a live request | Focal repository/migration/startup recovery tests, then `python -m pytest` |
| 6E3 — rollback/security regression | Gate, adapter, status and security tests, exact split deferred | No new provider call or retry after disable; in-flight may finish | Focal gate/adapter/security tests, then `python -m pytest` |
| 6F — optional one-shot live synthetic smoke | Exact separately approved command and run record; no implicit code change | Never default pytest; no commercial data; no claim of EU residency/ZDR | One explicitly approved synthetic call, bounded output and spend; record non-sensitive outcome |
| 6G — optional commercial-data activation | Exact separate authorization/processing-mode task after new decision | Blocked under current no-EU/no-Global-approval state | Prove gate, credential, smoke, rollback and legal/data controls before any commercial call |
| Documentation-only correction | `docs/architecture.md` alone under its own Scope Lock | No behavior/config/code change | Review exact diff and alignment with Phase 5 decisions; no tests needed for prose-only edit |

The preferred order is 6A1 → 6A2 → 6B → 6C → 6D → 6E1 → 6E2 → 6E3, with the documentation correction separately scoped; 6F and 6G require new explicit approvals and never merge into one task. The blocked 6E2 must not be bypassed to expose a commercial-analysis trigger. Exact per-subphase Scope Locks are withheld because this whole-plan finalization is stopped on D10's unproved ownership rule; otherwise they would falsely imply an executable approved plan.

## 6. Required behavior and acceptance constraints for the eventual plan

1. Under D8, the runtime gate is process-local, revocable, independent of `AISettings.enabled`, and commercial OFF at creation/restart. The provider-facing path must recheck immediately before the first commercial request and before any retry, after any delay. A separate synthetic-only CLI path cannot accept arbitrary commercial input as a bypass. A provider request already transmitted may finish; no recall or hard-kill claim is permitted.
2. Normal import, `create_app()`, status render, and normal pytest must make zero provider/network calls. Simply enabling provider settings, provisioning a key, or passing smoke cannot authorize commercial content.
3. Under D9, manual analysis must be a concrete localhost web/UI POST requiring a valid local session, CSRF token, and localhost origin/host validation before reaching `analyze_email_in_thread()`. Reservation, replay, stale-source validation, provenance, and no external-action authority remain unchanged. The POST cannot be exposed while startup recovery or these controls remain unproved.
4. Under D11, status may show only `enabled`, configured provider/model, endpoint class (`global`/`eu`/`unknown`), credential `present`/`missing`/`unavailable`, **current-process-only** smoke `pending`/`passed`/`failed`, and commercial gate `blocked`/`authorized`. Smoke status resets on restart and never authorizes commercial use. Credential presence is not validity; EU-looking host and smoke success do not prove EU processing. `/health` remains provider-network-free.
5. Credential CLI must accept set/replace via a non-echoing interactive prompt, perform status without printing the value, and delete/rotate through Windows Credential Manager under configured `credential_service`/`credential_account`. It must avoid secret-bearing argv, environment, files, repr, exceptions and logs; fake-keyring tests must cover failures.
6. Synthetic smoke CLI must construct all input from fixed synthetic literals and never open production SQLite or import IMAP/CRM/Calendar clients. It should invoke the existing Responses adapter/strict decoder through a separately authorized synthetic-only path, check `store=false`, no tools/functions, bounded timeout/retry, and emit only bounded result metadata. A successful call is a transport/schema check, not commercial-data consent.
7. Rollback must be one-step and fail closed: prevent all new calls and retries; already-sent requests may finish. Under D10, orphaned `reserved` rows must be recovered atomically/idempotently at controlled startup **only when a safe owner/liveness proof exists**. No provider raw text or commercial content may be logged to prove this.
8. No authorization, smoke-history or provider-telemetry table/migration is needed for D8/D11. Recovery is different: the missing reservation-ownership datum is not telemetry and would require a separately approved data-model change before 6E2 can be specified.

## 7. Dependencies, risks and out-of-scope discoveries

Internal dependencies are the Phase 5 projection/adapter, `AIService`, Phase 4 run repository and data-selection contracts, localhost FastAPI routes, settings, keyring abstraction, and existing CSRF helpers. Automated validation must use fake clients, fake keyring, and synthetic isolated SQLite. No new third-party package is identified by planning; if a session or operator design requires one, STOP for approval.

Main risks: accidental commercial disclosure from startup/status/retry; unauthorized Global processing; secret exposure during provisioning/status; status falsely presenting credential presence as validity or endpoint class as residency; a browser-origin forged manual action; stuck `reserved` runs after interruption; a rollback race with an in-flight request; prompt injection; and AI proposals being mistaken for approved external actions. Default tests must remain entirely offline. No code, migration, configuration, credential, provider, IMAP, Calendar or CRM mutation is part of this planning task.

**OUT-OF-SCOPE DISCOVERY:** `docs/architecture.md` still says no provider/model was selected despite approved Phase 5. The correction is approved only as a separately scoped documentation task; this file does not edit it.

## 8. STOP — existing data cannot prove orphaned `reserved` status

The decisive comparison is between two states that are indistinguishable to the proposed startup sweep:

| State at new process startup | Durable row | Process-local facts available to the new process |
| --- | --- | --- |
| Previous provider call crashed; its reservation is orphaned | `status='reserved'`, `failure_code=NULL`, `completed_at=NULL`, an `updated_at` value | No recorded owner or heartbeat |
| Another application process still has a live provider call after its reservation transaction committed | The **same** row shape, and possibly the same `updated_at` age | The new process sees no owner identity; the adapter's thread lock belongs only to the other process |

`AnalysisRun` has run identity, digest, versions, mode, status and `updated_at`, but no process/instance owner, lease, heartbeat or fencing generation (`app/persistence/models.py`). `AnalysisRepository.reserve_run()` commits `reserved`; `analyze_email_in_thread()` closes the session before the provider call (`app/services/email_analysis.py`). There is no SQLite write lock across that call. `_REQUEST_LOCK` is process-local, and `app/main.py` contains no enforced singleton lock. A second process can start with the same local database. The 60-second adapter budget is explicitly soft, so neither `updated_at` age nor a 60-second threshold proves that the request has stopped. The existing `failed_retryable/interrupted` transition permits the *result* but supplies no safe predicate for choosing rows.

Therefore a rule that converts every `reserved` row, or every row older than a chosen threshold, could mark a genuinely active request interrupted. Its still-running owner might then attempt completion; even if compare-and-swap prevents final persistence, an already-sent provider call and duplicate retries could have occurred. A local startup scan or SQLite `BEGIN IMMEDIATE` alone does not establish liveness during the external call. **Safe orphan detection is not demonstrable from the current row plus current process-local facts.** The exact 6E2 Scope Lock and a `READY FOR APPROVAL` whole-Phase-6 plan cannot be asserted.

### Minimum additional decision/change

Approve a durable **reservation owner identity** on `AnalysisRun`, written atomically when `status='reserved'` is created. The minimum useful datum is an owner identity that can be checked against the local OS without PID-reuse ambiguity—for example one bounded field encoding the owning process ID **and its OS creation time**. A PID alone, random UUID alone, `updated_at` alone, or a soft timeout is insufficient. The model, constraints, migration/backfill and repository contract would need an explicit data-model task. At controlled startup, recovery may convert only rows whose recorded owner is positively known dead, in one conditional `reserved → failed_retryable/interrupted` transaction; an owner that is alive, uncheckable, or absent must remain `reserved` and block that target. Legacy ownerless reservations require a separately approved manual/quiescent recovery rule; do not silently classify them as orphaned. The liveness query and conditional update must be tested for races and idempotency. This is a proposed minimal **decision**, not approval to add the column.

An alternative is to approve and enforce an exclusive OS-level single-instance lock held throughout all provider calls, plus a controlled upgrade/quiescence rule for pre-lock processes. That is a different architecture and is not present today. It likewise cannot be assumed as an existing process-local fact to turn this plan READY. The user must choose/approve the ownership guarantee; the per-run owner datum above is the smallest concrete data-model option identified by this review.

## 9. Result and approval gate

**BLOCKED — STOP.** D8, D9 and D11 have been incorporated and no longer need a new choice in this plan. D10's startup recovery cannot safely distinguish orphaned from live reservations with the existing schema and process-local facts. No implementation, migration, live smoke or commercial activation is authorized. Resolve the reservation-ownership decision first, then finalize exact per-subphase Scope Locks and focal/full-suite tests. Any later `READY FOR APPROVAL` plan still requires separate approval for each implementation subphase, a separately approved synthetic live call, and a still later processing-mode decision before commercial-data activation.
