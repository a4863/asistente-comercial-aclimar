# Phase 6G Protected Commercial Gate UI Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-29

## Accepted implementation

Commit:

`8099f5c31e1f590df81e391a75c6976b48ed73ec`

Exactly four tracked files changed:

1. `app/web/routes.py`
2. `app/web/templates/status.html`
3. `test/test_status.py`
4. `test/test_security.py`

## Accepted behavior

Two protected, parameter-free controls now exist:

- `POST /commercial-activation/enable`
- `POST /commercial-activation/disable`

Both:
- require local Host protection;
- require signed session, CSRF and same-origin Origin;
- require operational readiness and live exclusive ownership;
- require an empty body and no query string;
- mutate only the existing process-local `CommercialActivationGate`;
- do not construct the OpenAI adapter;
- do not read provider credentials;
- do not open DB/session/repository/analysis work;
- return only bounded local status.

Enable is idempotent and returns `authorized`.
Disable is idempotent and returns `blocked`.

## UI

The local status page:
- shows bounded commercial authorization state;
- renders only the state-appropriate enable/disable control;
- states that Global processing is selected;
- states that authorization resets OFF on restart;
- states that disabling prevents new attempts/retries but cannot recall an already-sent request;
- makes no EU-residency or ZDR claim.

The existing manual analysis selector and initial/retry behavior remain unchanged.

## Restart / process boundary

A fresh app/process starts with the commercial gate OFF.
Prior-process session/cookie material cannot authorize the fresh process.

## Validation

User-reported:

- focal tests: **315 passed**
- full suite: **946 passed, 2 skipped, 7 warnings**
- exact four-file Scope Lock
- `git diff --check`: PASS
- no OpenAI call
- no real commercial analysis
- origin commit: `8099f5c31e1f590df81e391a75c6976b48ed73ec`

GitHub review confirms the implementation matches the approved protected-UI plan.

## Result

**ACCEPTED.**

This acceptance authorizes the protected gate mechanism only.

It does NOT authorize the first real commercial provider call. That requires a separately approved controlled rollout after an explicit operational preflight.
