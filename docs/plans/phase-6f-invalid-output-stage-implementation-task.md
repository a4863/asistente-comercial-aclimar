# Phase 6F Invalid Output Stage Diagnostics Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-29
**Depends on:** docs/plans/phase-6f-invalid-output-stage-plan.md — READY FOR IMPLEMENT

## Objective

Implement a pure diagnostic relabeling of existing post-SDK-return output failures into exactly three bounded stage codes:

- `provider_output_envelope_failure`
- `provider_output_json_failure`
- `provider_output_semantic_failure`

No live provider call is authorized.

## Exact Scope Lock

Modify exactly these four tracked files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py
3. app/integrations/ai_smoke_cli.py
4. test/test_ai_smoke_cli.py

No fifth tracked file may change.

## Adapter mapping

### Envelope / extraction

Inside `_structured_text(response)`, replace only existing `invalid_output` raises with:

`provider_output_envelope_failure`

Preserve unchanged:
- incomplete -> provider_incomplete
- refusal -> provider_refusal
- reasoning skip
- traversal order
- split-output concatenation
- role/type/content checks
- UTF-8 bound
- MAX_RESPONSE_BYTES
- message.status behavior

Do not wrap `_structured_text()` in a broader catch.

### JSON parse

After successful extraction, place only:

`parsed = json.loads(text)`

inside its own try/catch using exactly the current tuple:

`(ValueError, AISchemaError, TypeError, OverflowError, UnicodeError)`

Caught failures map to:

`provider_output_json_failure`

Do not widen or alter the tuple.

### Semantic decoder

After successful JSON parse, place only:

`result = decode_analysis_response(parsed, projection)`

inside the adjacent try/catch using the exact same tuple:

`(ValueError, AISchemaError, TypeError, OverflowError, UnicodeError)`

Caught failures map to:

`provider_output_semantic_failure`

Do not change decoder behavior.

## Preserve all existing precedence

Unchanged:
- provider_response_json_failure from SDK-call boundary
- provider_incomplete
- provider_refusal
- timeout
- provider_client_close_failure
- all HTTP/transport/hook/provider classifications
- request_schema_failure
- retries/deadline/sleep
- deterministic close
- request lock
- ownership/commercial gate
- model/endpoint/schema/payload
- accepted response set

The three new codes are:
- non-transient
- no-retry
- content-free

## CLI

Add exactly these three codes to `_DIAGNOSTIC_CODES`:

- provider_output_envelope_failure
- provider_output_json_failure
- provider_output_semantic_failure

Keep:
- invalid_output
- provider_response_json_failure
- all previous codes
- generic smoke_failed fallback for unknown/non-string/unhashable values

## Required tests

### Envelope stage

Assert exact `provider_output_envelope_failure` for:
- non-completed global status other than incomplete
- missing/non-list output
- wrong item type
- wrong role
- non-list content
- unknown content part
- non-string output_text
- no text
- empty aggregate
- Unicode encode failure
- aggregate > MAX_RESPONSE_BYTES

### Preserved special codes

Assert unchanged:
- incomplete -> provider_incomplete
- refusal -> provider_refusal
- post-return deadline expiry -> timeout
- successful decode + close failure -> provider_client_close_failure
- SDK-call-boundary JSON failure -> provider_response_json_failure

### JSON stage

Assert exact `provider_output_json_failure` for:
- malformed JSON
- concatenated complete JSON documents

### Semantic stage

Assert exact `provider_output_semantic_failure` for:
- parseable wrong top-level shape
- evidence mismatch
- invalid support/reference index
- invalid date/domain invariant
- other currently caught decoder rejection

### Success/regression

Preserve:
- valid structured semantic output accepted
- split-output valid JSON accepted
- reasoning handling unchanged
- refusal traversal unchanged
- one provider call/no retry for all three stage failures
- client close exactly once
- request lock release
- no raw output/exception details in adapter/CLI/logs
- all previous provider/transport/hook classifications unchanged

## Security restrictions

Do not:
- call OpenAI
- run live smoke
- inspect eleventh live response
- use real keyring/API key
- access operational config/SQLite
- make network probes
- change dependencies
- change response_schema()
- change decode_analysis_response()
- change model/endpoint/payload/timeout/retries
- expose raw output, field names, parser offsets, exception messages/classes

## Validation

Run:

python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must be exactly the four files listed above.

## STOP conditions

STOP if:
- a fifth tracked file is needed;
- an exception tuple must change;
- schema/decoder behavior must change;
- special-code precedence cannot be preserved;
- live/provider access is needed.

## Completion

Commit:

Implement phase 6F invalid output stage diagnostics

Push only origin/codex-work.
