# Phase 6G First Commercial Call Plan v2 Acceptance

**Status:** ACCEPTED — READY FOR ONE-SHOT AUTHORIZATION
**Date:** 2026-09-29

## Accepted plan

Commit:

`f4158d719d68a0c426da580690b41764db98f563`

The plan correctly implements the approved Option A rollout contract:

- exactly one operator-selected eligible target email;
- exactly one initial `Analyze` click;
- no second target;
- no second click;
- no manual retry;
- existing adapter policy may make up to two provider attempts for the same minimized input through the already-approved transient retry path;
- exact internal provider-attempt count is not an acceptance criterion;
- commercial gate must be disabled and verified blocked after the bounded result settles.

## Preserved controls

The plan preserves:

- Global processing decision;
- protected localhost session/CSRF/Origin/Host boundary;
- exclusive operational ownership and readiness;
- process-local commercial gate;
- OFF-on-restart behavior;
- credential presence-only handling;
- source revalidation;
- existing initial/retry semantics;
- target + at most six prior messages;
- bounded 30,000-character excerpt budget;
- ephemeral aliases;
- no attachments/internal IDs/digests/tools;
- `store=false`;
- local decoder/evidence/provenance validation;
- no automatic external mutation.

## Success boundary

A candidate successful first commercial rollout requires:

- one initial Analyze action;
- bounded result `completed`;
- expected local manual run reaches completed;
- expected evidence/provenance is present;
- no unauthorized external action;
- final commercial gate verified blocked.

`completed_replay` does not validate a first live commercial disclosure.

Any bounded failure or operational/security mismatch is STOP with no manual retry and no second target.

## Authorization boundary

This acceptance does **not** authorize the commercial call.

The next step requires a fresh explicit one-shot user authorization for the controlled rollout described in the accepted v2 plan.

No commercial provider call has been made by this acceptance.
