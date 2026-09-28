# Phase 6F — Ninth Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-28

## User authorization

The user explicitly authorized a ninth live Phase 6F synthetic smoke attempt.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- current configured provider/model/endpoint;
- current Windows Credential Manager credential;
- current lock/ownership checks;
- current bounded diagnostics, including hook-level Unicode codes and deterministic client close.

## Expected bounded Unicode outcomes

If the same Unicode-family failure recurs, possible bounded codes include:

- `provider_unicode_before_request_hook`
- `provider_unicode_request_hook_reached`
- `provider_unicode_response_hook_reached`
- defensive fallback `provider_unicode_error_family`

These labels MUST NOT be interpreted as proof of transport dispatch, provider contact, provider receipt, provider-generated response, or successful response decoding.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, payload, timeout or retry policy;
- a tenth live attempt;
- operator retry after any failure;
- raw provider/exception disclosure;
- credential inspection.

## Execution rule

Run exactly once after local preflight passes.

Outcomes:
- `passed` -> Phase 6F candidate for acceptance.
- any `smoke_failed:<allowlisted_code>` -> STOP; do not retry.
- `smoke_failed`, `disabled`, `lock_unavailable`, `unavailable` or any other failure -> STOP; do not retry.

A failed ninth attempt consumes this authorization.
