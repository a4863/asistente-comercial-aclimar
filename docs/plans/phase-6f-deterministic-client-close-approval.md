# Phase 6F — Deterministic OpenAI Client Closure Approval

**Status:** APPROVED FOR PLANNING
**Date:** 2026-09-28

## User decision

The user explicitly approved deterministic closure of the OpenAI client.

## Approved lifetime contract

For each `OpenAIAnalysis._execute()` operation:

- construct exactly one SDK client;
- reuse that client across all adapter-level attempts/retries in that operation;
- close it exactly once after the operation completes or fails;
- do not close it before the retry loop finishes.

Closure must cover:
- success;
- non-transient provider failure;
- exhausted retry;
- timeout;
- authorization revocation during retry;
- response/output validation failure;
- any other path after successful client construction.

## Required behavior

- request/retry/deadline semantics remain unchanged;
- no provider call is authorized by this decision;
- no content is logged/persisted;
- close failures must be handled by a bounded policy defined in the implementation plan;
- a close failure must not expose raw exception data.

## Test/fake contract

All test `client_factory` fakes affected by the new lifetime contract must implement a close-capable public interface.

No production-only bypass is permitted.

## Not authorized

This approval does not itself authorize:
- implementation;
- live smoke;
- provider call;
- dependency/package changes;
- transport wrapping;
- private SDK/httpx2 monkeypatching.

A separate implementation plan is required.
