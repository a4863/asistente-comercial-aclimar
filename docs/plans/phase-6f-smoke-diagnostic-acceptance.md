# Phase 6F Smoke Diagnostic Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-28

## Implementation

Accepted commit:
- `42146a4419e871440da5a3c1ce5290ed96291845`

Exactly two files changed:
- `app/integrations/ai_smoke_cli.py`
- `test/test_ai_smoke_cli.py`

## Accepted behavior

The synthetic smoke CLI now exposes only this exact allowlist:

- credential_missing
- credential_unavailable
- provider_unavailable
- provider_auth
- provider_quota
- provider_transient_exhausted
- provider_failure
- timeout
- provider_incomplete
- provider_refusal
- invalid_output
- invalid_configuration

For allowlisted codes:
- stdout: `smoke_failed:<code>`
- exit: 1

All excluded/internal/unknown/non-string/unhashable values collapse to:
- stdout: `smoke_failed`
- exit: 1

Existing outputs remain unchanged:
- `passed`
- `disabled`
- `lock_unavailable`
- `unavailable`
- invalid command/help behavior

The CLI never reflects raw exception/provider/body/secret/path/model/endpoint data.

## Validation

User-reported:
- focal tests: 90 passed
- full suite: 770 passed, 2 skipped, 7 warnings
- exact two-file diff
- no live smoke
- no OpenAI call

GitHub review confirms the implementation matches the approved diagnostic contract and Scope Lock.

## Result

**ACCEPTED.**

A new live smoke is still not authorized. Any further live attempt requires fresh explicit approval.
