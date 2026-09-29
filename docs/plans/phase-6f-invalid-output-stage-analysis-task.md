# Phase 6F Invalid Output Stage Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-29
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Trigger:** eleventh live smoke returned `invalid_output` after split-output correction

## Objective

Determine whether the current post-SDK-return `invalid_output` can be safely partitioned into fixed, content-free stage diagnostics that distinguish:

1. response-envelope/extraction failure;
2. JSON parse failure;
3. local semantic/schema/evidence decoder failure.

Do not inspect or recover the eleventh live response.
Do not call OpenAI.

## Current boundary

After successful `Responses.create()` return, the adapter currently performs:

1. deadline check;
2. `_structured_text(response)`;
3. `json.loads(text)`;
4. `decode_analysis_response(parsed, projection)`.

Multiple failures in steps 2–4 collapse to `invalid_output`.

## Required analysis

Inspect current code/tests and determine whether fixed stage diagnostics can be introduced without:

- reading or logging raw output;
- changing response acceptance semantics;
- weakening schema/evidence validation;
- changing retries/timeouts;
- changing provider request shape;
- exposing exception messages/classes.

## Questions to resolve

1. Can all current `_structured_text()` invalid-output branches safely map to a fixed envelope-stage code?
2. Can `json.loads(text)` failures safely map to a fixed JSON-stage code without exposing parser details?
3. Can `decode_analysis_response()` failures safely map to a fixed semantic-stage code without weakening or exposing validation details?
4. Which current special codes must remain unchanged:
   - provider_incomplete
   - provider_refusal
   - timeout
   - provider_client_close_failure
   - provider_response_json_failure from SDK-call boundary
   and all provider/transport categories?
5. Is there any overlap where a fixed stage code would misrepresent the stage?
6. Should Unicode/oversize aggregate failures inside `_structured_text()` remain envelope-stage or receive separate treatment?
7. Can the change be limited to the adapter + adapter tests + CLI allowlist/tests?
8. What exact code names are least misleading?
9. Can all stage codes remain non-transient and no-retry?
10. If the partition cannot be made without semantic changes or content inspection, return STOP.

## Preferred bounded direction

Only if supported, consider fixed names conceptually equivalent to:

- `provider_output_envelope_failure`
- `provider_output_json_failure`
- `provider_output_semantic_failure`

Do not adopt these names unless analysis confirms they are accurate.

The names must describe application validation stage only, not provider fault.

## Required offline tests

Using synthetic response objects only, demonstrate stage separation for:

### Envelope/extraction
- non-completed status other than incomplete;
- missing/non-list output;
- wrong item type;
- wrong role;
- non-list content;
- unknown content part;
- non-string output_text;
- no text / empty aggregate;
- aggregate Unicode encode failure;
- aggregate over MAX_RESPONSE_BYTES.

### Preserved special codes
- incomplete -> provider_incomplete;
- refusal -> provider_refusal.

### JSON stage
- malformed JSON after otherwise valid extraction;
- concatenated independent JSON documents.

### Semantic stage
- structurally parseable JSON rejected by decode_analysis_response;
- evidence mismatch;
- invalid support/reference/date/domain invariant.

### Success
- schema-valid semantic output still accepted.

### Regression
- no retry;
- one client close;
- request lock release;
- no raw output in errors/logs/stdout/stderr;
- all provider/transport/hook codes unchanged.

## Security restrictions

Do not:
- call OpenAI;
- run live smoke;
- inspect live response;
- use real keyring/API key;
- access operational config/SQLite;
- make network probes;
- modify code;
- change dependencies;
- change response_schema;
- change decoder semantics;
- change model/endpoint/payload/timeout/retries;
- print raw synthetic output except minimal fixture construction;
- expose exception text/class identity.

## Deliverable

Create only:

`docs/plans/phase-6f-invalid-output-stage-analysis.md`

Include:
- current decision tree;
- safe/unsafe stage boundaries;
- exact proposed fixed codes or STOP;
- precedence/special-code preservation;
- proposed Scope Lock;
- offline/no-network test matrix;
- whether another live synthetic smoke would be justified after an accepted implementation;
- verdict: READY FOR PLAN or STOP.

No code changes.
No live access.

Commit:

Analyze phase 6F invalid output stages

Push only origin/codex-work.
