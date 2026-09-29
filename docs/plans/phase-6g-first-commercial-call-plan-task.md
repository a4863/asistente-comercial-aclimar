# Phase 6G First Commercial Call Rollout Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-29
**Mode:** READ-ONLY / NO COMMERCIAL PROVIDER CALL

## Authority

Depends on:

- Global processing decision approved;
- protected localhost gate UI accepted;
- Phase 6F synthetic live provider plumbing accepted;
- existing protected manual email analysis route accepted.

## Objective

Produce the exact operational plan for one controlled first commercial analysis of one operator-selected existing eligible email.

This task does not authorize the call.

## Planning requirements

Define the exact preflight, operator sequence, success criteria, STOP conditions, rollback and post-call verification for one first real commercial request.

Use only the existing accepted mechanisms:

- controlled operational worker;
- status page;
- protected gate enable/disable controls;
- bounded existing email selector;
- `POST /analysis/email`;
- existing initial/retry semantics;
- existing projection/minimization;
- existing audit/persistence/evidence contracts.

Do not design new code unless inspection demonstrates a blocker.

## Preflight

The plan must require confirmation of:

1. branch/build at the accepted 6G UI commit or later accepted descendant;
2. clean tracked working tree;
3. exactly one operational process;
4. no reload / no multiple workers;
5. exclusive operational lock owned;
6. startup recovery/cutover succeeds;
7. status reports operational=ready;
8. AI enabled;
9. provider=openai;
10. endpoint class=global;
11. expected approved model;
12. credential presence=present only, never inspect secret;
13. commercial gate initially blocked;
14. no unexpected pending/in-progress/reserved analysis state requiring intervention;
15. protected session/CSRF control available.

## Email selection

The plan must require the operator to select exactly one email from the existing bounded selector.

Do not:
- type or paste an internal source ID;
- broaden to multiple emails manually;
- select arbitrary mailbox content outside the existing eligibility rules.

Before clicking Analyze, the operator should review only the selector's safe metadata and confirm it is an appropriate first commercial test.

Do not copy the email body into planning documentation.

## Gate sequence

Required sequence:

1. status = blocked;
2. explicitly click Enable commercial analysis (Global);
3. verify status = authorized;
4. immediately execute exactly one initial Analyze action on the selected eligible email;
5. no second email;
6. no retry during the same rollout unless separately approved after seeing a bounded retry-required/failure state;
7. after the call settles, immediately disable the commercial gate;
8. verify status = blocked.

If enable/disable control is unavailable or status does not match, STOP.

## Success criteria

Define success narrowly.

Preferred successful first-commercial-call result:

- one `completed` analysis result;
- exactly one live provider disclosure initiated for the selected analysis run;
- local analysis/evidence/provenance persistence completes normally;
- no external mutation follows;
- no email send/move/archive;
- no CRM/Calendar/WhatsApp action;
- gate can be disabled and verified blocked afterward.

A `completed_replay` must NOT count as validating the first real commercial provider disclosure.

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
- any provider diagnostic
- ownership/readiness loss
- inability to disable the gate afterward
- unexpected external mutation
- unexpected data category

On any bounded failure:
- do not click Analyze again;
- do not retry;
- disable gate if possible;
- record only bounded outcome;
- STOP for review.

## Post-call verification

Plan how to verify, without exposing raw commercial content:

- gate reports blocked;
- analysis result is completed or bounded failure;
- exactly expected run state exists locally;
- evidence/provenance exists only if completed;
- no unauthorized external action records;
- no second provider attempt;
- no scheduler/background work;
- no email/CRM/Calendar mutation.

Do not require printing source body, raw provider JSON, credential or prompt.

## Rollback

If the call is already in flight:
- disabling gate prevents new attempts/retries but does not recall transmitted data;
- allow already-sent request to settle;
- if UI disable is unavailable, stop worker only after in-flight work settles safely;
- restart returns gate OFF.

## Decision/output

Create only:

`docs/plans/phase-6g-first-commercial-call-plan.md`

Include:
- exact operator preflight;
- exact click/order sequence;
- bounded acceptable outputs;
- explicit no-retry rule for first rollout;
- success/failure criteria;
- rollback;
- post-call verification;
- whether any code change is needed;
- verdict: READY FOR ONE-SHOT AUTHORIZATION or STOP.

No code changes.
No OpenAI call.
No commercial data transmission.

Commit:

Plan phase 6G first commercial call

Push only origin/codex-work.
