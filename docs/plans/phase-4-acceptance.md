# Phase 4 Acceptance Record — Email/Thread Analysis and AIService Boundary

**Status:** ACCEPTED
**Date:** 2026-09-24
**Final accepted head:** 5365f849b698658f5b04f39483d05e4b00d08138

## Accepted scope

Phase 4 is accepted end-to-end:

- 4A1 — analysis persistence models
- 4A2 — migration 0007
- 4B — canonical input, evidence, candidate DTOs and typed support references
- 4C — AnalysisRun reservation/replay/versioning/retryable states
- 4D — atomic persistence of evidence, derivations, summaries and operational links
- 4E — AIService protocol, deterministic fake and orchestration
- 4F — adversarial security and end-to-end validation

## Final validation

Focused adversarial/integration suite:

`python -m pytest test/test_email_analysis_service.py test/test_security.py`

Result:
- 36 passed
- 1 warning

Full suite:

`python -m pytest`

Result:
- 425 passed
- 8 warnings

Warnings are known non-blocking deprecations:
- Starlette/httpx TestClient deprecation
- sqlite default datetime adapter deprecation in existing migration test

## Acceptance conclusions

The accepted implementation proves:

- provider call occurs outside write transaction;
- provider receives only bounded canonical AnalysisInput;
- max 6 prior messages and 30,000 disclosed body characters;
- hidden body changes are detected by full-body digest;
- stale inputs become stale_retryable with zero derivation persistence;
- failed provider/output/persistence attempts remain append-only and retryable;
- exact completed replay does not call provider;
- force reanalysis creates a new append-only run and supersedes prior completed run;
- email content is untrusted data and has no execution authority;
- prompt-injection strings cannot approve, send, move, delete, write CRM or modify Calendar;
- no automatic Alert/ActionProposal/ApprovalDecision/ExecutionResult creation from analysis;
- Question/Commitment/Task/NextStep persistence preserves evidence and provenance;
- metadata-only prior messages are supported safely;
- no production changes were required by Phase 4F adversarial testing.

## Phase boundary

No real remote AI provider is implemented yet.
No live CRM query/write is implemented in Phase 4.
No email draft/move/send or Calendar mutation is authorized by analysis.

Any future Phase 5 work must treat this accepted Phase 4 contract as frozen unless a separately approved change explicitly reopens it.
