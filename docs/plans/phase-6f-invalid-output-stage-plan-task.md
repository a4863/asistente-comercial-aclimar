# Phase 6F Invalid Output Stage Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-29
**Depends on:** docs/plans/phase-6f-invalid-output-stage-analysis.md — READY FOR PLAN

## Objective

Produce an implementation-ready plan for a pure diagnostic relabeling of existing post-SDK-return output failures into three fixed stage codes:

- `provider_output_envelope_failure`
- `provider_output_json_failure`
- `provider_output_semantic_failure`

Do not implement code.
Do not call OpenAI.

## Fixed semantic contract

These codes identify only the application validation stage.

They MUST NOT claim:
- provider fault;
- exact malformed field;
- parser position;
- invalid evidence rule;
- provider-origin response shape.

## Exact mapping

### Envelope/extraction stage

Existing `_structured_text()` branches that currently raise `invalid_output` should instead raise:

`provider_output_envelope_failure`

This includes only existing invalid-output branches such as:
- non-completed global status other than incomplete;
- output missing/non-list;
- wrong item type;
- wrong role;
- non-list content;
- unknown content part;
- non-string output_text;
- no text / empty aggregate;
- aggregate UTF-8 encoding failure;
- aggregate > MAX_RESPONSE_BYTES.

Preserve:
- `provider_incomplete`
- `provider_refusal`

Do not reorder traversal or refusal precedence.

### JSON parse stage

After successful extraction, existing caught `json.loads(text)` failures should map to:

`provider_output_json_failure`

This code is distinct from:

`provider_response_json_failure`

which belongs to the SDK-call boundary and must remain unchanged.

### Semantic decoder stage

After successful JSON parsing, existing caught `decode_analysis_response(parsed, projection)` failures should map to:

`provider_output_semantic_failure`

Do not change decoder semantics.

## Exception boundaries

The plan must preserve the exact existing caught exception tuples at each call site.

Do not:
- broaden catches;
- swallow unexpected exceptions;
- catch all exceptions around _structured_text;
- collapse special codes into stage codes.

## Preserved behavior

Unchanged:
- accepted response set;
- response traversal;
- split-output handling;
- response_schema();
- decode_analysis_response();
- evidence/provenance checks;
- model/endpoint/payload;
- timeout/deadline;
- retries/sleep;
- hook observability;
- deterministic client close;
- ownership/gate;
- request lock;
- one-shot smoke.

All three new stage codes are:
- fixed;
- non-transient;
- no-retry.

Existing `invalid_output` remains in CLI allowlist as compatibility/fallback.

## Exact Scope Lock

Planning must verify implementation can remain within exactly four files:

1. `app/integrations/openai_analysis.py`
2. `test/test_openai_analysis.py`
3. `app/integrations/ai_smoke_cli.py`
4. `test/test_ai_smoke_cli.py`

If a fifth tracked file is required, verdict must be STOP.

## Required test matrix

### Envelope stage
Exact code `provider_output_envelope_failure` for:
- non-completed global status other than incomplete;
- missing/non-list output;
- wrong item type;
- wrong role;
- non-list content;
- unknown content part;
- non-string output_text;
- no text;
- empty aggregate;
- aggregate Unicode encode failure;
- aggregate > MAX_RESPONSE_BYTES.

### Preserved special codes
- incomplete -> provider_incomplete;
- refusal -> provider_refusal;
- timeout -> timeout;
- successful decode + close failure -> provider_client_close_failure.

### JSON stage
Exact code `provider_output_json_failure` for:
- malformed JSON;
- concatenated complete JSON documents.

### Semantic stage
Exact code `provider_output_semantic_failure` for:
- parseable wrong top-level shape;
- evidence mismatch;
- invalid support/reference index;
- invalid date/domain invariant;
- any existing decoder failure covered by current catch tuple.

### Success
- valid structured and semantic output accepted.

### Regression
- provider_response_json_failure unchanged for SDK-call-boundary JSON failure;
- exact provider/transport/hook classifications unchanged;
- no retry/provider re-call;
- client close exactly once;
- request lock released;
- no raw output/exception details in adapter/CLI/logs.

### CLI
Add exactly the three new fixed codes to the allowlist.
Keep:
- existing invalid_output;
- provider_response_json_failure;
- all previous diagnostics;
- generic fallback for unknown/non-string/unhashable values.

## Security restrictions

Do not:
- call OpenAI;
- run live smoke;
- inspect eleventh live response;
- use real keyring/API key;
- access operational config/SQLite;
- make network probes;
- change dependencies;
- change schema/decoder semantics;
- change provider request shape;
- expose raw output, field names, parser offsets, exception text/class/module/MRO.

## Deliverable

Create only:

`docs/plans/phase-6f-invalid-output-stage-plan.md`

Include:
- exact mapping and precedence;
- exact unchanged exception tuples;
- exact four-file Scope Lock;
- per-file changes;
- offline/no-network acceptance matrix;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F invalid output stage diagnostics

Push only origin/codex-work.
