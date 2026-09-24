# Phase 5C Correction Task — 429 Retry Classification

**Status:** Approved for Implement
**Date:** 2026-09-24
**Parent implementation:** 54acbd5fe1e64bceb2213402dfa2a02b1a881ce2
**Parent task:** docs/plans/implementation-phase-5c-task.md

## Finding

Static review found one behavioral mismatch with the approved Phase 5C retry contract.

Current implementation treats an HTTP 429 with no recognized provider code as `provider_quota` and does not retry.

Approved behavior is:
- explicit quota/billing exhaustion: no retry;
- ordinary rate limiting: retry once if monotonic soft-deadline budget permits.

Therefore an unclassified 429 must not be presumed to be quota exhaustion.

## Exact Scope Lock

Modify only:

1. app/integrations/openai_analysis.py
2. test/test_openai_analysis.py

No other tracked file may change.

## Required correction

For HTTP 429 / RateLimitError:

1. If a verified provider error code explicitly identifies quota/billing exhaustion, classify as `provider_quota`, non-transient, no retry.
2. If a verified provider error code identifies ordinary rate limiting, classify as transient and permit one retry within the remaining monotonic budget.
3. If the 429 has no recognized code, default conservatively to **ordinary rate limiting**, not quota exhaustion, and permit one retry within the remaining budget.
4. Do not inspect or expose raw provider error text.
5. Preserve existing Retry-After handling.
6. Preserve max two total attempts.
7. Preserve max_retries=0 in the SDK.
8. No other retry categories should change.

## Tests

Update/add tests proving:
- 429 + explicit quota code => no retry, provider_quota;
- 429 + explicit rate-limit code => one retry;
- 429 + no code => one retry;
- second 429 stops after two total attempts;
- Retry-After exceeding remaining budget prevents the second attempt;
- no raw provider error/secret leaks.

## Restrictions

- no pyproject change;
- no config/credential/domain/service/persistence change;
- no network;
- no real API key;
- no live OpenAI call;
- no activation;
- no unrelated refactor.

## Validation

Run:

python -m pytest test/test_openai_analysis.py test/test_ai_schema.py test/test_config.py test/test_credentials.py

Then:

python -m pytest

Tracked diff must contain exactly:
- app/integrations/openai_analysis.py
- test/test_openai_analysis.py

## Completion

Commit:

Fix phase 5C rate limit retry classification

Push only origin/codex-work.
