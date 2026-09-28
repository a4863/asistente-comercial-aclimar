# Phase 6F — Hook Observability Client Lifetime Decision

**Status:** DECISION REQUIRED
**Date:** 2026-09-28
**Source:** docs/plans/phase-6f-hook-observability-analysis.md — STOP

## Established findings

The public-hook design is technically viable for bounded lifecycle observation.

Using:
- `openai.DefaultHttpxClient`
- the same base URL
- the same initial timeout
- public HTTPX2 request/response event hooks
- no custom transport

preserves the inspected effective HTTP behavior for:
- `trust_env`
- environment proxy discovery
- default transport selection
- TLS verification defaults
- SDK connection limits/pooling defaults
- redirects
- per-request timeout override
- SDK `max_retries=0`

The remaining parity gap is client ownership/lifetime.

## Current behavior

When the SDK creates its own sync HTTP client, it uses an internal wrapper that has finalizer-based cleanup.

The current adapter:
- creates one OpenAI client per `_execute()`;
- reuses it across the adapter's own retry loop;
- does not explicitly close it.

## Proposed lifetime contract

Approve deterministic closure of the SDK client at the end of each `_execute()`.

Requirements:

- create exactly one SDK client per `_execute()`;
- reuse that client across all adapter attempts in that operation;
- close exactly once after the operation completes or fails;
- closure must happen on:
  - success;
  - non-transient provider failure;
  - exhausted retry;
  - authorization revocation during retry;
  - timeout;
  - response/output validation failure;
  - any other path after successful client construction;
- do not close before the adapter retry loop finishes;
- do not alter request/retry/deadline semantics;
- no persistence/logging/content inspection;
- close failures must not leak raw exception data or overwrite a prior primary bounded failure without an explicitly designed policy.

## Fake/test contract

All `client_factory` fakes used in tests must expose the same close-capable public contract.

No production-only bypass is acceptable.

## Consequence for hook observability

If this lifetime contract is approved, planning may proceed for:

- public request/response hooks;
- ephemeral per-attempt phase state;
- fixed bounded Unicode hook-state diagnostics;
- deterministic client closure.

Conditional planning Scope Lock identified by analysis:

1. `app/integrations/openai_analysis.py`
2. `test/test_openai_analysis.py`
3. `app/integrations/ai_smoke_cli.py`
4. `test/test_ai_smoke_cli.py`
5. `test/test_email_analysis_service.py`
6. `test/test_security.py`

No seventh file without STOP/re-approval.

## Not authorized

This document does not authorize:
- implementation;
- live smoke;
- provider call;
- credential inspection;
- dependency change;
- transport wrapping;
- private API/monkeypatching.

A separate plan is required after explicit approval.
