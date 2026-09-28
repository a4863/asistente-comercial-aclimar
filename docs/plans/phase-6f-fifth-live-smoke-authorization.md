# Phase 6F — Fifth Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-28

## User authorization

The user explicitly authorized a fifth live Phase 6F synthetic smoke attempt.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- current configured provider/model/endpoint;
- current Windows Credential Manager credential;
- current lock/ownership checks;
- accepted bounded diagnostics including `request_schema_failure` and `provider_non_http_failure`.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, payload, timeout or retry policy;
- a sixth live attempt;
- operator retry after any failure;
- raw provider error disclosure.

## Execution rule

Run exactly once after local preflight passes.

Outcomes:
- `passed` -> Phase 6F candidate for acceptance.
- any `smoke_failed:<allowlisted_code>` -> STOP; do not retry.
- `smoke_failed`, `disabled`, `lock_unavailable`, `unavailable` or any other failure -> STOP; do not retry.

A failed fifth attempt consumes this authorization.
