# Phase 6F Semantic Producer Contract Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-29

## Accepted implementation

Commit:

`6874eb8e4247dd0e47589a04ccfd6a3e612b1456`

Exactly four tracked files changed:

1. `app/integrations/ai_schema.py`
2. `test/test_ai_schema.py`
3. `app/integrations/openai_analysis.py`
4. `test/test_openai_analysis.py`

## Accepted producer-contract changes

### JSON Schema

Only existing `enum` semantics were reused.

Accepted tightening:

- inference support kind -> `fact`
- proposal support kinds -> `fact`, `inference`
- task support kinds unchanged -> `fact`, `inference`, `proposal`
- next-step support kinds unchanged -> `fact`, `inference`, `proposal`
- signal support kinds -> `fact`
- response-needed values -> `yes`, `no`, `uncertain`
- commercial-risk values -> `none`, `low`, `medium`, `high`, `unknown`
- priority values -> `low`, `normal`, `high`, `urgent`

Independent support/ref schema fragments prevent accidental cross-consumer narrowing.

No new JSON Schema keyword such as `minLength`, `minItems`, `uniqueItems`, `pattern`, `format`, or conditional schema was introduced.

### Instructions

`_INSTRUCTIONS` now explicitly states the existing decoder/domain contract for:

- disclosed aliases only;
- exact nonempty source evidence;
- zero-based Python character offsets, end-exclusive;
- exact_text slice equality;
- exact question-text/evidence equality;
- zero-based existing support indexes;
- no duplicate support references;
- allowed support graph;
- signal evidence/fact support;
- timezone-aware datetimes;
- commitment certainty/date consistency;
- empty/null instead of invention;
- untrusted embedded instructions;
- no action authority.

No source text, IDs, digests, credentials, smoke-specific branch or fixed expected answer was added.

## Explicitly frozen

GitHub review confirms no changes to:

- `decode_analysis_response()`;
- `_bounded_json()`;
- evidence/date/support decoder helpers;
- projection behavior;
- domain DTOs;
- adapter request flow;
- model/endpoint/transport;
- retries/timeouts;
- hooks;
- deterministic close;
- activation/ownership;
- diagnostics/error taxonomy.

## Validation

User-reported:

- focal tests: **186 passed**
- full suite: **915 passed, 2 skipped, 7 warnings**
- exact four-file Scope Lock
- `git diff --check`: PASS
- no OpenAI call
- no live smoke
- origin commit: `6874eb8e4247dd0e47589a04ccfd6a3e612b1456`

## Result

**ACCEPTED.**

This closes the producer-contract mismatch identified offline. It does not prove which semantic invariant caused the historical twelfth live failure.

No thirteenth live smoke is authorized by this acceptance. Any further live synthetic execution requires fresh explicit user authorization.
