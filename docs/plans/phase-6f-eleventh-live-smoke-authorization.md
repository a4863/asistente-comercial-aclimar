# Phase 6F — Eleventh Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-29

## User authorization

The user explicitly authorized an eleventh live Phase 6F synthetic smoke attempt.

## Precondition state

Before this authorization:
- hook-level Unicode observability was accepted;
- deterministic client closure was accepted;
- pre-request Unicode operator remediation was completed;
- the stored API credential was freshly reset through the secure CLI;
- optional OpenAI SDK environment variables relevant to prior analysis were confirmed absent;
- split `output_text` aggregation was implemented and accepted.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- current configured provider/model/endpoint;
- current Windows Credential Manager credential;
- current lock/ownership checks;
- current bounded diagnostics and parser behavior.

## Not authorized

- commercial data;
- commercial activation gate;
- changing model, endpoint, schema, payload, timeout or retry policy;
- a twelfth live attempt;
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

A failed eleventh attempt consumes this authorization.
