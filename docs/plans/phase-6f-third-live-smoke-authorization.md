# Phase 6F — Third Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-28

## User authorization

The user explicitly authorized a third live Phase 6F synthetic smoke attempt.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- existing configured provider/model/endpoint;
- existing Windows Credential Manager credential;
- existing lock/ownership checks;
- bounded diagnostics including the accepted provider-failure refinements from commit `731f1d49d0a13dd136b9dfbcd82127a48b31bc86`.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, payload, timeout or retry policy;
- a fourth live attempt;
- operator retry after any failure;
- exposing raw provider errors or secrets.

## Execution rule

Run exactly once after local preflight passes.

Expected outcomes:
- `passed` -> Phase 6F candidate for acceptance.
- any `smoke_failed:<allowlisted_code>` -> STOP; do not retry.
- `smoke_failed`, `disabled`, `lock_unavailable`, `unavailable` or any other failure -> STOP; do not retry.

A failed third attempt consumes this authorization and requires fresh approval for any further live call.
