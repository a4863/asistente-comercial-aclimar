# Phase 6F — Eighth Live Synthetic Smoke Failure

**Status:** FAILED / EIGHTH AUTHORIZATION CONSUMED
**Date:** 2026-09-28

## Result

Eighth explicitly authorized live synthetic smoke returned:

`smoke_failed:provider_unicode_error_family`

Exit code:

`1`

No retry is authorized.

## What is now established

The exception raised inside `client.responses.create(**request_kwargs)` is a residual `UnicodeError` family member.

It was not classified as:
- API timeout/connection/status/auth/quota branches;
- exact APIResponseValidationError;
- exact JSONDecodeError;
- exact TypeError;
- exact ValueError;
- exact RuntimeError;
- residual OpenAIError;
- residual httpx2.RequestError;
- residual OSError.

It therefore matched:

`isinstance(error, UnicodeError)`

This does **not** identify the concrete Unicode subclass, exact source path, response origin, or dispatch stage.

## Status

- Phase 6F remains NOT ACCEPTED.
- Commercial activation remains unauthorized.
- Do not retry live.
- A ninth live attempt requires fresh explicit approval after offline Unicode-path analysis.
