# Phase 6F — Second Live Synthetic Smoke Failure

**Status:** FAILED / SECOND AUTHORIZATION CONSUMED
**Date:** 2026-09-28

## Result

Second explicitly authorized live synthetic smoke execution returned:

`smoke_failed:provider_failure`

Exit code:

`1`

Tracked repository status was clean before execution.

No retry is authorized.

## Interpretation

The adapter's current bounded mapping rules exclude several categories because they would have produced different codes:

- provider_auth
- provider_quota
- provider_transient_exhausted
- timeout
- provider_incomplete
- provider_refusal
- invalid_output
- provider_unavailable
- credential_missing
- credential_unavailable
- invalid_configuration

Therefore `provider_failure` indicates a non-transient provider/SDK failure not currently mapped more specifically.

Do not infer a root cause such as model ID, schema, endpoint, billing or credential correctness from this code alone.

## Security/operational status

- Phase 6F remains NOT ACCEPTED.
- Do not retry.
- Commercial activation remains OFF/unauthorized.
- Do not expose raw provider response bodies or secrets.
- A third live attempt requires a new explicit user authorization after offline diagnostic work.
