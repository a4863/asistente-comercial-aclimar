# Phase 6F — Tenth Live Synthetic Smoke Failure

**Status:** FAILED / TENTH AUTHORIZATION CONSUMED
**Date:** 2026-09-28

## Result

Tenth explicitly authorized live synthetic smoke returned:

`smoke_failed:invalid_output`

Exit code:

`1`

No retry is authorized.

## What is now established

The prior pre-request Unicode failure did not recur.

The adapter reached a later stage in which `client.responses.create(**request_kwargs)` returned successfully to application code, and the bounded failure was raised during application-side response/output validation.

Under the current implementation, `invalid_output` can arise after SDK return from:
- `_structured_text(response)`; or
- JSON parsing / `decode_analysis_response(...)` validation after text extraction.

This result does **not** disclose or establish:
- the raw provider response;
- the returned text;
- whether the response was semantically close to valid;
- whether the model, schema, SDK response object shape, or application decoder caused the mismatch.

## Status

- Phase 6F remains NOT ACCEPTED.
- Commercial activation remains unauthorized.
- Do not repeat the live smoke.
- An eleventh live attempt requires fresh explicit approval after offline invalid-output analysis.
