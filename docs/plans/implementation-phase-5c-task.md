# Phase 5C Implementation Task — OpenAI Analysis Adapter

**Status:** Approved for Implement
**Date:** 2026-09-24
**Plan:** docs/plans/implementation-phase-5-plan.md
**Decisions:** docs/plans/phase-5-ai-provider-decisions.md
**Prerequisites:** Phase 5A ACCEPTED; Phase 5B ACCEPTED

## Objective

Implement the concrete OpenAI adapter behind the existing synchronous AIService boundary using the official OpenAI Python SDK and the Responses API, while keeping all automated tests fully offline.

This task must not perform any real OpenAI request and must not activate AI for commercial data.

## Exact Scope Lock

Create/modify only:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. pyproject.toml

No other tracked file may change.

## External verification gate

Before writing provider-specific code, verify against current official OpenAI API/SDK documentation:

- current official Python SDK package name and compatible version;
- Responses API request shape;
- strict Structured Outputs / JSON Schema request shape;
- selected model identifier `gpt-6-sol`;
- output token parameter name;
- refusal/incomplete response representation;
- exception/status classes needed for retry classification;
- SDK retry defaults and how to disable them;
- timeout behavior and whether SDK-level timeout includes retries.

If any of these cannot be verified unambiguously, STOP before implementation.

Do not silently substitute:
- another model;
- Chat Completions for Responses;
- free-form JSON;
- tool/function calling;
- Global activation;
- any undocumented SDK behavior.

## Dependency

Add the official OpenAI Python SDK to pyproject.toml using a reviewed version strategy compatible with the repository's packaging approach.

The adapter must not rely on undeclared transitive behavior.

Automated tests must run with no network.

## Adapter contract

Implement a concrete synchronous adapter compatible with:

AIService.analyze(AnalysisInput) -> AnalysisCandidates

The adapter may depend on:
- AISettings;
- CredentialStore;
- Phase 5A project_analysis_input / response_schema / decode_analysis_response;
- official OpenAI SDK client types only where necessary.

It must not depend on:
- SQLAlchemy Session/Engine;
- repositories;
- persistence models;
- FastAPI;
- IMAP adapter;
- CRM/Calendar adapters;
- action execution code.

## Provider request construction

Use:
- Responses API;
- configured model, default `gpt-6-sol`;
- strict Structured Outputs JSON Schema based on Phase 5A response_schema();
- static trusted instruction text;
- minimized Phase 5A remote projection as untrusted input/data;
- no tools;
- no functions;
- no web search;
- no code execution;
- no computer/browser capability;
- no streaming.

Email/source text must never be interpolated into trusted instructions.

Do not serialize AnalysisInput directly.

Do not send:
- source_record_id;
- account_scope;
- input/original/span digests;
- run/conversation IDs;
- IMAP UIDs/folders;
- attachment content/metadata;
- CRM/Calendar context;
- logs/audit/config;
- credentials.

## Credentials

Retrieve API secret only through injected CredentialStore using AISettings.credential_service/account immediately before a real client call path.

If:
- AI disabled;
- credential missing;
- credential lookup fails;

then fail with a bounded, value-free local error.

Never include API key in:
- repr;
- exceptions;
- logs;
- result objects;
- tests;
- configuration.

Do not create/set a credential in this task.

## Timeout, retry and concurrency

Approved behavior:
- no streaming;
- one concurrent remote request per process;
- timeout budget: 60 seconds overall for the adapter operation;
- maximum 2 total attempts (initial + one retry);
- explicitly disable SDK automatic retries so the adapter owns retry behavior;
- retry only verified transient classes:
  - connection failure;
  - timeout;
  - rate-limit response;
  - server-side 5xx response.
- do not retry:
  - auth failure;
  - quota/billing failure;
  - provider refusal;
  - policy rejection;
  - malformed/incomplete output;
  - schema/decoder failure;
  - local validation/sensitive gate failure.

Any retry delay must remain bounded inside the 60-second overall budget.

If the SDK cannot reliably enforce this model, STOP.

## Error surface

Define bounded local exception/error codes suitable for existing Phase 4 provider_failure handling.

No raw SDK/provider exception string may escape.

No provider request/response body may appear in exception text.

No secret-bearing headers may appear in logs/errors.

At minimum distinguish internally where useful:
- disabled;
- credential_missing;
- provider_transient_exhausted;
- provider_auth;
- provider_quota;
- provider_refusal;
- provider_incomplete;
- invalid_output;
- timeout;
- busy/concurrency if needed.

These classifications must not require Phase 4 persistence changes.

## Response handling

Use only the provider's structured response payload.

Fail closed on:
- refusal;
- incomplete/truncated output;
- absent structured payload;
- malformed JSON/object shape;
- schema mismatch;
- oversize response;
- decoder error;
- unsupported enum/date/evidence/support semantics.

Pass the parsed JSON-shaped object to Phase 5A decode_analysis_response().

Return only immutable AnalysisCandidates.

Never repair or coerce provider output.

## Concurrency

Enforce a single active remote analysis request per process.

Implementation may use a process-local lock/semaphore.

Do not introduce global background workers or scheduler behavior.

Tests must prove that a second concurrent call cannot create a second provider request.

## Offline test strategy

test/test_openai_analysis.py must use only:
- synthetic AnalysisInput;
- fake CredentialStore;
- fake/injected SDK client or factory;
- fake Responses API results/exceptions.

No socket/network.
No real API key.
No environment-based credential lookup.
No live OpenAI call.

Tests must verify at least:

1. disabled adapter performs zero credential/client calls;
2. missing credential fails bounded;
3. secret never appears in repr/error;
4. exact configured model passed;
5. Responses API path used;
6. strict schema passed;
7. no tools/functions/stream;
8. Phase 5A minimized projection used;
9. internal IDs/digests absent from provider request;
10. target/prior content stays in untrusted input channel;
11. output token ceiling passed correctly;
12. timeout configured;
13. SDK implicit retries disabled;
14. valid structured output returns AnalysisCandidates;
15. refusal fails without retry;
16. incomplete/truncated output fails without retry;
17. malformed structured output fails without retry;
18. auth failure no retry;
19. quota/billing failure no retry;
20. transient connection failure retries once;
21. transient timeout retries once if budget permits;
22. rate limit retries once;
23. 5xx retries once;
24. second transient failure stops after total 2 attempts;
25. concurrency cap prevents second provider request;
26. decoder error remains bounded and value-free;
27. request/response/secret not logged;
28. zero real HTTP calls.

## Restrictions

- no app/services/email_analysis.py change;
- no app/config.py change;
- no app/security/credentials.py change;
- no domain changes;
- no repositories/persistence/models/migrations;
- no routes/UI/scheduler/startup wiring;
- no live smoke;
- no real endpoint call;
- no real credential;
- no activation with commercial data;
- no EU/residency claim;
- no cache/untracked inspection.

## Validation

Run:

python -m pytest test/test_openai_analysis.py test/test_ai_schema.py test/test_config.py test/test_credentials.py

Then:

python -m pytest

Tracked diff must contain exactly:
- app/integrations/openai_analysis.py
- test/test_openai_analysis.py
- pyproject.toml

## STOP conditions

STOP if:
- official SDK/model/Responses/Structured Outputs behavior cannot be verified;
- another production file is required;
- existing AIService contract must change;
- existing Phase 4 DTOs must change;
- safe retry/timeout control cannot be implemented;
- SDK implicit retries cannot be disabled;
- testing requires a real API call;
- production activation appears necessary.

## Completion

Commit:

Implement phase 5C OpenAI analysis adapter

Push only origin/codex-work.
