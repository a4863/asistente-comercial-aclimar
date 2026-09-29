# Phase 6F Invalid Output Stage Diagnostics Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-29

## Accepted implementation

Commit:

`14a169b32b9af41a85f9f11989be92c43af22897`

Exactly four tracked files changed:

1. `app/integrations/openai_analysis.py`
2. `test/test_openai_analysis.py`
3. `app/integrations/ai_smoke_cli.py`
4. `test/test_ai_smoke_cli.py`

## Accepted diagnostic mapping

Post-SDK-return failures are now partitioned by application validation stage:

- extraction/envelope rejection
  -> `provider_output_envelope_failure`
- JSON parse rejection
  -> `provider_output_json_failure`
- semantic/schema/evidence decoder rejection
  -> `provider_output_semantic_failure`

## Explicitly preserved

Unchanged:
- accepted response set;
- global response validation order;
- split-output handling;
- refusal -> `provider_refusal`;
- incomplete -> `provider_incomplete`;
- post-return deadline -> `timeout`;
- SDK-call-boundary JSON -> `provider_response_json_failure`;
- deterministic client close;
- `provider_client_close_failure` precedence;
- request lock;
- hook observability;
- retries/deadline/sleep;
- ownership/commercial gate;
- model/endpoint/schema/payload;
- decoder semantics and evidence/provenance rules.

The exact existing exception tuple remains unchanged at both post-extraction call sites.

## CLI

Added exactly:

- `provider_output_envelope_failure`
- `provider_output_json_failure`
- `provider_output_semantic_failure`

Existing `invalid_output`, all prior diagnostics, and generic fallback remain.

## Validation

User-reported:

- focal tests: **229 passed**
- full suite: **909 passed, 2 skipped, 7 warnings**
- exact four-file Scope Lock
- `git diff --check`: PASS
- no OpenAI call
- no live smoke
- origin commit: `14a169b32b9af41a85f9f11989be92c43af22897`

GitHub review confirms the implementation is a pure call-site diagnostic relabeling and matches the approved plan.

## Result

**ACCEPTED.**

This acceptance does not identify the historical eleventh `invalid_output` stage.

No twelfth live smoke is authorized by this acceptance. Any further live synthetic execution requires fresh explicit user authorization.
