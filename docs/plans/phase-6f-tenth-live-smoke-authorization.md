# Phase 6F — Tenth Live Synthetic Smoke Authorization

**Status:** AUTHORIZED — ONE LIVE ATTEMPT
**Date:** 2026-09-28

## User authorization

The user explicitly authorized a tenth live Phase 6F synthetic smoke attempt.

## Precondition state

Operator remediation completed before this authorization:
- optional OpenAI SDK environment variables `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`, and `OPENAI_CUSTOM_HEADERS` were confirmed absent;
- stored API credential was deleted and freshly re-entered through the secure interactive credential CLI;
- credential status returned `present`.

The organization/project identifiers mentioned by the user in chat are not persisted by this authorization and are not added to environment/configuration for this attempt.

## Scope

Authorized exactly once:
- existing `asistente-aclimar-ai-smoke` command;
- fixed synthetic payload only;
- current configured provider/model/endpoint;
- current Windows Credential Manager credential;
- current lock/ownership checks;
- current bounded hook-level diagnostics.

## Not authorized

- setting organization/project environment variables;
- changing config;
- commercial data;
- commercial activation;
- changing model, endpoint, schema, payload, timeout or retry policy;
- an eleventh live attempt;
- retry after any failure;
- raw provider/exception disclosure.

## Execution rule

Run exactly once after standard local preflight passes.

Outcomes:
- `passed` -> Phase 6F candidate for acceptance.
- any `smoke_failed:<allowlisted_code>` -> STOP; do not retry.
- any other failure -> STOP; do not retry.

A failed tenth attempt consumes this authorization.
