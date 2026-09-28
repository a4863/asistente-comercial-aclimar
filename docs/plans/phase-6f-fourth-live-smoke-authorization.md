# Phase 6F — Fourth Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-28

## User authorization

The user explicitly requested another live Phase 6F synthetic smoke because the OpenAI API key may not have been activated during the previous attempts.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- current configured provider/model/endpoint;
- current Windows Credential Manager credential;
- current accepted bounded diagnostics;
- existing lock/ownership checks.

## Context

The prior third smoke returned:
- `smoke_failed:provider_non_http_failure`

Subsequent offline analysis found that installed `openai==3.17.0` can construct and serialize the exact synthetic request using a no-network transport.

This authorization does not assert that credential activation caused the previous failure. It allows exactly one retest after the user states the key may now be activated.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, payload, timeout or retry policy;
- a fifth live attempt;
- operator retry after any failure;
- raw provider error disclosure.

## Execution rule

Run exactly once after preflight passes.

Outcomes:
- `passed` -> Phase 6F candidate for acceptance.
- any `smoke_failed:<allowlisted_code>` -> STOP; do not retry.
- `smoke_failed`, `disabled`, `lock_unavailable`, `unavailable` or any other failure -> STOP; do not retry.

A failed fourth attempt consumes this authorization.
