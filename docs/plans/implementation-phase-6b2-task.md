# Phase 6B2 Implementation Task — Local AI Status and Credential Presence

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6A1–6A3 and 6B1 ACCEPTED
**Plan:** docs/plans/implementation-phase-6-plan.md
**Decisions:** D2, D3, D7, D8, D11

## Objective

Extend the existing localhost status surface with bounded, non-sensitive AI operational state and a non-disclosing credential-presence check.

This task must make **zero OpenAI/provider calls** and must not add any control that enables commercial authorization.

## Exact Scope Lock

Modify only:

1. app/main.py
2. app/web/routes.py
3. app/web/templates/status.html
4. app/security/credentials.py
5. test/test_status.py
6. test/test_credentials.py

No other tracked file may change.

## Required status fields

The existing local status page may display only bounded non-sensitive AI state:

- technical AI enabled/disabled;
- configured provider;
- configured model;
- endpoint class:
  - `global`
  - `eu`
  - `unknown`
- credential status:
  - `present`
  - `missing`
  - `unavailable`
- commercial authorization:
  - `blocked`
  - `authorized`
- operational ownership/readiness state, if needed to avoid misleading UI;
- current-process smoke state only if an in-memory value already exists; otherwise `pending`/not-run is sufficient.

Do not expose:
- credential value;
- credential length/prefix/suffix;
- raw keyring exception;
- raw Win32 handle;
- request/response content;
- email content;
- provider raw error;
- commercial source identifiers.

## Credential presence boundary

Extend the credential abstraction with the smallest safe presence API if required.

Requirements:
- presence check may read Windows Credential Manager/keyring through the existing abstraction;
- return only bounded presence state;
- never return the secret;
- distinguish missing from unavailable/error without exposing raw exception text;
- no provider/client creation;
- no validation call to OpenAI;
- no write/delete behavior in this phase.

If existing `get_secret()` is internally reused, ensure status/routes never receive the returned secret value.

Tests must use fake keyring/credential stores only.

## Endpoint classification

Classify configured AI base URL locally:

- `https://api.openai.com/v1` -> `global`
- `https://eu.api.openai.com/v1` -> `eu`
- any other/None -> `unknown`

This label is only endpoint classification.

The UI must not claim:
- EU residency;
- ZDR;
- retention guarantees;
- legal/compliance approval.

## Commercial gate visibility

The status page may read the process-local commercial gate state.

It must not provide a button, POST, query parameter or route that changes the gate.

Gate remains OFF by default and resets OFF on restart.

## Composition

If `app/main.py` needs to place the process-local gate and/or safe credential-status dependency in `app.state`, do so without:

- enabling the gate;
- constructing OpenAIAnalysis;
- creating an OpenAI client;
- reading the credential during module import/create_app;
- provider/network calls.

Prefer lazy status-time credential presence lookup.

Import and inert `create_app()` behavior must remain safe.

## /health

Keep `/health` simple and provider/network-free.

Do not turn it into a detailed credential/AI diagnostics endpoint.

## Tests

Prove at minimum:

1. status shows AI disabled/enabled accurately;
2. provider/model are displayed without secrets;
3. global/eu/unknown endpoint classification is correct;
4. credential present is shown without exposing value;
5. missing credential maps to `missing`;
6. keyring/credential error maps to `unavailable` without raw exception;
7. status lookup never calls OpenAI/provider/network;
8. credential lookup does not happen on module import;
9. credential lookup does not happen merely on inert `create_app()`;
10. commercial gate OFF displays blocked;
11. explicitly enabled test gate displays authorized;
12. status render cannot mutate gate state;
13. operational readiness/ownership is not overstated;
14. `/health` remains unchanged/provider-free;
15. secret never appears in HTML, response body, logs or repr used by status tests;
16. no smoke result is persisted;
17. existing credential tests remain green.

## Restrictions

Do not modify:
- OpenAI adapter
- activation.py
- persistence
- models/migrations
- config schema
- pyproject
- startup recovery logic beyond composition of non-active status dependencies
- any provider/client code
- docs

Do not:
- add a gate enable/disable route;
- call OpenAI;
- validate credential against provider;
- write/delete credentials;
- persist smoke/status telemetry;
- add dependencies.

## Validation

Run:

python -m pytest test/test_status.py test/test_credentials.py test/test_startup.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/main.py
- app/web/routes.py
- app/web/templates/status.html
- app/security/credentials.py
- test/test_status.py
- test/test_credentials.py

## STOP conditions

STOP if:
- a status control would need to mutate the commercial gate;
- safe credential presence requires returning/exposing the secret outside the credential layer;
- another production/test file is required;
- provider validation/network access appears necessary;
- a persistence/model/config migration is required.

## Completion

Commit:

Implement phase 6B2 local AI status

Push only origin/codex-work.
