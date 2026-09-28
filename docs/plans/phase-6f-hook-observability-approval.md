# Phase 6F — Hook-Level Observability Approval

**Status:** APPROVED FOR ANALYSIS/DESIGN
**Date:** 2026-09-28

## User decision

The user explicitly approved hook-level observability from:

`docs/plans/phase-6f-unicode-observability-followup-decision.md`

## Approved semantic boundary

Only supported public HTTPX2 request/response event hooks may be considered.

The only permitted meanings are:

- `before_request_hook`: failure occurred before the request hook fired.
- `request_hook_reached`: HTTPX2 entered its send lifecycle far enough to invoke the request hook.
- `response_hook_reached`: HTTPX2 produced a response far enough to invoke the response hook.

These states MUST NOT be described as:
- request dispatched;
- provider contacted;
- provider received request;
- response decoded;
- response originated from OpenAI.

## Mandatory invariants

Any future design must preserve current production semantics for:
- environment proxy selection;
- trust_env;
- TLS verification;
- connection limits and pooling;
- redirect behavior;
- timeout semantics;
- client ownership/lifetime;
- adapter retry/reset behavior.

The hook callbacks must be:
- content-free;
- process-local;
- ephemeral;
- non-persistent;
- non-logging;
- non-blocking;
- free of URL/header/body/credential inspection.

## Not yet approved

This approval does not authorize:
- implementation;
- live smoke;
- provider call;
- credential inspection;
- dependency changes;
- transport wrapping;
- private SDK/HTTPX2 monkeypatching;
- new CLI diagnostic codes.

A separate analysis and explicit implementation approval are required.
