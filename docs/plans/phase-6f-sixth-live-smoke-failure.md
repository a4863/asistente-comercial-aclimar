# Phase 6F — Sixth Live Synthetic Smoke Failure

**Status:** FAILED / SIXTH AUTHORIZATION CONSUMED
**Date:** 2026-09-28

## Result

Sixth explicitly authorized live synthetic smoke returned:

`smoke_failed:provider_non_http_failure`

Exit code:

`1`

No retry is authorized.

## What is now excluded by bounded classification

The live exception did not match:
- OpenAI API status categories;
- OpenAI timeout category;
- OpenAI connection category;
- exact `openai.APIResponseValidationError`;
- exact `json.JSONDecodeError`;
- exact plain `TypeError`;
- exact plain `ValueError`;
- exact plain `RuntimeError`.

It therefore reached the generic non-HTTP fallback.

This does not identify the concrete class. It may be:
- a subclass of one of the tested built-ins;
- another OpenAI/httpx2/httpcore2/Pydantic/runtime exception;
- an unrelated exception escaping a request-build, transport, or response-processing path.

Do not infer pre-dispatch/post-dispatch or root cause from this result alone.

## Status

- Phase 6F remains NOT ACCEPTED.
- Commercial activation remains unauthorized.
- Do not retry live.
- A seventh live attempt requires fresh explicit approval after further offline analysis and bounded diagnostic design.
