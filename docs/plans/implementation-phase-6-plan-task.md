# Phase 6 Planning Task — Safe AI Activation

**Status:** APPROVED FOR PLANNING ONLY
**Date:** 2026-09-24
**Analysis:** docs/plans/phase-6-activation-analysis.md
**Decisions:** docs/plans/phase-6-activation-decisions.md

## Objective

Produce a concrete implementation plan for Phase 6 using the approved decisions.

This task is planning/documentation only. Do not implement production code, tests, CLI tooling, migrations, provider calls or credential operations.

## Required plan

Create:

`docs/plans/implementation-phase-6-plan.md`

The plan must:

1. map the approved decisions to concrete future files;
2. split Phase 6 into small independently reviewable subphases;
3. define exact Scope Lock proposals for each subphase;
4. identify dependencies/order between subphases;
5. keep commercial-data activation separate from synthetic live smoke;
6. keep all default tests offline;
7. preserve zero provider calls on import/startup/status;
8. define how runtime gate state is represented without silently using `AISettings.enabled` as consent;
9. define credential CLI set/status/delete behavior without echo/argv secret exposure;
10. define synthetic smoke CLI structure and how it is prevented from reading IMAP/CRM/Calendar/production SQLite;
11. define kill-switch semantics and `reserved` run recovery;
12. define status-page fields and safe credential-presence lookup behavior;
13. identify whether any data-model or migration work is actually required; avoid it unless necessary;
14. include the controlled correction to the stale AI-provider statement in `docs/architecture.md` only if explicitly scoped;
15. include focal and full-suite validation commands for each implementation subphase.

## Preferred subphase sequence

Use this as a default unless repository inspection proves a better split:

- 6A — runtime activation gate + composition foundation;
- 6B — local status + credential presence;
- 6C — interactive credential CLI;
- 6D — synthetic live-smoke CLI tooling with fake-client tests only;
- 6E — rollback/recovery + security regression;
- 6F — optional one-shot live synthetic smoke, separately approved;
- 6G — optional commercial-data activation, separately approved.

The plan should minimize production file count per subphase, ideally 2–4 tracked files where practical.

## Hard restrictions

Planning only.

Do not:
- modify production code;
- modify tests;
- modify config;
- modify `docs/architecture.md` yet;
- create scripts;
- add dependencies;
- create migrations;
- call OpenAI;
- inspect real credentials;
- read IMAP/CRM/Calendar;
- activate commercial processing.

## STOP conditions

STOP if:
- two or more reasonable implementation architectures still remain after applying the approved decisions;
- runtime gate requires a new persistent authorization model/migration not already approved;
- a scheduler/background trigger appears necessary;
- safe credential provisioning requires a new secret store;
- a live provider call appears necessary to complete planning.

If blocked, document the alternatives and request a decision rather than inventing one.

## Completion

Create only:

`docs/plans/implementation-phase-6-plan.md`

Commit:

`Plan phase 6 safe AI activation`

Push only to `origin/codex-work`.
