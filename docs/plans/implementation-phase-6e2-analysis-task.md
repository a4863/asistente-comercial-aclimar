# Phase 6E2 Analysis Task — Protected Manual Commercial Analysis Trigger

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-25
**Depends on:** Phase 6E1 ACCEPTED
**Decisions:** D1, D2, D6, D8, D9, D12, D13
**Plan:** docs/plans/implementation-phase-6-plan.md

## Objective

Define the exact UI/request/composition contract for a manual local commercial-analysis trigger before implementation.

This is READ-ONLY analysis.

Do not modify production code, tests, config, templates, dependencies, persistence or credentials.

## Current invariants

- Commercial analysis is manual-only in Phase 6.
- `OpenAIAnalysis.analyze()` requires technical AI enabled, live operational ownership and commercial gate ON.
- Commercial gate defaults OFF and has no UI mutation control.
- 6E1 provides:
  - local signed session;
  - CSRF token helpers;
  - Host validation;
  - same-origin Origin validation;
  - `validate_protected_request()`.
- No state-changing commercial POST currently exists.
- Existing service entry point is `analyze_email_in_thread(...)`.
- Status page is currently the only local browser UI.
- No new dependency should be introduced merely to parse form bodies.
- Real commercial activation remains separately controlled; 6E2 must not silently authorize it.

## Questions to resolve

Analyze current code and recommend one exact design answering:

1. What browser UI should initiate manual analysis at this stage?
2. How does the user identify the target email:
   - account scope + source_record_id,
   - another existing identifier,
   - or a selectable existing record exposed safely by current code?
3. What exact POST route/path should be used?
4. What request representation should be used without adding a multipart/form dependency?
5. How is the CSRF token delivered to the browser and returned on POST without leaking it in URLs/logs?
6. How are Host and Origin checks applied?
7. Does the route require `operational_ready=True` and current lock ownership before constructing the adapter?
8. How should `OpenAIAnalysis` be composed with:
   - current app credential store;
   - current operational lock;
   - current process-local commercial gate?
9. What happens when commercial gate is OFF?
10. What happens when technical AI is disabled, credential missing, ownership unavailable, provider fails, input is invalid/stale, or analysis is already in progress/replayed?
11. What response should the browser receive: redirect, bounded JSON, or rendered status?
12. How do we prevent duplicate POST/reload from creating unintended repeated runs?
13. Which existing service/repository semantics already provide replay/idempotency and which must not be reinvented in the route?
14. Should force reanalysis be exposed now? Default answer should be NO unless current contracts require it.
15. What exact production/test files need modification?
16. Can the task remain migration-free, config-schema-free and dependency-free?
17. How can tests remain fully offline with no real commercial provider call?
18. Confirm that 6E2 does not add a control to turn the commercial gate ON.

## Preferred properties

Prefer:
- one explicit button/action initiated by the user;
- no background/scheduler trigger;
- CSRF sent in a request header or body, never query string;
- no secret/provider details in UI response;
- bounded status result;
- existing `analyze_email_in_thread` orchestration reused;
- current commercial gate state honored, never altered;
- operational lock passed directly as adapter ownership proof;
- no direct database access outside existing service/repository boundaries except what the service already uses;
- no force mode in first manual trigger;
- no new dependency.

## Security checks

The proposed design must preserve:

- Host and same-origin Origin validation;
- session-bound CSRF validation;
- operational ownership;
- gate OFF means no credential lookup/provider call;
- no request can supply alternate provider URL/model/credential reference;
- no browser-supplied payload is sent directly to OpenAI;
- browser identifies only an existing local analysis target;
- no raw provider error, API key, source body, digest or Win32 handle returned to browser;
- no GET causes analysis;
- no cross-origin POST causes analysis.

## STOP conditions

STOP and present alternatives if:
- there is no safe/user-meaningful way to select an existing target with the current UI/data surfaces;
- body parsing would require a new dependency unless a safe built-in representation is selected;
- the trigger requires changing the commercial activation policy;
- implementation would require persistence/model/migration changes;
- force/replay semantics are ambiguous.

## Deliverable

Create only:

`docs/plans/phase-6e2-trigger-analysis.md`

Include:
- current-state findings;
- candidate UI/request designs;
- rejected alternatives;
- recommended exact route and request contract;
- exact gate/ownership/readiness behavior;
- exact response semantics;
- exact proposed production/test Scope Lock;
- security invariants;
- offline test matrix;
- ambiguities/STOP findings;
- verdict: READY FOR PLAN or STOP.

Commit:

Analyze phase 6E2 manual trigger contract

Push only origin/codex-work.
