# Phase 6F — Twelfth Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-29

## User authorization

The user explicitly authorized a twelfth live Phase 6F synthetic smoke attempt.

## Precondition state

Before this authorization:
- hook-level Unicode observability was accepted;
- deterministic client closure was accepted;
- pre-request Unicode operator remediation was completed;
- split output-text aggregation was accepted;
- post-SDK output-stage diagnostics were implemented and accepted.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- current configured provider/model/endpoint;
- current Windows Credential Manager credential;
- current lock/ownership checks;
- current bounded hook and post-output stage diagnostics.

## Expected bounded post-return outcomes

If output validation still fails, possible bounded codes include:

- `provider_output_envelope_failure`
- `provider_output_json_failure`
- `provider_output_semantic_failure`

These codes identify application validation stage only and MUST NOT be interpreted as provider fault or disclosure of response content.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, payload, timeout or retry policy;
- a thirteenth live attempt;
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

A failed twelfth attempt consumes this authorization.
