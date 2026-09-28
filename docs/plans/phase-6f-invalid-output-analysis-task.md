# Phase 6F Invalid Output Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY / NO LIVE PROVIDER CALL
**Trigger:** tenth live smoke returned `invalid_output`

## Objective

Determine every bounded path by which the current fixed synthetic smoke can produce `invalid_output` after a successful return from `client.responses.create(**request_kwargs)`, and identify the smallest offline-testable next correction, if any.

Do not inspect or recover the live response content.
Do not call OpenAI.

## Current known boundary

The application currently does:

1. `response = client.responses.create(**request_kwargs)`
2. deadline check
3. `text = _structured_text(response)`
4. `json.loads(text)`
5. `decode_analysis_response(parsed, projection)`

The tenth smoke reached a bounded `invalid_output`.

## Required source inspection

Inspect:
- current `_structured_text()`
- current `decode_analysis_response()`
- current `response_schema()`
- installed `openai==3.17.0` Responses API response model types/shapes
- current tests around structured output
- smoke fixed input and expected AnalysisCandidates contract

## Questions to resolve

1. Enumerate exact branches in `_structured_text()` that map to `invalid_output`.
2. Enumerate exact post-text branches that map to `invalid_output`.
3. Does the installed SDK return a Responses object whose output/content shape exactly matches what `_structured_text()` assumes?
4. Are there SDK helper properties (for example an output-text helper) that differ from the raw model structure currently parsed?
5. Could reasoning items, annotations, multiple output_text parts, or other valid Responses API constructs cause the parser to reject a valid structured response?
6. Does strict Structured Outputs with `text.format=json_schema` guarantee exactly one assistant message/output_text item, or only schema-conformant text content?
7. Does the current response schema match `decode_analysis_response()` exactly?
8. Can a minimal synthetic valid response object be built offline that passes the full parser?
9. Can realistic SDK response variants be synthesized offline that currently fail `_structured_text()` despite containing one valid schema-conformant payload?
10. Could the tenth result be caused by valid but unexpected SDK envelope shape rather than invalid model JSON?
11. Can the failure be narrowed without exposing live response content?
12. If a parser correction is justified, what is the minimal safe change?
13. If no correction can be justified without live response inspection, return STOP rather than guessing.

## Required offline tests

Use only synthetic data / installed SDK models / fake response objects.

At minimum cover:
- one valid completed response with one assistant output_text containing schema-valid JSON;
- completed response with reasoning item plus assistant message;
- assistant message with more than one content part;
- annotations or metadata on output_text if supported;
- multiple message/output items if supported;
- refusal;
- incomplete status;
- malformed JSON text;
- schema-valid JSON that fails application semantic validation;
- response object shape produced by installed SDK model constructors if practical.

Record only fixed case labels and bounded outcomes.

## Security restrictions

Do not:
- call OpenAI;
- run another live smoke;
- inspect live response body/content;
- use real keyring/API key;
- access operational config/SQLite;
- make external network probes;
- add production code;
- change model/endpoint/schema/payload/timeout/retries;
- print raw synthetic payloads beyond minimal fixed fixtures;
- expose exception text/class identity from live data.

## Deliverable

Create only:

`docs/plans/phase-6f-invalid-output-analysis.md`

Include:
- exact invalid_output decision tree;
- installed SDK response-envelope findings;
- schema/decoder compatibility findings;
- offline reproduction matrix;
- whether a parser mismatch is demonstrated;
- proposed minimal correction and Scope Lock, or STOP;
- whether another live synthetic smoke would be justified after correction;
- verdict: READY FOR PLAN or STOP.

No code changes.
No live access.

Commit:

Analyze phase 6F invalid output

Push only origin/codex-work.
