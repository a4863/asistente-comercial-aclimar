# Phase 6F Split Output Text Handling Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-29

## Accepted implementation

Commit:

`8e3b5350afea9a4b39c3dc7a3ae23e73b4cdb516`

Exactly two tracked files changed:

1. `app/integrations/openai_analysis.py`
2. `test/test_openai_analysis.py`

## Accepted extraction change

`_structured_text(response)` now:

- preserves existing global response status checks;
- skips only reasoning items;
- still requires all other output items to be assistant messages;
- still rejects refusals immediately;
- still rejects unknown/non-output_text parts;
- collects all allowed string `output_text` fragments in traversal order;
- requires at least one fragment;
- concatenates fragments with exactly no separator;
- rejects an empty aggregate;
- applies the existing UTF-8 and `MAX_RESPONSE_BYTES` checks to the aggregate;
- returns the aggregate to the unchanged `json.loads` and `decode_analysis_response` path.

## Explicitly unchanged

- `message.status` behavior;
- `response_schema()`;
- `decode_analysis_response()`;
- evidence/provenance validation;
- model/endpoint/payload;
- timeouts/retries;
- hook observability;
- deterministic client close;
- ownership/commercial gate;
- refusal/incomplete/unknown-item fail-closed semantics.

No SDK `response.output_text` shortcut, separator insertion, JSON repair, best-message selection, or semantic relaxation was introduced.

## Validation

User-reported:

- focal tests: **146 passed**
- full suite: **897 passed, 2 skipped, 7 warnings**
- exact two-file Scope Lock
- `git diff --check`: PASS
- tracked state clean
- origin commit: `8e3b5350afea9a4b39c3dc7a3ae23e73b4cdb516`
- no OpenAI call
- no live smoke

GitHub review confirms the production change matches the approved extraction-only plan.

## Result

**ACCEPTED.**

This acceptance does not establish that split output text caused the tenth live `invalid_output`.

No eleventh live smoke is authorized by this acceptance. Any further live synthetic execution requires fresh explicit user authorization.
