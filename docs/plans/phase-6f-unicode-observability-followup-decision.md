# Phase 6F — Unicode Observability Follow-up Decision

**Status:** DECISION REQUIRED
**Date:** 2026-09-28
**Source:** docs/plans/phase-6f-unicode-phase-observability-analysis.md — STOP

## Established constraint

No inspected supported mechanism simultaneously:
- proves transport dispatch started;
- proves response received;
- preserves the current default HTTPX2/OpenAI transport/proxy semantics.

An explicit transport wrapper would alter environment-proxy selection because HTTPX2 only enables its normal environment-proxy discovery when `transport is None`.

Therefore exact dispatch instrumentation is not approved.

## Safe next option — hook-level observability

Use only supported HTTPX2 request/response event hooks and define deliberately weaker semantics:

- `before_request_hook`: the SDK call failed before the request hook fired.
- `request_hook_reached`: HTTPX2 entered its send lifecycle far enough to invoke the request hook.
- `response_hook_reached`: HTTPX2 produced a response far enough to invoke the response hook.

These states MUST NOT be described as:
- request dispatched;
- provider contacted;
- provider received request;
- response decoded;
- response originated from OpenAI.

The request hook occurs before transport handoff, so `request_hook_reached` is not a dispatch marker.

## Why this option is preferred

It can potentially provide useful phase narrowing using public lifecycle hooks without wrapping the transport itself.

Before implementation, a dedicated analysis must still prove:
- how to instantiate the SDK's default HTTP client with hooks while preserving the same SDK defaults;
- environment proxy behavior;
- trust_env behavior;
- TLS verification behavior;
- connection limits/pooling;
- redirect behavior;
- timeout semantics;
- client ownership/lifetime;
- adapter retry reset semantics.

If those cannot be proven equivalent, STOP.

## Alternative

Retain only:
- `provider_unicode_error_family`

and end Phase 6F diagnosis at the current bounded level.

## Not authorized

This document does not authorize:
- implementation;
- live smoke;
- transport wrapping;
- provider call;
- dependency change;
- credential inspection.

A separate explicit user decision is required.
