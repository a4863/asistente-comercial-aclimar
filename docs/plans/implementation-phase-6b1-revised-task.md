# Phase 6B1 Revised Implementation Task — Process-Local Commercial Activation Gate

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Supersedes:** docs/plans/implementation-phase-6b1-task.md
**Depends on:** Phase 6A1–6A3 ACCEPTED
**Plan:** docs/plans/implementation-phase-6-plan.md
**Decisions:** D2, D6, D8, D12, D13

## Reason for revision

The initial 6B1 Scope Lock omitted two existing integration/security test files that construct `OpenAIAnalysis` directly and expect fake provider calls.

Those tests must be updated to supply explicit fake operational ownership and commercial authorization capability.

Do **not** add a fake-client bypass, test-only production bypass or implicit authorization path.

## Objective

Implement a process-local, revocable commercial activation gate and enforce it at the OpenAI adapter boundary before the initial provider attempt and before any retry.

This task does **not** authorize commercial-data processing.

The gate must default OFF and remain OFF unless explicitly manipulated by future approved local control code.

## Exact Scope Lock

Create only:

1. app/security/activation.py
2. test/test_activation.py

Modify only:

3. app/integrations/openai_analysis.py
4. test/test_openai_analysis.py
5. test/test_email_analysis_service.py
6. test/test_security.py

No other tracked file may change.

## Required behavior

### CommercialActivationGate

Implement a small process-local object with:

- default state OFF;
- explicit enable/disable API;
- revocable state;
- no persistence;
- restart/new instance naturally resets OFF;
- thread-safe reads/writes;
- no provider/model/credential knowledge beyond authorization state;
- no secret or commercial-data storage.

### Ownership capability

The adapter must receive an explicit operational-ownership capability/predicate.

Production semantics:
- no ownership capability or false ownership => fail closed;
- do not infer ownership from AI enabled state, fake client presence, process identity or environment;
- no test/fake bypass exists in production code.

Tests may use explicit fake ownership objects/predicates that satisfy the same interface as production ownership.

### Adapter enforcement

Update `OpenAIAnalysis` so that commercial analysis requires:

1. `AISettings.enabled=True`;
2. valid operational ownership proof;
3. commercial gate currently ON.

Ordering:
- technical disabled check before secret lookup;
- ownership/gate check before credential lookup/client creation/provider request;
- recheck ownership + gate immediately before initial provider attempt;
- recheck ownership + gate before every retry, after any retry delay;
- disabling gate after attempt 1 prevents retry;
- losing ownership after attempt 1 prevents retry;
- already-sent attempt may finish; no hard cancellation.

No route/UI-only enforcement.

### Synthetic boundary

If a synthetic-only capability is defined for future 6D:
- keep it separate from commercial authorization;
- it must not be a general capability that accepts arbitrary commercial `AnalysisInput`;
- do not implement live smoke in this task.

### Existing integration/security tests

Update `test/test_email_analysis_service.py` and `test/test_security.py` only as needed to:

- pass explicit fake ownership and explicit enabled commercial gate when a fake provider call is intentionally expected;
- preserve disabled/no-body/sensitive-content/error/minimization/security assertions;
- add/assert fail-closed behavior where appropriate;
- never weaken production gate semantics;
- never use monkeypatches that bypass the gate inside production code.

## Tests

Prove at minimum:

1. gate defaults OFF;
2. enable turns it ON;
3. disable revokes future attempts;
4. new gate instance starts OFF;
5. thread-safe concurrent read/write behavior;
6. technical AI disabled fails before credential lookup;
7. no ownership fails before credential lookup;
8. ownership false fails before credential lookup;
9. ownership true + gate OFF fails before credential lookup;
10. ownership true + gate ON reaches fake client;
11. gate disabled between first attempt and retry => no retry;
12. ownership lost between first attempt and retry => no retry;
13. no retry bypass after delay;
14. integration through `analyze_email_in_thread` still works with explicit fake capability;
15. replay/no-body behavior still avoids unnecessary provider access;
16. sensitive preflight still happens safely;
17. prompt-injection/minimized-payload/no-tools assertions remain intact;
18. provider raw errors and credentials remain bounded;
19. no real network/keyring access;
20. default commercial authorization remains OFF.

## Restrictions

Do not modify:
- app/main.py
- startup/recovery
- routes/templates
- config schema
- credentials implementation
- persistence/models/repositories
- migrations
- pyproject
- docs other than this task

Do not:
- enable commercial processing by default;
- add UI/control to turn gate ON;
- create any fake/test bypass in production;
- call OpenAI;
- read real keyring;
- add dependency;
- add scheduler/background work.

## Validation

Run:

python -m pytest test/test_activation.py test/test_openai_analysis.py test/test_email_analysis_service.py test/test_security.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/security/activation.py
- test/test_activation.py
- app/integrations/openai_analysis.py
- test/test_openai_analysis.py
- test/test_email_analysis_service.py
- test/test_security.py

## STOP conditions

STOP if:
- another production file is required;
- another test file constructs `OpenAIAnalysis` and cannot remain valid without adaptation;
- adapter integration requires app/main.py or route changes;
- synthetic boundary cannot remain separate from commercial authorization;
- a new dependency/persistence layer is needed;
- retry recheck cannot be enforced inside the adapter without broader refactor.

## Completion

Commit:

Implement revised phase 6B1 commercial activation gate

Push only origin/codex-work.
