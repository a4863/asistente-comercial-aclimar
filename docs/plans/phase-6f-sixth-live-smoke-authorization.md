# Phase 6F — Sixth Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-28

## User authorization

The user explicitly authorized a sixth live Phase 6F synthetic smoke attempt.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- current configured provider/model/endpoint;
- current Windows Credential Manager credential;
- current lock/ownership checks;
- accepted bounded diagnostics including the latest SDK non-HTTP exception categories.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, payload, timeout or retry policy;
- a seventh live attempt;
- operator retry after any failure;
- raw provider error disclosure.

## Execution rule

Run exactly once after local preflight passes.

Outcomes:
- `passed` -> Phase 6F candidate for acceptance.
- any `smoke_failed:<allowlisted_code>` -> STOP; do not retry.
- `smoke_failed`, `disabled`, `lock_unavailable`, `unavailable` or any other failure -> STOP; do not retry.

A failed sixth attempt consumes this authorization.
