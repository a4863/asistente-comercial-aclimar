# Phase 6F — Unicode Phase Observability Decision

**Status:** DECISION REQUIRED
**Date:** 2026-09-28
**Source:** docs/plans/phase-6f-unicode-path-analysis.md — STOP

## Problem

The eighth live smoke returned:

`provider_unicode_error_family`

Offline analysis reproduced two distinct paths that both produce that same family:

1. request-side Unicode failure before mock dispatch;
2. response-side Unicode failure while decoding response bytes after one mock dispatch.

The current application wraps the whole `Responses.create()` call in one catch boundary and has no trusted phase marker.

Therefore the current implementation cannot safely distinguish:
- request/build Unicode failure;
- response/decode Unicode failure.

## Decision options

### Option A — add bounded phase observability

Approve design work for a non-content-bearing phase marker around the SDK transport lifecycle.

Requirements:
- ephemeral only;
- no persistence;
- no logging;
- no URL/header/body/request/credential capture;
- no exception class/message/reflection;
- no change to model/endpoint/schema/payload/timeout/retries;
- no commercial data;
- no live call during design/implementation;
- phase value must be derived from a proven transport/SDK boundary, not guessed from exception type.

The design must define at minimum:
- pre-dispatch;
- response-received boundary;
- treatment of failures after response receipt but before SDK return;
- how the marker is reset per attempt/retry;
- how ownership/authorization/retry semantics remain unchanged.

Only after offline acceptance could new fixed codes be considered, for example request-side versus response-side Unicode failure. Exact names are not yet approved.

### Option B — retain coarse Unicode family

Keep:
- `provider_unicode_error_family`

Do not add phase instrumentation.
Do not run further live diagnostics to distinguish request versus response phase.

Under this option Phase 6F remains bounded but cannot identify whether the Unicode failure occurs before or after dispatch.

## Recommendation

Proceed with **Option A** only if the user wants to continue root-cause isolation. It adds a small observability contract but can remain non-content-bearing and offline-testable.

If minimizing code/diagnostic complexity is preferred, choose **Option B** and stop further live debugging at this layer.

## Not authorized by this document

- implementation;
- live smoke;
- provider call;
- credential inspection;
- package change;
- raw diagnostic capture.

A separate analysis/plan is required if Option A is approved.
