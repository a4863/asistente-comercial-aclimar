# Phase 6G — First Commercial Rollout Retry Policy Decision

**Status:** APPROVED DECISION
**Date:** 2026-09-29

## User decision

The user explicitly approved:

> Apruebo Opción A: un solo Analyze sobre un solo email, permitiendo hasta dos intentos automáticos del proveedor.

## Approved rollout contract

For the first commercial rollout:

- exactly one operator-selected eligible email;
- exactly one initial `Analyze` action;
- no second email;
- no manual retry action;
- the existing adapter transient retry policy remains unchanged;
- one initial Analyze may therefore cause up to two provider attempts using the same minimized input;
- a second provider attempt is allowed only through the already-implemented automatic retry path for transient failures;
- no separate operator action authorizes that automatic retry;
- after the bounded result settles, the commercial gate must be disabled and verified blocked.

## Explicit exclusions

This decision does NOT authorize:

- a second Analyze click;
- `/analysis/email/retry`;
- another email;
- scheduler/background analysis;
- force reanalysis;
- changing retry configuration;
- provider-attempt instrumentation;
- any commercial call before a separately approved one-shot rollout authorization.

## Verification boundary

The first rollout will verify:

- one selected email;
- one operator Analyze action;
- bounded final result;
- expected local run/provenance state;
- no unauthorized external mutation;
- gate returned to blocked.

It will NOT require proving whether the adapter used one or two provider attempts internally.

No commercial provider call is authorized by this decision alone.
