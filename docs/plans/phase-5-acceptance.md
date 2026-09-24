# Phase 5 Acceptance — Real AI Provider Integration

**Status:** ACCEPTED
**Date:** 2026-09-24
**Branch:** codex-work

## Scope accepted

Phase 5 delivered the provider-facing OpenAI integration boundary while preserving the existing Phase 4 orchestration and safety model.

Accepted subphases:

- Phase 5A — provider-neutral remote projection and strict response schema.
- Phase 5B — non-secret AI configuration and credential references.
- Phase 5C — concrete synchronous OpenAI Responses API adapter with bounded retries, soft overall deadline and offline fake-client tests.
- Phase 5D — service integration and security regression tests using the concrete adapter, entirely offline.

## Final implementation state

The repository now contains:

- minimized provider projection with ephemeral aliases;
- strict JSON Schema response contract;
- local alias-to-source evidence reconstruction;
- bounded request/response sizes;
- sensitive-content fail-closed preflight;
- OpenAI Responses API adapter;
- configured default model `gpt-6-sol`;
- official OpenAI Python SDK dependency;
- SDK implicit retries disabled;
- adapter-owned maximum one retry for approved transient classes;
- monotonic 60-second soft overall deadline with per-attempt timeout bounded by remaining budget;
- single concurrent remote analysis request per process;
- bounded provider errors with no raw provider text or secret leakage;
- no model tools/functions/web/browser/computer/code-execution capability;
- no production route/scheduler/startup activation;
- no automatic external action authority.

## Data-processing gate

Real commercial-data activation remains blocked.

The currently configured API project does not expose an EU residency option. Therefore:

- Phase 5 acceptance does not authorize transmission of commercial data to a Global project;
- no EU residency/ZDR claim is made;
- AI remains disabled for real use unless a later explicitly approved activation task is completed;
- future activation requires either:
  1. verified EU eligibility/processing for the actual account/project, or
  2. a separate explicit user decision accepting Global processing.

## Validation

Phase 5C validation:

- focal: 117 passed, 1 warning;
- full suite: 520 passed, 8 warnings.

Phase 5D final validation:

- focal:
  `python -m pytest test/test_email_analysis_service.py test/test_security.py test/test_openai_analysis.py`
  → **76 passed, 1 warning**
- full:
  `python -m pytest`
  → **532 passed, 8 warnings**

Warnings are pre-existing/non-blocking:
- Starlette TestClient/httpx deprecation;
- SQLite datetime adapter deprecations under Python 3.13.

## Acceptance conclusion

Phase 5 is ACCEPTED.

No live smoke, real credential use, real provider call, production composition or commercial-data activation is included in this acceptance.

Any activation must be handled by a new Scope Lock and explicit approval.
