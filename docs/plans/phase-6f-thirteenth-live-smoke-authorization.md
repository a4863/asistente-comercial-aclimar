# Phase 6F — Thirteenth Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-29

## User authorization

The user explicitly authorized a thirteenth live Phase 6F synthetic smoke attempt.

## Precondition state

Before this authorization:
- hook-level Unicode observability was accepted;
- deterministic client closure was accepted;
- pre-request Unicode remediation was completed;
- split output-text aggregation was accepted;
- post-SDK output-stage diagnostics were accepted;
- semantic producer-contract alignment was implemented and accepted.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- current configured provider/model/endpoint;
- current Windows Credential Manager credential;
- current lock/ownership checks;
- current bounded diagnostics and semantic producer contract.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, payload, timeout or retry policy;
- a fourteenth live attempt;
- operator retry after any failure;
- raw provider/exception/response disclosure;
- credential inspection;
- adding organization/project environment variables for this attempt.

## Execution rule

Run exactly once after standard local preflight passes.

Outcomes:
- `passed` -> Phase 6F candidate for acceptance.
- any `smoke_failed:<allowlisted_code>` -> STOP; do not retry.
- any other failure -> STOP; do not retry.

A failed thirteenth attempt consumes this authorization.
