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
