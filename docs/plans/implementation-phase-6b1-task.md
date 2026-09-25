# Phase 6B1 Implementation Task — Process-Local Commercial Activation Gate

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6A1–6A3 ACCEPTED
**Plan:** docs/plans/implementation-phase-6-plan.md
**Decisions:** D2, D6, D8, D12, D13

## Objective

Implement a process-local, revocable commercial activation gate and enforce it at the OpenAI adapter boundary before the initial provider attempt and before any retry.

This task does **not** authorize commercial-data processing.

The gate must default OFF and remain OFF unless explicitly manipulated by future approved local UI/control code.

## Exact Scope Lock

Create only:

1. app/security/activation.py
2. test/test_activation.py

Modify only:

3. app/integrations/openai_analysis.py
4. test/test_openai_analysis.py

No other tracked file may change.

## Required behavior

### CommercialActivationGate

Implement a small process-local object with:

- default state OFF;
- explicit enable/disable methods or equivalent bounded API;
- revocable state;
- no persistence;
- restart naturally resets OFF;
- thread-safe behavior suitable for current process-local usage;
- no provider/model/credential knowledge beyond authorization state;
- no secret or commercial data storage.

The object must distinguish:
- commercial authorization capability;
- synthetic-only capability, if the adapter needs one for future smoke tooling.

The synthetic capability must be structurally unable to authorize arbitrary commercial `AnalysisInput`.

### Adapter enforcement

Update `OpenAIAnalysis` so that:

- commercial analysis requires:
  1. `AISettings.enabled=True`;
  2. valid operational single-instance ownership proof;
  3. commercial gate currently ON;
- these checks occur before credential lookup/client creation/provider request;
- ownership + commercial gate are rechecked immediately before the first provider attempt;
- ownership + commercial gate are rechecked again before any retry, after any retry delay;
- disabling the gate after the first failed attempt prevents the retry;
- loss of operational ownership after first attempt prevents retry;
- already-sent first request may finish; no hard cancellation is introduced.

Do not rely solely on route/UI checks.

### Error behavior

Use bounded local error codes/messages only.

Do not expose:
- raw gate internals;
- raw handle value;
- provider body;
- API key;
- request body.

### Synthetic boundary

If a synthetic-only authorization object/path is needed for future 6D smoke:
- define it narrowly in `activation.py`;
- it must not accept arbitrary caller-provided `AnalysisInput` as commercial bypass;
- no live smoke call is implemented in this task.

Prefer the smallest API that lets later smoke tooling prove it is using fixed synthetic input.

## Tests

Add/update offline tests proving at minimum:

1. gate defaults OFF;
2. explicit enable turns it ON;
3. disable revokes immediately for future attempts;
4. restart/new instance starts OFF;
5. gate behavior is thread-safe enough for concurrent read/write;
6. adapter with technical AI disabled fails before credential lookup;
7. adapter with no operational ownership fails before credential lookup;
8. adapter with ownership but commercial gate OFF fails before credential lookup;
9. adapter with ownership + gate ON may proceed to fake client path;
10. gate disabled between attempt 1 and retry -> retry does not occur;
11. ownership lost between attempt 1 and retry -> retry does not occur;
12. no retry path bypasses gate/ownership after delay;
13. provider raw errors/secrets remain bounded;
14. no real network/keyring access;
15. no provider tools/functions introduced;
16. existing request byte/schema/timeout/retry behavior remains intact.

Use fake client, fake credential store, fake ownership object and fake clock only.

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
- docs

Do not:
- enable commercial processing;
- add UI/control to turn gate ON;
- call OpenAI;
- read real keyring;
- add dependency;
- add scheduler/background work.

## Validation

Run:

python -m pytest test/test_activation.py test/test_openai_analysis.py

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

## STOP conditions

STOP if:
- adapter integration requires app/main.py or route changes;
- synthetic boundary cannot be kept separate from commercial authorization;
- a new dependency/persistence layer is needed;
- retry recheck cannot be enforced inside the adapter without broader refactor.

## Completion

Commit:

Implement phase 6B1 commercial activation gate

Push only origin/codex-work.
