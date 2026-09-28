# Phase 6F — API Dashboard Evidence

**Date:** 2026-09-28
**Status:** DIAGNOSTIC EVIDENCE

The user supplied current OpenAI platform screenshots after five live synthetic smoke attempts.

Observed on the API-key page:
- key status: Active
- last used: Never
- monthly spend: $0.00
- permissions: All

Observed on the project page:
- project residency: Global
- data retention: Standard Retention
- monthly spend: $0

## Diagnostic interpretation

This is strong evidence that the five smoke attempts did not reach OpenAI far enough for the API key to be recorded as used.

It is consistent with the current bounded result:

`provider_non_http_failure`

and materially shifts the investigation toward the local transport/client path before provider processing/authentication.

Priority areas for the ongoing SDK non-HTTP analysis:
- DNS resolution
- TLS/certificate validation
- proxy/environment interaction
- firewall/network interception
- installed httpx/httpx2 transport compatibility
- Python 3.13 networking/runtime compatibility
- OpenAI SDK exception translation before HTTP/APIStatusError creation

Do not infer an exact cause from dashboard telemetry alone; UI counters may have propagation delay.

## Commercial-data boundary

The project screenshots show:
- residency: Global
- retention: Standard Retention

Therefore this evidence does not authorize commercial-data activation. Phase 6F remains synthetic-only.

No additional live call is authorized by this note.
