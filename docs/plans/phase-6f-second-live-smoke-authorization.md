# Phase 6F — Second Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-28

## User authorization

The user explicitly authorized a second live Phase 6F synthetic smoke attempt.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- existing configured provider/model/endpoint;
- existing Windows Credential Manager credential;
- existing lock/ownership checks;
- bounded diagnostic output accepted in commit `42146a4419e871440da5a3c1ce5290ed96291845`.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, timeout or retry policy;
- a third live attempt;
- retries by the operator after any failure;
- exposing raw provider errors or secrets.

## Execution rule

Run exactly once after local preflight passes.

Expected outcomes:
- `passed` -> Phase 6F candidate for acceptance.
- `smoke_failed:<allowlisted_code>` -> STOP; do not retry.
- `smoke_failed`, `disabled`, `lock_unavailable`, `unavailable` or any other failure -> STOP; do not retry.

A failed second attempt consumes this authorization and requires fresh approval for any further live call.
