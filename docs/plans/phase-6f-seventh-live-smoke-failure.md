# Phase 6F — Seventh Live Synthetic Smoke Failure

**Status:** FAILED / SEVENTH AUTHORIZATION CONSUMED
**Date:** 2026-09-28

## Result

Seventh explicitly authorized live synthetic smoke returned:

`smoke_failed:provider_value_subclass_family`

Exit code:

`1`

No retry is authorized.

## What is now established

The exception raised inside `client.responses.create(**request_kwargs)` is a residual subclass of `ValueError`.

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

It therefore matched the approved residual `isinstance(error, ValueError)` family branch.

This does **not** identify the concrete subclass, source, root cause, or dispatch stage.

## Status

- Phase 6F remains NOT ACCEPTED.
- Commercial activation remains unauthorized.
- Do not retry live.
- An eighth live attempt requires fresh explicit approval after offline narrowing of the ValueError-subclass family.
