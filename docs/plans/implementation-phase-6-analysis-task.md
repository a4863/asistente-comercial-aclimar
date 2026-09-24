# Phase 6 Analyze Task — Safe AI Activation and Controlled Operations

**Status:** APPROVED FOR ANALYSIS ONLY
**Date:** 2026-09-24
**Depends on:** Phase 5 ACCEPTED
**Branch:** codex-work

## Objective

Analyze and design the safest minimal path from the current disabled Phase 5 OpenAI adapter to controlled operational use.

This phase must separate clearly:

1. application wiring;
2. local status/health observability;
3. credential provisioning;
4. synthetic live smoke;
5. commercial-data activation;
6. rollback/disable procedures.

The analysis must not implement any of them.

## Current frozen baseline

Phase 5 is accepted with:

- provider projection and strict schema;
- OpenAI Responses adapter;
- default model `gpt-6-sol`;
- credentials through existing CredentialStore/keyring abstraction;
- AI disabled by default;
- no production wiring;
- no live provider call;
- no commercial-data activation;
- no authorization to use Global processing for commercial data;
- proposal -> explicit approval -> revalidation -> execution -> audit remains mandatory for irreversible actions.

## Required analysis questions

### A. Composition / wiring

Determine the smallest production composition change required to inject `OpenAIAnalysis` behind the existing `AIService` seam.

Identify:
- exact files that would need modification;
- whether startup/main/app factory currently has a suitable composition root;
- whether any scheduler path would automatically trigger analysis once wired;
- how to keep AI disabled by default;
- how to guarantee that wiring alone does not create provider calls.

STOP if the current architecture would require broad refactoring.

### B. Status / health

Design a minimal local-only status model that can answer, without calling OpenAI:

- AI enabled/disabled;
- provider configured;
- model configured;
- endpoint class: global/eu/unknown;
- credential reference configured;
- credential present/missing, without revealing the secret;
- activation gate status;
- last successful synthetic smoke timestamp/result, if persisted;
- commercial-data activation authorized/not authorized.

Do not design a public internet-facing endpoint.

Determine whether this belongs in:
- existing status route/page;
- a dedicated local-only status object;
- config inspection only.

Prefer the smallest solution.

### C. Credential provisioning

Design the operator workflow for placing the API key in Windows Credential Manager via the existing abstraction.

Requirements:
- key never appears in TOML, shell history if avoidable, Git, SQLite, logs, browser output or screenshots;
- no new secret store;
- no key echo;
- clear replace/rotate/delete procedure;
- verify presence without revealing value.

Determine whether a small local CLI/helper is justified or whether existing CredentialStore APIs are sufficient.

### D. Synthetic live smoke

Design a separate explicitly approved live-smoke task using **synthetic non-commercial text only**.

The smoke must prove:
- credential lookup works;
- DNS/TLS/base URL works;
- selected model is accepted;
- Responses API works;
- strict Structured Outputs schema is accepted;
- response decoder succeeds;
- timeout/retry behavior is bounded;
- no tools/functions are enabled;
- store=false is sent.

The smoke must not:
- read IMAP;
- read CRM;
- read Calendar;
- read production SQLite content;
- send actual commercial/customer data;
- alter any external system.

Determine whether the smoke should be:
- a dedicated script;
- a pytest marked live and excluded by default;
- a local CLI command.

Recommend one and justify.

### E. Commercial-data activation gate

Define the explicit conditions that must all be true before real email content may reach the provider.

At minimum include:
- Phase 6 wiring accepted;
- synthetic live smoke passed;
- credentials configured;
- provider/model config valid;
- user has explicitly approved the applicable data-processing mode;
- if EU processing remains unavailable, commercial-data activation remains blocked unless the user separately and explicitly accepts Global processing;
- rollback switch tested;
- no auto-send or external-action authority is introduced.

Design the gate so normal startup cannot silently bypass it.

### F. Rollback / kill switch

Define:
- one-step local disable procedure;
- expected behavior of already-running jobs/requests;
- what happens to pending analysis runs;
- how to prove zero new provider calls after disable;
- whether restart is required.

Prefer fail-closed behavior.

### G. Observability and audit

Determine the minimal non-sensitive operational telemetry needed:
- success/failure code;
- latency;
- retry count;
- provider/model identifier;
- request/response byte counts;
- timestamp;
- run linkage by local non-secret identifiers if needed.

Explicitly prohibit:
- API key;
- provider raw error body;
- request/response body;
- email content;
- authorization headers.

State whether existing audit/persistence models are sufficient or require a later schema task.

### H. Testing strategy

Define offline tests for activation logic and composition without any real call.

Define the separate live synthetic smoke procedure.

No test should require commercial data.

## Deliverables

Create:

1. `docs/plans/phase-6-activation-analysis.md`

The analysis must include:

- current-state findings;
- exact candidate files for future implementation;
- risks;
- alternatives;
- recommended minimal design;
- explicit STOP/decision points;
- proposed subphases, ideally small and independently reviewable;
- Scope Lock proposal for each subphase;
- validation plan.

## Expected subphase shape

Use this only as a starting point; adjust if analysis supports a better split:

- 6A — composition + disabled-by-default activation gate;
- 6B — local status/credential-presence observability;
- 6C — synthetic live smoke tooling;
- 6D — activation regression/security tests;
- 6E — optional commercial-data activation, only after a separate explicit user decision.

Do not collapse live smoke and commercial-data activation into the same task.

## Hard restrictions

READ-ONLY analysis.

Do not:
- modify production code;
- modify tests;
- modify config;
- install dependencies;
- create scripts;
- call OpenAI;
- read real credentials;
- read IMAP/CRM/Calendar;
- run migrations;
- change main;
- merge to main;
- create implementation commits.

## STOP rule

If two or more reasonable activation architectures remain, present the alternatives and request a decision.

If any path could cause commercial data to be sent merely by starting the app, treat that as a blocker and design a stricter gate.

## Completion

Create only:
- `docs/plans/phase-6-activation-analysis.md`

Commit:

`Analyze phase 6 safe AI activation`

Push only to `origin/codex-work`.
