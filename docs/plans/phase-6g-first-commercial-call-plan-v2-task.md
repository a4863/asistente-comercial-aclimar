# Phase 6G First Commercial Call Revised Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-29
**Mode:** READ-ONLY / NO COMMERCIAL PROVIDER CALL

## Authority

Depends on:

- Global processing decision approved;
- protected localhost gate UI accepted;
- Phase 6F synthetic live provider plumbing accepted;
- first-commercial-rollout retry policy decision approved:
  one Analyze action, one email, up to two automatic provider attempts.

## Objective

Produce the exact operational plan for one controlled first commercial analysis using the existing stack and retry semantics.

This task does not authorize the call.

## Fixed retry contract

The plan must preserve the current adapter behavior:

- `max_retries == 1`;
- one operator Analyze action may cause up to two provider attempts;
- only transient classes may trigger the second attempt;
- ownership and commercial gate are rechecked before retry;
- no SDK internal retry is added;
- no retry config/code change is authorized.

Do not require exact provider-attempt counting after the call.

The rollout success criteria are based on:
- one operator Analyze click;
- one selected email;
- bounded final result;
- expected local state;
- no unauthorized external mutation;
- final gate blocked.

## Required preflight

Require confirmation of:

1. deployed branch/build is accepted 6G UI commit or later accepted descendant;
2. tracked working tree clean;
3. exactly one operational process;
4. no reload / no multiple workers;
5. exclusive lock owned;
6. startup recovery/cutover healthy;
7. status operational=ready;
8. AI enabled;
9. provider=openai;
10. endpoint class=global;
11. expected approved model;
12. credential presence=present only;
13. commercial gate initially blocked;
14. no selected item already completed/in_progress/retry_required;
15. protected session/CSRF controls usable.

## Email selection

The operator must select exactly one existing eligible item shown as `ready` in the bounded selector.

Do not:
- type internal IDs;
- select arbitrary mailbox content;
- choose a second email;
- copy email body into documentation.

Review only safe selector metadata necessary to identify an appropriate first test.

## Exact rollout sequence

1. Confirm gate blocked.
2. Click `Enable commercial analysis (Global)` once.
3. Verify status authorized.
4. Click `Analyze` exactly once on the single selected ready email.
5. Do not click Analyze again regardless of delay.
6. Do not click Retry analysis in this rollout.
7. Allow the adapter to complete its normal bounded execution, including at most one automatic transient retry.
8. Record only the bounded UI outcome.
9. Immediately click Disable commercial analysis.
10. Verify status blocked.

If any expected state/control is unavailable, STOP.

## Success criteria

Primary success:

- bounded result `completed`;
- exactly one operator Analyze action;
- selected email/run completes locally;
- expected evidence/provenance persists;
- no unauthorized external action occurs;
- gate is verified blocked after completion.

`completed_replay` does not count as first-live-commercial success because it may make no provider call.

Do not require proof of one vs two provider attempts.

## Failure / STOP outcomes

At minimum:

- blocked
- unavailable
- disabled
- credential_missing
- credential_unavailable
- invalid_security
- invalid_request
- invalid_target
- no_analyzable_body
- in_progress
- retry_required
- retry_not_available
- failed_retryable
- stale_retryable
- completed_replay
- any bounded provider diagnostic
- ownership/readiness loss
- inability to disable gate
- unexpected external mutation
- unexpected data category

On any such outcome:

- do not click Analyze again;
- do not click Retry analysis;
- disable gate if possible;
- record bounded outcome only;
- STOP for review.

## Post-call verification

Without exposing raw commercial content, verify:

- gate blocked;
- one manual analysis run for the selected initial action is in the expected final state;
- evidence/provenance present only if completed;
- no unauthorized external action record;
- no scheduler/background trigger;
- no email/CRM/Calendar/WhatsApp mutation.

Do not print:
- source body;
- raw provider JSON;
- prompt;
- credential;
- internal digests;
- exception details.

## Rollback

If a provider call is in flight:

- disabling gate can prevent a later automatic retry once the adapter reaches its recheck;
- it does not recall already transmitted data;
- do not kill the process merely to stop a dispatched request;
- allow already-sent work to settle safely;
- if UI disable is unavailable after settlement, stop/restart the worker; fresh gate is OFF.

## Code-change decision

The plan must determine whether any code change is needed.

Expected answer: no code change should be required because the retry-policy contradiction is resolved by the explicit Option A decision.

If any code change is required, verdict must be STOP and explain why.

## Deliverable

Create only:

`docs/plans/phase-6g-first-commercial-call-plan-v2.md`

Include:
- exact operator preflight;
- exact click/order sequence;
- retry semantics;
- success/failure criteria;
- rollback;
- post-call verification;
- explicit no-manual-retry rule;
- whether code change is needed;
- verdict: READY FOR ONE-SHOT AUTHORIZATION or STOP.

No code changes.
No OpenAI call.
No commercial data transmission.

Commit:

Plan phase 6G first commercial call v2

Push only origin/codex-work.
