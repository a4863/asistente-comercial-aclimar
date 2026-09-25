# Phase 6D Implementation Task — Synthetic Smoke CLI and Adapter Path

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6C ACCEPTED
**Decisions:** D5, D8, D11, D12, D13, D15
**Analysis:** docs/plans/phase-6d-smoke-analysis.md

## Objective

Implement an explicit local synthetic smoke path that exercises the real OpenAI adapter mechanics with one fixed non-commercial payload, without enabling or consulting the commercial activation gate and without allowing caller-supplied arbitrary analysis content.

No live provider call is authorized by this task.

## Exact Scope Lock

Create only:

1. app/integrations/ai_smoke_cli.py
2. test/test_ai_smoke_cli.py

Modify only:

3. app/integrations/openai_analysis.py
4. test/test_openai_analysis.py
5. pyproject.toml

No other tracked file may change.

## Adapter design

### Public commercial path

Preserve:
- `OpenAIAnalysis.analyze(AnalysisInput)`;
- technical AI enabled requirement;
- operational ownership requirement;
- commercial gate ON requirement;
- all current 6B1 checks/rechecks.

Do not weaken or special-case the commercial entry point.

### Public synthetic path

Add:

`OpenAIAnalysis.smoke() -> str`

Requirements:
- no parameters that accept content, `AnalysisInput`, source IDs, mode, authorization token or arbitrary data;
- constructs the fixed synthetic input internally;
- returns only bounded success value `passed`;
- second call on the same adapter instance fails with a bounded local code;
- does not inspect, enable or mutate `CommercialActivationGate`;
- requires `AISettings.enabled=True`;
- requires live operational ownership;
- ownership is checked before credential lookup/client creation;
- ownership is rechecked immediately before first provider attempt;
- ownership is rechecked before every retry after any retry delay;
- loss of ownership blocks subsequent attempt.

### Fixed synthetic input

Use one immutable fixed literal only:

Scope:
`synthetic:smoke`

Target source id:
`1`

Contract version:
`1`

Policy version:
`1`

One target message body:
`This is a synthetic test message. Please confirm receipt of a sample catalogue request.`

No:
- prior messages;
- sender/recipient identifiers;
- subject;
- date;
- attachments;
- CRM context;
- Calendar context;
- IMAP identifiers;
- externally supplied text.

Compute necessary digests locally.

The fixed projection/request content must be snapshot-tested.

### Shared private execution path

Refactor only as much as necessary so both `analyze()` and `smoke()` use one private provider execution implementation for:

- endpoint/config validation;
- projection;
- request byte limits;
- credential lookup;
- client construction;
- one-process request lock;
- strict Responses schema;
- decoder;
- timeout/deadline;
- bounded retry;
- provider error mapping;
- `store=False`;
- no tools/functions/streaming.

Do not duplicate provider logic in the CLI.

Do not introduce a public `synthetic=True`/mode flag.

## CLI

Register:

`asistente-aclimar-ai-smoke`

The command:
- accepts no data/request argument;
- may support `--help` only if needed;
- loads normal settings;
- requires technical AI enabled;
- creates/uses the existing configured credential reference through the adapter;
- acquires the actual `SingleInstanceLock(settings.database_url)`;
- constructs `OpenAIAnalysis` with that actual lock as ownership proof;
- invokes `smoke()` exactly once;
- prints only bounded result/error code;
- releases the lock on all exits.

The CLI must not:
- instantiate or enable a commercial gate;
- call `analyze()`;
- query/open SQLite through SQLAlchemy;
- import/select IMAP/CRM/Calendar/notes/commercial data;
- accept payload text via argv, stdin, environment or file;
- persist smoke status;
- print key, request body, response body, path, handle, raw provider error or commercial identifiers.

Using the lock primitive may create/open its sidecar as designed; that is not commercial database access.

## Live-call prohibition

All pytest validation must use fakes.

Do not run the new CLI against real OpenAI in this task.

Real live smoke remains Phase 6F and requires separate explicit approval.

## Tests

### Adapter tests

Prove at minimum:

1. commercial `analyze()` still fails without gate;
2. `smoke()` signature accepts no arbitrary payload/input;
3. fixed synthetic payload exactly matches the approved literal/projection;
4. caller material cannot enter smoke request;
5. smoke ignores commercial gate state and never calls enable/disable;
6. technical AI disabled -> zero credential/client/provider calls;
7. no ownership -> zero credential/client/provider calls;
8. ownership loss before first attempt -> zero provider call;
9. ownership loss during retry delay -> no second attempt;
10. success uses strict schema, decoder, allowed endpoint/model, configured credential, `store=False`, no tools/functions, bounded timeout/retry;
11. second smoke call on same adapter instance fails bounded;
12. raw provider errors/secrets/request/response bodies are not surfaced;
13. existing commercial adapter tests remain green.

### CLI tests

Use fake settings, fake keyring/credentials, fake lock and fake client only.

Prove at minimum:

14. CLI accepts no payload/data argument;
15. help text does not suggest arbitrary payload input;
16. acquires the configured DB-identity lock before smoke;
17. second-owner/lock failure prevents credential/provider use;
18. lock is released on success and every failure;
19. invokes `smoke()` exactly once;
20. commercial gate is never enabled or mutated;
21. no SQLAlchemy DB session/repository/source selector/IMAP/CRM/Calendar access occurs;
22. stdout/stderr contain only bounded status/error codes;
23. no real network/OpenAI call occurs in tests;
24. no smoke result is persisted.

## Restrictions

Do not modify:
- app/security/activation.py
- app/main.py
- routes/templates
- credentials implementation
- config schema/defaults
- persistence/models/repositories/database
- migrations
- domain selectors/services
- IMAP/CRM/Calendar integrations
- docs

Do not:
- call OpenAI live;
- enable commercial gate;
- add dependency;
- add persistence;
- add route/UI trigger;
- create public synthetic flags/tokens accepting arbitrary input.

## Validation

Run:

python -m pytest test/test_ai_smoke_cli.py test/test_openai_analysis.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/integrations/ai_smoke_cli.py
- test/test_ai_smoke_cli.py
- app/integrations/openai_analysis.py
- test/test_openai_analysis.py
- pyproject.toml

## STOP conditions

STOP if:
- another production/test file is required;
- smoke cannot remain structurally no-argument/fixed-payload;
- safe reuse requires weakening `analyze()` authorization;
- CLI requires persistence or commercial DB reads;
- commercial gate mutation becomes necessary;
- a live provider call seems necessary for implementation validation.

## Completion

Commit:

Implement phase 6D synthetic smoke CLI

Push only origin/codex-work.
