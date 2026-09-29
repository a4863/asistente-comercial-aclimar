# Phase 6G — First Commercial One-Shot Authorization

**Status:** AUTHORIZED — ONE CONTROLLED COMMERCIAL ROLLOUT
**Date:** 2026-09-29

## User authorization

The user explicitly authorized the controlled first commercial rollout under the accepted Phase 6G v2 plan.

## Exact authorization scope

Authorized exactly once:

- one operator-selected existing eligible email in `ready` state;
- one initial `Analyze` click through the existing protected localhost UI;
- the existing adapter may perform zero or one automatic transient retry, for at most two provider attempts total, using the same minimized input;
- normal local analysis/evidence/provenance persistence;
- immediate protected gate disable after the bounded result settles.

## Not authorized

- a second target email;
- a second initial Analyze click;
- manual `Retry analysis`;
- `/analysis/email/retry`;
- force reanalysis;
- scheduler/background commercial analysis;
- a new synthetic smoke;
- provider/config/model/retry changes;
- external email/CRM/Calendar/WhatsApp mutation;
- any retry after a bounded failure without a new authorization.

## Required preflight

Before enabling the commercial gate, the operator must confirm:

- accepted build/branch or later accepted descendant;
- clean tracked working tree;
- exactly one operational worker;
- no reload or multiple workers;
- exclusive operational ownership;
- startup recovery/cutover healthy;
- status: operational=ready;
- AI enabled;
- provider=openai;
- endpoint class=global;
- approved model;
- credential presence=present;
- commercial=blocked;
- selected item is exactly one eligible `ready` email;
- protected session/CSRF controls are usable.

Any mismatch consumes no provider disclosure but blocks execution until reviewed.

## Exact execution sequence

1. Confirm `commercial=blocked`.
2. Click **Enable commercial analysis (Global)** once.
3. Confirm `commercial=authorized`.
4. Click **Analyze** exactly once on the single selected `ready` email.
5. Do not click Analyze again regardless of latency or uncertainty.
6. Do not click Retry analysis.
7. Allow the bounded result to settle; the existing adapter may make at most one automatic transient retry.
8. Record only the bounded UI outcome.
9. Click **Disable commercial analysis**.
10. Confirm `commercial=blocked`.

## Success / STOP

Candidate success requires:

- bounded result `completed`;
- expected local manual run completes;
- expected evidence/provenance persists;
- no unauthorized external action;
- final gate is `blocked`.

Any other bounded result, security/ownership/readiness problem, unexpected mutation or inability to return the gate to blocked is STOP.

A failed attempt consumes this one-shot authorization. Do not retry without a new explicit authorization.
