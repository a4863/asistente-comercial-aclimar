# Phase 6F Split Output Text Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-invalid-output-analysis.md — READY FOR PLAN

## Objective

Produce an implementation-ready plan for one narrow extraction correction:

Allow a valid logical structured-output JSON payload to be formed by concatenating multiple allowed `output_text` parts, in SDK output/content order, before the existing JSON parse and semantic decoder.

Do not implement code.
Do not call OpenAI.

## Fixed design decision

This correction is extraction-only.

Preserve unchanged:
- global response status handling;
- reasoning-item skip;
- assistant-message requirement;
- refusal precedence;
- unknown/tool/non-message output rejection;
- unknown/non-output_text part rejection;
- UTF-8 byte bound;
- `json.loads`;
- `decode_analysis_response`;
- all evidence/provenance/domain validation;
- retries/timeouts;
- model/endpoint/schema/payload;
- hook observability;
- deterministic client close;
- ownership/gate behavior.

Do NOT add or change message-level status validation in this task. The current behavior regarding message status remains exactly as-is.

## Required extraction contract

Plan the smallest change to `_structured_text(response)` such that:

1. Traverse output items in their existing order.
2. Skip only reasoning items, as today.
3. Every non-reasoning output item must still be an assistant message.
4. Every message content item must still be either:
   - refusal -> fail with existing provider_refusal;
   - output_text with string text -> eligible text fragment.
5. Collect all allowed output_text fragments in order across all allowed messages.
6. Require at least one fragment.
7. Concatenate fragments exactly in order with no separator and no repair/coercion.
8. Require aggregate text to be nonempty.
9. Apply existing UTF-8 encoding check and MAX_RESPONSE_BYTES bound to the aggregate.
10. Return the aggregate to the existing unchanged json.loads + decode_analysis_response path.

Do not:
- use SDK `response.output_text` as sole validation;
- pick a “best” message;
- ignore refusals;
- ignore unknown output/content items;
- insert separators;
- repair JSON;
- accept multiple independent JSON documents;
- weaken semantic validation.

## Exact Scope Lock

Planning must verify implementation can remain within exactly:

1. `app/integrations/openai_analysis.py`
2. `test/test_openai_analysis.py`

If a third tracked file is required, verdict must be STOP.

## Required test matrix

Plan offline tests for at least:

- completed response, one assistant message, one output_text -> accepted;
- reasoning item + valid message -> accepted;
- one message with multiple output_text fragments forming one valid JSON -> accepted;
- multiple assistant messages whose fragments form one valid JSON -> accepted;
- annotations/metadata remain harmless;
- refusal alone -> provider_refusal;
- refusal alongside text -> provider_refusal;
- incomplete global status -> provider_incomplete;
- other non-completed global status -> invalid_output;
- empty content/no output_text -> invalid_output;
- output_text fragment with non-string text -> invalid_output;
- unknown content part -> invalid_output;
- non-message/tool output item -> invalid_output;
- wrong message role -> invalid_output;
- aggregate malformed JSON -> invalid_output downstream;
- two complete JSON documents concatenated -> invalid_output downstream;
- aggregate exceeds MAX_RESPONSE_BYTES -> invalid_output;
- Unicode encoding failure on aggregate -> invalid_output;
- schema-shaped but semantically invalid evidence -> invalid_output;
- no retry/provider re-call;
- deterministic client close still exactly once;
- request lock released;
- no raw output leakage.

Use installed SDK Response models where practical, not only SimpleNamespace fakes.

## Security restrictions

Do not:
- call OpenAI;
- run live smoke;
- inspect tenth live response;
- use real keyring/API key;
- access operational config/SQLite;
- make network probes;
- change dependencies;
- change response_schema();
- change decode_analysis_response();
- change model/endpoint/payload/timeout/retries;
- add logging/raw response diagnostics.

## Deliverable

Create only:

`docs/plans/phase-6f-split-output-text-plan.md`

Include:
- exact extraction algorithm;
- exact preserved failure semantics;
- explicit no-change decision for message-level status;
- exact two-file Scope Lock;
- per-file changes;
- offline/no-network test matrix;
- rollback;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F split output text handling

Push only origin/codex-work.
