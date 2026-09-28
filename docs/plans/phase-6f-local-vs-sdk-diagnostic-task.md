# Phase 6F Local vs SDK Diagnostic Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-local-vs-sdk-diagnostic-plan.md — READY FOR IMPLEMENT

## Objective

Implement the approved bounded phase separation between:
1. local response-schema/request-argument construction;
2. the SDK `responses.create()` call.

No live smoke and no OpenAI call are authorized by this task.

## Exact Scope Lock

Modify exactly these four files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

No fifth tracked file may change.

## Required adapter change

Inside each retry-loop iteration:

1. Keep existing positive remaining-time check.
2. Keep existing authorization recheck.
3. Before invoking `client.responses.create()`, build the exact current request kwargs inside a dedicated bounded local `try`.

The kwargs must remain semantically identical:

- `model=settings.model`
- `instructions=_INSTRUCTIONS`
- `input=request_input`
- `text={"format": {"type": "json_schema", "name": "commercial_analysis_v1", "strict": True, "schema": response_schema()}}`
- `max_output_tokens=settings.max_output_tokens`
- `store=False`
- `timeout=remaining`

Do not:
- cache/move `response_schema()` outside the retry iteration;
- change schema semantics;
- change request_input/request_text handling;
- change model/endpoint/payload/token limit/timeout/retries.

If local schema/kwargs construction raises any Exception:
- map only to fixed `request_schema_failure`;
- use existing `_raise`;
- do not inspect/print/log/retain the caught exception;
- do not invoke SDK;
- do not retry.

Then invoke only:

`response = client.responses.create(**request_kwargs)`

inside the existing SDK-call `try`.

Preserve the complete current SDK exception classification and retry behavior unchanged, including:
- timeout
- connection/transient
- quota/rate
- auth
- typed HTTP mappings
- provider_failure
- provider_non_http_failure

Do not add pre-dispatch/post-dispatch claims.

## CLI change

Add exactly:

`request_schema_failure`

to the existing private diagnostic allowlist.

For that code:
- stdout exactly `smoke_failed:request_schema_failure\n`
- stderr empty
- exit 1

Preserve all existing diagnostic/fallback/output behavior.

## Tests — adapter

In `test/test_openai_analysis.py` add/adjust only offline tests that prove:

1. Monkeypatched `response_schema()` raising secret/body/path/control-text exception ->
   - code `request_schema_failure`
   - zero SDK calls
   - zero retry/sleep
   - request lock released
   - injected text absent from exception output/logs/stdout/stderr.
2. Non-HTTP exception raised from `responses.create()` ->
   - `provider_non_http_failure`
   - exactly one SDK call
   - no retry
   - no raw text leak.
3. Existing typed HTTP/auth/quota/timeout/connection categories and retry counts unchanged.
4. Exact request kwargs unchanged on successful fake call.
5. Existing transient retry rebuilds the same local kwargs and reauthorizes as before.
6. Installed `openai==3.17.0` offline contract test with synthetic key and explicit no-network/mock transport:
   - exact fixed synthetic request path;
   - one in-process POST /v1/responses;
   - no default transport/network;
   - no real keyring/config/SQLite;
   - do not print request body or auth header.

## Tests — CLI

In `test/test_ai_smoke_cli.py`:

1. Add `request_schema_failure` to expected allowlist.
2. Verify exact bounded output, empty stderr, exit 1, lock release.
3. Preserve `provider_non_http_failure` behavior.
4. Preserve generic fallback for unknown/internal/non-string/unhashable codes.
5. Preserve success/help/disabled/lock_unavailable/unavailable/invalid-command behavior.
6. No gate/keyring/config/SQLite/provider real access.

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

## Security restrictions

Never expose:
- raw local exception text
- traceback/cause
- SDK/provider body/message/code
- request payload
- schema contents
- API key/credential reference
- endpoint/model/path

Do not:
- call OpenAI
- access real keyring
- access operational config/SQLite
- change dependencies
- change model/endpoint/schema/payload/retries/timeout/gate/routes

## STOP conditions

STOP if:
- a fifth file is required;
- safe phase separation needs raw exception/provider content;
- a pre-dispatch/post-dispatch distinction inside SDK is required;
- any request/retry semantic change is required;
- live access is needed to validate.

## Completion

Commit:

Implement phase 6F local vs SDK diagnostics

Push only origin/codex-work.
