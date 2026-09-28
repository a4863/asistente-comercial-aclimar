# Phase 6F Unknown Non-HTTP Family Classification Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-unknown-non-http-family-plan.md — READY FOR IMPLEMENT

## Objective

Implement the approved six-family bounded refinement of the remaining `provider_non_http_failure` branch.

No live smoke and no OpenAI call are authorized by this task.

## Exact Scope Lock

Modify exactly these four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

No fifth tracked file may change.

## Adapter import boundary

Inside the existing provider-client-construction try that currently lazily imports `openai`:

- lazily import already-installed `httpx2` there as well;
- keep import-time/provider-client-construction failures mapped through the existing `provider_unavailable` boundary;
- do not add a top-level production import;
- do not change client factory arguments;
- do not add or change dependencies.

## Required precedence

Preserve all existing branches and order through exact `RuntimeError`.

After the exact `RuntimeError` branch and before the final generic fallback, add exactly:

1. `isinstance(error, openai.OpenAIError)`
   -> `provider_openai_error_family`
   -> non-transient

2. `isinstance(error, httpx2.RequestError)`
   -> `provider_http_client_error_family`
   -> non-transient

3. `isinstance(error, OSError)`
   -> `provider_os_error_family`
   -> non-transient

4. `isinstance(error, ValueError)`
   -> `provider_value_subclass_family`
   -> non-transient

5. `isinstance(error, (TypeError, RuntimeError, AttributeError, LookupError, AssertionError))`
   -> `provider_python_internal_family`
   -> non-transient

6. `isinstance(error, ExceptionGroup)`
   -> `provider_exception_group_family`
   -> non-transient

7. Every other remaining exception
   -> existing `provider_non_http_failure`
   -> non-transient

## Critical invariants

All existing classifications retain priority, including:

- APITimeoutError before APIConnectionError
- auth/quota/rate/HTTP mappings
- anomalous APIStatusError -> provider_failure
- exact APIResponseValidationError
- exact JSONDecodeError
- exact TypeError
- exact ValueError
- exact RuntimeError

Do not broaden or reorder those branches.

Specific inheritance outcomes required:

- APIResponseValidationError subclass -> provider_openai_error_family
- JSONDecodeError subclass -> provider_value_subclass_family
- TypeError subclass -> provider_python_internal_family
- RuntimeError subclass -> provider_python_internal_family
- KeyError/IndexError -> provider_python_internal_family via LookupError
- raw httpcore2 exceptions remain provider_non_http_failure
- raw/unrelated custom Exception remains provider_non_http_failure

Do not:
- use broad `httpx2.HTTPError`
- add direct httpcore2 production classification
- add direct Pydantic production classification
- inspect nested ExceptionGroup members
- catch BaseException/BaseExceptionGroup
- reflect class names/modules/MRO

## CLI additions

Add exactly these six literals to the existing private diagnostic allowlist:

- provider_openai_error_family
- provider_http_client_error_family
- provider_os_error_family
- provider_value_subclass_family
- provider_python_internal_family
- provider_exception_group_family

Preserve all existing allowlisted codes, bounded output, generic fallback, stderr behavior, exit codes, and lock lifecycle.

## Adapter tests

In `test/test_openai_analysis.py`, add/adjust only offline tests proving:

1. residual OpenAIError/APIError subclass -> provider_openai_error_family
2. residual httpx2.RequestError/ProtocolError/DecodingError -> provider_http_client_error_family when they escape unwrapped
3. raw OSError -> provider_os_error_family
4. SSL/OSError subclass -> provider_os_error_family
5. UnicodeError/UnicodeDecodeError -> provider_value_subclass_family
6. safe ValueError subclass -> provider_value_subclass_family
7. TypeError subclass -> provider_python_internal_family
8. RuntimeError subclass -> provider_python_internal_family
9. AttributeError -> provider_python_internal_family
10. KeyError/IndexError -> provider_python_internal_family
11. AssertionError -> provider_python_internal_family
12. exact ExceptionGroup -> provider_exception_group_family
13. raw httpcore2 error -> provider_non_http_failure
14. unrelated custom Exception -> provider_non_http_failure

For each new family:
- one SDK attempt
- no retry/sleep
- request lock released
- no raw injected text in adapter error, stdout/stderr, logs

## Regression tests

Preserve and prove:

- exact APIResponseValidationError -> provider_response_validation_failure
- exact JSONDecodeError -> provider_response_json_failure
- exact TypeError -> provider_sdk_type_failure
- exact ValueError -> provider_sdk_value_failure
- exact RuntimeError -> provider_sdk_runtime_failure
- timeout/connection/auth/quota/HTTP retry behavior unchanged
- request_schema_failure unchanged
- request kwargs unchanged
- client factory arguments unchanged
- existing synthetic smoke one-shot and ownership behavior unchanged

## Pinned-SDK offline/no-network tests

Use only:
- synthetic API key
- explicit httpx2.MockTransport / no-network transport
- local injected failures

At minimum verify:
- ordinary httpx2.DecodingError emitted during send is still translated by SDK into existing connection/retry behavior;
- residual family injections map to fixed new codes only when they escape the normal SDK wrappers;
- pre-send structural failure can be tested with zero mock dispatch without asserting that the live failure occurred there;
- no default network transport;
- no real keyring/config/SQLite/provider endpoint.

## CLI tests

In `test/test_ai_smoke_cli.py`:

1. Add all six new codes to expected allowlist.
2. Verify exact `smoke_failed:<code>\n`, empty stderr, exit 1, lock release.
3. Preserve provider_non_http_failure and all previous diagnostics.
4. Preserve generic fallback for unknown/internal/non-string/unhashable values.
5. Preserve success/help/disabled/lock_unavailable/unavailable/invalid-command behavior.

## Security restrictions

Never expose/log/derive:
- type(error).__name__
- type(error).__module__
- MRO
- str(error)
- repr(error)
- args
- cause/context
- nested ExceptionGroup members
- provider body/message
- request payload
- URL/headers
- secrets

Do not:
- call OpenAI
- execute live smoke
- access real keyring/API key
- access operational config/SQLite
- install/update/downgrade dependencies
- change model/endpoint/schema/payload/retries/timeout/gate/routes
- add telemetry or transport instrumentation

## Validation

Run:

python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/integrations/openai_analysis.py
- test/test_openai_analysis.py
- app/integrations/ai_smoke_cli.py
- test/test_ai_smoke_cli.py

## STOP conditions

STOP if:
- a fifth file is required;
- a dependency/package change is required;
- dynamic exception reflection is needed;
- nested ExceptionGroup inspection is needed;
- BaseException catch expansion is needed;
- retry semantics must change;
- live access is needed to validate.

## Completion

Commit:

Implement phase 6F unknown non-HTTP exception families

Push only origin/codex-work.
