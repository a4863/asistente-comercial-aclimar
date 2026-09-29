# Phase 6F — Eleventh Live Synthetic Smoke Failure

**Status:** FAILED / ELEVENTH AUTHORIZATION CONSUMED
**Date:** 2026-09-29

## Result

Eleventh explicitly authorized live synthetic smoke returned:

`smoke_failed:invalid_output`

Exit code:

`1`

No retry is authorized.

## What is now established

The split-`output_text` extraction correction did not make the live synthetic smoke pass.

The current bounded `invalid_output` still conflates multiple post-SDK-return stages, including:

- response-envelope rejection in `_structured_text()`;
- JSON parsing failure after text extraction;
- application semantic/schema/evidence rejection in `decode_analysis_response()`.

This result does **not** establish which stage failed.

## Status

- Phase 6F remains NOT ACCEPTED.
- Commercial activation remains unauthorized.
- Do not repeat the live smoke.
- A twelfth live attempt requires fresh explicit approval after offline bounded stage analysis.
