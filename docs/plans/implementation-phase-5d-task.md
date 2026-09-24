# Phase 5D Implementation Task — Service Integration and Security Regression

**Status:** Approved for Implement
**Date:** 2026-09-24
**Plan:** docs/plans/implementation-phase-5-plan.md
**Decisions:** docs/plans/phase-5-ai-provider-decisions.md
**Prerequisites:** Phase 5A ACCEPTED; Phase 5B ACCEPTED; Phase 5C ACCEPTED

## Objective

Prove, entirely offline, that the concrete OpenAIAnalysis adapter can be injected through the existing Phase 4 AIService seam without changing orchestration, persistence, replay, stale handling, disclosure limits, prompt-injection boundaries or action authority.

This phase is tests only.

## Exact Scope Lock

Modify only:

1. test/test_email_analysis_service.py
2. test/test_security.py

No production file may change.

## Required service-regression coverage

Use:
- OpenAIAnalysis;
- AISettings with enabled=true only inside isolated tests;
- fake CredentialStore;
- fake OpenAI client/factory;
- synthetic SQLite and synthetic email content only.

Prove at least:

1. valid structured OpenAIAnalysis result completes through analyze_email_in_thread();
2. provider adapter failure is mapped by existing service to failed_retryable/provider_failure without leaking provider text;
3. malformed provider output is mapped through the existing bounded failure path;
4. completed replay does not call OpenAIAnalysis/client again;
5. manual replay without force also avoids provider call;
6. force_reanalysis creates a new run and calls provider once more;
7. stale source mutation after provider call still returns stale_retryable/input_changed and persists no derivations from stale output;
8. target with no analyzable body never reaches adapter/client;
9. provider call remains outside the long write transaction;
10. retryable failed run is not reused as completed replay;
11. no production composition/factory/route/scheduler is introduced.

## Required security-regression coverage

Prove at least:

1. prompt-injection text in an email is placed only in untrusted request input/data, never in trusted instructions;
2. minimized provider request excludes:
   - source_record_id;
   - account_scope;
   - input/original/span digests;
   - conversation/run/stable keys;
   - IMAP UID/folder/UIDVALIDITY;
   - raw MIME;
   - attachment content/metadata;
   - CRM/Calendar records;
   - audit/config;
   - credentials;
   - unrelated messages;
3. sensitive-content preflight prevents any fake client call;
4. secret value from fake CredentialStore is absent from logs, exceptions and result repr;
5. quoted-history questions retain existing local quote semantics and do not become current actionable questions;
6. invalid evidence/support returned through the concrete adapter fails closed;
7. no ActionProposal, ApprovalDecision, ExecutionResult or external mutation is created merely because the provider suggests something;
8. no tools/functions/web/browser/computer/code-execution capability appears in the fake provider request;
9. import/startup/default pytest creates zero provider/network calls;
10. the existing 30,000-character / six-prior disclosure boundary still holds when using OpenAIAnalysis.

## Test design constraints

- No real OpenAI call.
- No real API key.
- No environment credential lookup.
- Fake client/factory only.
- Fake keyring/credential store only.
- Synthetic data only.
- No monkeypatch that bypasses the actual OpenAIAnalysis projection/decoder path for tests claiming concrete-adapter coverage.
- Existing FakeAIService tests remain valid and should not be rewritten unnecessarily.

## Restrictions

- no app/ production edits;
- no pyproject changes;
- no dependency changes;
- no config changes;
- no credential implementation changes;
- no domain/repository/persistence/migration changes;
- no route/UI/scheduler/startup wiring;
- no live smoke;
- no activation;
- no Global-processing approval;
- no cache/untracked inspection.

## Validation

Run:

python -m pytest test/test_email_analysis_service.py test/test_security.py test/test_openai_analysis.py

Then:

python -m pytest

Tracked diff must contain exactly:
- test/test_email_analysis_service.py
- test/test_security.py

## STOP conditions

STOP if:
- any production file must change;
- existing analyze_email_in_thread contract must change;
- Phase 4 persistence/domain behavior must change;
- tests require a real provider/network/credential;
- activation/composition wiring appears necessary.

## Completion

Commit:

Validate phase 5 OpenAI analysis security boundary

Push only origin/codex-work.
