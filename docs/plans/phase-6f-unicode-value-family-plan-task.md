# Phase 6F Unicode ValueError Family Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-value-subclass-analysis.md — READY FOR PLAN

## Objective

Produce an implementation-ready plan for exactly one additional bounded family classification:

- `provider_unicode_error_family`

This code is for residual `UnicodeError` subclasses that escape `client.responses.create(**request_kwargs)`.

Do not implement code.
Do not call OpenAI.

## Fixed evidence

The seventh live smoke returned:

`provider_value_subclass_family`

The accepted offline analysis reproduced that family with the exact fixed synthetic request and a no-network 200 JSON response containing invalid UTF-8 bytes.

This reproduction justifies a Unicode-family diagnostic, but does **not** prove that the seventh live failure was caused by invalid UTF-8, nor identify provider/intermediary origin or dispatch stage.

## Exact classification to plan

Preserve all existing branches and precedence unchanged.

Insert exactly one new family branch:

`isinstance(error, UnicodeError)`
-> `provider_unicode_error_family`
-> non-transient

Placement must be:

1. after all existing higher-priority OpenAI/HTTP/OS/exact classifications;
2. after exact `json.JSONDecodeError`;
3. after exact `ValueError`;
4. before the existing residual `isinstance(error, ValueError)` -> `provider_value_subclass_family`.

The existing residual `provider_value_subclass_family` must remain unchanged for:
- Pydantic ValidationError/serialization errors if they escape;
- custom ValueError subclasses;
- every other residual ValueError subclass not caught by the new Unicode branch.

Do not add a Pydantic-specific code.
Do not add a generic "value other" alias.
Do not rename or remove `provider_value_subclass_family`.

## Inheritance expectations

The plan must explicitly preserve:

- exact JSONDecodeError -> provider_response_json_failure
- exact ValueError -> provider_sdk_value_failure
- UnicodeError subclass -> provider_unicode_error_family
- UnicodeDecodeError/UnicodeEncodeError -> provider_unicode_error_family
- idna.IDNAError -> provider_unicode_error_family if it escapes abnormally by inheritance
- Pydantic ValidationError -> provider_value_subclass_family if it escapes unwrapped
- PydanticSerializationError -> provider_value_subclass_family if it escapes
- custom ValueError subclass -> provider_value_subclass_family

Do not claim any of those occurred live.

## Scope Lock expected

Exactly four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

A fifth tracked file is a STOP condition.

## Planning requirements

The plan must define:

1. exact branch location and precedence;
2. exact non-transient semantics;
3. exact CLI allowlist addition;
4. exact no-leak invariants;
5. exact offline/no-network test matrix;
6. pinned-SDK invalid-UTF8 MockTransport reproduction;
7. regression coverage for exact JSON/ValueError and residual ValueError family;
8. exact Scope Lock;
9. rollback;
10. confirmation that request/model/endpoint/schema/payload/timeout/retries/dependencies/gate remain unchanged.

## Offline/no-network test matrix

At minimum plan tests for:

- UnicodeError -> provider_unicode_error_family
- UnicodeDecodeError -> provider_unicode_error_family
- UnicodeEncodeError -> provider_unicode_error_family
- idna.IDNAError synthetic injection -> provider_unicode_error_family
- pinned SDK + explicit MockTransport + invalid UTF-8 application/json bytes -> provider_unicode_error_family
- exact JSONDecodeError -> provider_response_json_failure
- exact ValueError -> provider_sdk_value_failure
- Pydantic ValidationError injection -> provider_value_subclass_family
- PydanticSerializationError injection -> provider_value_subclass_family
- custom ValueError subclass -> provider_value_subclass_family
- existing HTTP/auth/quota/timeout/connection/retry behavior unchanged
- request_schema_failure unchanged
- request kwargs unchanged
- CLI unknown/non-string/unhashable fallback unchanged

All new Unicode-family cases:
- one SDK attempt
- no retry/sleep
- lock released
- no raw injected text in adapter error/stdout/stderr/logs

## Security restrictions

Do not expose or derive:
- concrete exception class name
- module
- MRO
- str/repr/args
- cause/context
- malformed response bytes
- provider body/message
- request payload
- URL/headers
- secrets

Do not:
- call OpenAI;
- execute live smoke;
- access real keyring/API key;
- access operational config/SQLite;
- install/update/downgrade packages;
- add Pydantic production import solely for classification;
- change model/endpoint/schema/payload/timeout/retries;
- add transport instrumentation;
- attribute invalid UTF-8 to provider/intermediary/live seventh smoke.

## STOP conditions

STOP if:
- a fifth file is required;
- a new dependency/import is required;
- raw exception or response content is needed;
- retry semantics must change;
- live access is needed;
- classification requires concrete class reflection.

## Deliverable

Create only:

`docs/plans/phase-6f-unicode-value-family-plan.md`

Include:
- exact mapping;
- exact precedence;
- exact four-file Scope Lock;
- per-file implementation steps;
- offline/no-network tests;
- security invariants;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F Unicode ValueError family

Push only origin/codex-work.
