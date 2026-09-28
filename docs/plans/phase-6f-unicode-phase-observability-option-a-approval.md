# Phase 6F — Unicode Phase Observability Option A Approval

**Status:** APPROVED FOR ANALYSIS/DESIGN
**Date:** 2026-09-28

## User decision

The user explicitly approved **Option A** from:

`docs/plans/phase-6f-unicode-phase-observability-decision.md`

## Approved direction

Design a minimal, non-content-bearing, ephemeral phase observation mechanism capable of distinguishing at least:

- failure before request dispatch;
- failure after a response has been received.

The design must not infer phase from exception type alone.

## Mandatory security properties

The phase signal must:
- be process-local and ephemeral;
- not be persisted;
- not be logged;
- not contain URL, headers, body, request payload, response payload, credentials, model content, exception text, exception class name, or traceback;
- not expose arbitrary transport metadata;
- not change request content or retry semantics.

## Not yet approved

This approval does **not** authorize:
- code implementation;
- live smoke;
- provider call;
- credential inspection;
- package/dependency changes;
- transport instrumentation beyond analysis/design;
- new CLI diagnostic literals.

A separate analysis/design and explicit implementation approval are required.
