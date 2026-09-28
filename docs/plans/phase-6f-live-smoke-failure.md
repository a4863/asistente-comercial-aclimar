# Phase 6F Live Synthetic Smoke — Failed Attempt

**Status:** FAILED / AUTHORIZATION CONSUMED
**Date:** 2026-09-28

## Execution result

The authorized one-time live synthetic smoke was executed once.

Observed bounded CLI output:

`smoke_failed`

No retry is authorized.

## What this proves

The command passed enough local preconditions to reach the existing smoke execution path and the adapter surfaced an `OpenAIAnalysisError` or a non-passing smoke result that the CLI collapsed to `smoke_failed`.

The current CLI intentionally hides the adapter's bounded error code, so the exact category is not recoverable from this output alone.

Possible bounded adapter categories include:
- provider_auth
- provider_quota
- provider_failure
- provider_transient_exhausted
- timeout
- provider_incomplete
- provider_refusal
- invalid_output
- credential_missing
- credential_unavailable
- invalid_configuration
- operational_ownership_required

This document does not claim which category occurred.

## Security status

- Do not retry the live smoke.
- Do not expose or log raw provider errors, response bodies, API keys or request content.
- Commercial activation remains unauthorized.
- Phase 6F is not accepted.

A second live attempt requires a new explicit user authorization after offline diagnostic hardening.
