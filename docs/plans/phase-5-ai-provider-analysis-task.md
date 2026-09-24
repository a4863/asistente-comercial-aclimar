# Phase 5 Analyze Task — Real AI Provider Integration

**Status:** Approved for Analyze Task
**Date:** 2026-09-24
**Phase 4 accepted baseline:** 5365f849b698658f5b04f39483d05e4b00d08138
**Phase 4 acceptance record:** docs/plans/phase-4-acceptance.md

## Goal

Analyze the smallest safe Phase 5 increment that connects the accepted provider-agnostic `AIService` boundary to one real remote AI provider for email/thread analysis.

This is an ANALYSIS ONLY task.

Do not implement production code.
Do not add dependencies.
Do not modify configuration.
Do not create credentials.
Do not call a real AI provider.
Do not run live-network tests.

## Authoritative inputs

Inspect at minimum:

- AGENTS.md
- docs/functional-spec.md
- docs/architecture.md
- docs/security.md
- docs/testing-strategy.md
- docs/plans/remote-ai-data-policy.md
- docs/plans/technical-stack-decisions.md
- docs/plans/implementation-phase-4-plan.md
- docs/plans/phase-4-acceptance.md
- app/domain/email_analysis.py
- app/services/email_analysis.py
- app/persistence/repositories.py
- app/config.py if present
- app/credentials.py if present
- pyproject.toml
- current tests relevant to config, credentials, analysis and security

Ignore:
- __pycache__
- .pytest_cache
- untracked files outside this task

Use only:
- git status --short --untracked-files=no
- git diff --name-only

Do not inspect Python caches.

## Questions the analysis must answer

### A. Provider boundary

Determine the exact adapter responsibilities needed to implement one real provider while preserving the frozen Phase 4 `AIService` contract.

Identify:
- provider adapter input;
- provider request projection;
- structured-output decoding;
- mapping into existing immutable `AnalysisCandidates`;
- bounded provider errors;
- timeouts;
- retry policy;
- request cancellation/interruption behavior;
- whether streaming is useful or should be prohibited in this phase.

### B. Provider/model decision points

Do not silently select a provider or model.

List the decisions requiring explicit approval, including at least:
- provider;
- model;
- official SDK versus direct HTTPS;
- API endpoint style;
- structured-output mechanism;
- timeout;
- automatic retry count/backoff;
- maximum output/token budget;
- temperature or determinism controls if applicable;
- provider-side retention/training/data-controls assumptions that materially affect security;
- region/data-residency implications if relevant.

If current provider/model facts cannot be established from repository evidence alone, mark them as requiring current external verification rather than guessing.

### C. Credentials

Determine the exact credential flow compatible with:
- Windows Credential Manager;
- existing keyring abstraction;
- no secrets in TOML/Git/SQLite/logs/errors;
- independently revocable AI integration.

Identify:
- proposed logical credential reference;
- retrieval timing;
- failure states for missing/revoked/invalid credential;
- whether any secret could accidentally enter repr/log/exception text;
- tests needed to prove isolation.

### D. Configuration

Identify only non-secret configuration necessary for the real provider.

Examples to assess:
- provider identifier;
- model identifier;
- endpoint/base URL if needed;
- timeout;
- output/token budget;
- retry count;
- enabled/disabled flag.

State which settings belong in TOML and which must remain credentials.

Do not edit configuration in this analysis.

### E. Structured output contract

Compare the provider's likely structured-output capabilities with the existing Phase 4 DTO graph.

Determine:
- whether existing `AnalysisCandidates` can remain unchanged;
- how enums, typed `SupportRef`, evidence spans and exact question text can be represented;
- where validation must occur;
- whether provider JSON schema must be a projection of domain DTOs rather than importing domain models directly;
- how malformed/refusal/truncated output maps to `invalid_output`.

If a domain or persistence change would be required, identify it explicitly as a blocker. Do not make the change.

### F. Data minimization and prompt-injection boundary

Verify the real-provider adapter can preserve the Phase 4 disclosure boundary.

Analyze:
- exact request fields sent remotely;
- system/developer instruction placement versus untrusted email data;
- representation of selected messages so embedded instructions remain data;
- prohibition on credentials, attachments, logs, audit, whole DB, unrelated records;
- no provider tool/function/action capability in this phase;
- no remote browsing, computer-use, code execution or external mutation tools.

### G. Reliability and cost controls

Propose bounded controls suitable for this local MVP:
- request timeout;
- retryable versus non-retryable provider failures;
- rate-limit handling;
- quota/billing failure handling;
- max request size consistent with current 30k-char Phase 4 input;
- max structured response size;
- deterministic/reproducible settings where provider supports them;
- local observability without logging commercial content.

Do not invent exact provider-specific numeric defaults without evidence; mark approval points.

### H. Test strategy

Define tests that can be completed without spending money or exposing production commercial data.

Separate:
1. pure adapter tests with fake HTTP/SDK client;
2. service integration tests with adapter test double;
3. credential/config tests;
4. adversarial/security regression;
5. optional explicit live smoke test, disabled by default and requiring deliberate user action plus non-production/synthetic content.

No default pytest run may call a real remote provider.

### I. Scope proposal

Propose a staged implementation with the smallest useful increments, likely separating:
- provider-neutral request/response schema if needed;
- config/credential wiring;
- concrete provider adapter;
- fake transport tests;
- optional manual live smoke test.

For each proposed subphase, list exact likely files and explicit exclusions.

Aim for 2–4 tracked files per implementation subphase where practical.

## STOP conditions

STOP and request a decision if:
- provider choice is required;
- model choice is required;
- SDK versus direct HTTP materially changes dependencies or architecture;
- structured output cannot map cleanly to existing Phase 4 DTOs;
- a new dependency is required;
- provider data-control terms materially affect the approved security policy;
- any production credential handling is ambiguous;
- any domain/persistence contract would need reopening.

Do not choose among reasonable alternatives.

## Output

Create exactly:

`docs/plans/phase-5-ai-provider-analysis.md`

The analysis must end with one of:

- READY FOR DECISIONS
- READY FOR PLAN
- BLOCKED

If decisions are needed, provide them as numbered items with concise A/B/C alternatives and consequences.

## Scope Lock

This Analyze Task may create/modify only:

- docs/plans/phase-5-ai-provider-analysis.md

No other tracked file.

## Validation

Do not run the full pytest suite for this analysis task.

Permitted:
- read repository files;
- inspect dependency/config declarations;
- use `git diff --name-only`;
- use `git status --short --untracked-files=no`.

## Completion

Commit message:

`Analyze phase 5 real AI provider integration`

Push only to `origin/codex-work`.
