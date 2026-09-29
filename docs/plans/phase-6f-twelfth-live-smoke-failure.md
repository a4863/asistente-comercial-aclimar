# Phase 6F — Twelfth Live Synthetic Smoke Failure

**Status:** FAILED / TWELFTH AUTHORIZATION CONSUMED
**Date:** 2026-09-29

## Result

Twelfth explicitly authorized live synthetic smoke returned:

`smoke_failed:provider_output_semantic_failure`

Exit code:

`1`

No retry is authorized.

## What is now established

The live synthetic response successfully passed:

- SDK return to application code;
- response-envelope extraction;
- JSON parsing.

The bounded rejection occurred inside:

`decode_analysis_response(parsed, projection)`

This narrows the issue to the local structural/semantic/evidence/domain validation layer.

This result does **not** reveal:
- which field or invariant failed;
- the raw JSON;
- the provider response text;
- whether the model output was nearly valid or fundamentally incompatible.

## Status

- Phase 6F remains NOT ACCEPTED.
- Commercial activation remains unauthorized.
- Do not repeat the live smoke.
- A thirteenth live attempt requires fresh explicit approval after offline semantic-failure analysis.
