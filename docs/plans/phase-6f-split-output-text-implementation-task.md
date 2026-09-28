# Phase 6F Split Output Text Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-28
**Depends on:** docs/plans/phase-6f-split-output-text-plan.md — READY FOR IMPLEMENT

## Objective

Implement exactly the approved extraction-only correction so one logical JSON payload may be split across multiple allowed `output_text` fragments.

No live provider call is authorized.

## Exact Scope Lock

Modify exactly these two tracked files:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py

No third tracked file may change.

## Production change

Modify only `_structured_text(response)`.

Preserve current logic for:

- global status:
  - incomplete -> provider_incomplete
  - non-completed -> invalid_output
- output must be a list
- reasoning items are skipped
- every other output item must be assistant message
- every message content must be a list
- refusal -> provider_refusal immediately
- every other content part must be output_text with string text
- unknown/tool/non-message/wrong-role cases -> invalid_output
- UTF-8 encoding guard
- MAX_RESPONSE_BYTES bound
- downstream json.loads
- downstream decode_analysis_response
- message.status behavior exactly unchanged

Change only extraction semantics:

1. collect all allowed output_text string fragments in traversal order;
2. require at least one fragment;
3. concatenate with exactly "" and no separator;
4. reject empty aggregate;
5. apply existing UTF-8 and byte bound to aggregate;
6. return aggregate.

Do not:
- use response.output_text as sole validator;
- trim;
- insert separators;
- repair JSON;
- choose a best message;
- ignore refusal;
- ignore unknown parts/items;
- change schema/decoder.

## Required tests

In test/test_openai_analysis.py cover at minimum:

- one message/one output_text accepted;
- reasoning + message accepted;
- one message/two fragments forming one JSON accepted;
- two assistant messages whose fragments form one JSON accepted;
- annotations/metadata harmless;
- refusal alone -> provider_refusal;
- refusal mixed with text -> provider_refusal;
- incomplete -> provider_incomplete;
- other non-completed -> invalid_output;
- empty output/content/no text -> invalid_output;
- only empty fragments -> invalid_output;
- non-string text -> invalid_output;
- unknown content part -> invalid_output;
- non-message/tool output -> invalid_output;
- wrong role -> invalid_output;
- malformed aggregate JSON -> invalid_output;
- two complete JSON documents concatenated -> invalid_output;
- aggregate > MAX_RESPONSE_BYTES -> invalid_output;
- Unicode aggregate encode failure -> invalid_output;
- structurally valid but semantically invalid evidence -> invalid_output;
- output failure does not retry;
- success/failure still close client exactly once;
- request lock released;
- no raw synthetic output leakage;
- message.status behavior unchanged.

Use installed SDK Response models where practical.

## Security restrictions

Do not:
- call OpenAI;
- execute live smoke;
- inspect tenth live response;
- use real keyring/API key;
- access operational config/SQLite;
- make external network probes;
- change dependencies;
- change response_schema();
- change decode_analysis_response();
- change model/endpoint/payload/timeout/retries;
- change hook observability or deterministic close;
- add logging or raw response diagnostics;
- change message.status validation.

## Validation

Run:

python -m pytest test/test_openai_analysis.py

Then:

python -m pytest

Then:

git diff --name-only
git diff --check

Tracked diff must be exactly:

- app/integrations/openai_analysis.py
- test/test_openai_analysis.py

## STOP conditions

STOP if:
- a third tracked file is needed;
- any schema/decoder change is needed;
- message.status behavior must change;
- live/provider access is needed;
- retry/timeout/gate/ownership semantics must change.

## Completion

Commit:

Implement phase 6F split output text handling

Push only origin/codex-work.
