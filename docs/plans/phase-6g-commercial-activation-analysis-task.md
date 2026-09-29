# Phase 6G Commercial Activation Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-29
**Mode:** READ-ONLY / NO COMMERCIAL PROVIDER CALL

## Context

Phase 6F is ACCEPTED/CLOSED for fixed synthetic live provider plumbing.

Phase 6G is the separately gated commercial-data activation phase.

The existing Phase 6 plan requires a new explicit processing-mode decision for the actual OpenAI account/project:

A. verified EU-eligible processing/residency for the configured project/endpoint; or
B. separate explicit user acceptance of Global processing for commercial data.

The user's instruction to proceed with Phase 6G authorizes this analysis only. It does NOT select Global processing and does NOT enable the commercial gate.

## Objective

Produce the exact implementation/operational decision boundary for safely enabling real commercial email analysis through the existing manual protected route.

Determine:

1. what repository/runtime state is already ready for 6G;
2. what external evidence is required before selecting EU processing;
3. what explicit user decision would be required if Global processing is chosen instead;
4. the smallest safe activation UX/API/runtime change, if any;
5. the exact rollback/revocation procedure;
6. the first-commercial-call acceptance protocol.

Do not implement code.

## Required repository inspection

Inspect at minimum:

- docs/plans/implementation-phase-6-plan.md
- all accepted 6B1, 6B2, 6E1, 6E2, 6E3, 6F decisions/acceptances
- app/security/activation.py
- app/integrations/openai_analysis.py
- app/main.py
- app/web/routes.py
- app/web/templates/status.html
- app/config.py
- credential/status handling
- email analysis service/repository path
- security/session/CSRF/origin protections
- startup ownership/recovery behavior
- relevant tests

## Processing-mode decision boundary

Document two mutually exclusive activation paths.

### Path A — EU verified

Commercial activation may be planned only if operator evidence establishes that the actual OpenAI API organization/project is configured/eligible for the required European data-processing/residency mode.

The analysis must define exactly what evidence is acceptable, for example:
- project/account control-plane setting or OpenAI-provided confirmation;
- exact project used by the API key;
- exact endpoint/base URL required by that configuration;
- any retention setting relevant to the approved requirement.

Do NOT infer EU residency from:
- `https://eu.api.openai.com/v1` alone;
- geographic user location;
- a successful smoke;
- model name;
- API key presence.

If acceptable evidence cannot be produced, EU path remains blocked.

### Path B — Global explicit acceptance

If the operator chooses Global processing instead, require a fresh explicit user statement accepting Global processing for real commercial data.

Do not infer this decision from:
- "proceed";
- approval of Phase 6G analysis;
- prior synthetic smoke approvals.

Until that exact decision exists, Global commercial activation remains blocked.

## Existing commercial gate review

Determine whether the current `CommercialActivationGate` and protected manual route already satisfy the Phase 6G activation lifecycle:

- OFF on every process start;
- explicit enable only;
- revocable in-process;
- adapter checks gate before credential/provider and every retry;
- already-sent call may finish;
- disable prevents new calls/retries;
- no persistence of authorization;
- no background/scheduler trigger;
- localhost session/CSRF/origin protection;
- operational ownership required.

Identify whether code changes are actually needed.

Prefer **no code change** if the existing gate plus an operator-controlled activation procedure can safely satisfy 6G.

If code/UI changes are needed, explain exactly why.

## Activation UX / operator action

Analyze the safest practical way for the single local operator to enable/revoke commercial activation.

Evaluate, without implementing:

- existing process-local API only;
- local CLI command;
- protected localhost UI control;
- startup flag/environment variable;
- any already-supported minimal mechanism.

Requirements:

- no authorization persistence;
- explicit user action;
- visible current gate state;
- revocation available;
- cannot be triggered by email/AI/provider content;
- cannot bypass session/CSRF/origin/ownership;
- bounded feedback;
- no credential exposure.

If more than one reasonable mechanism remains after inspection, STOP with a decision table rather than choosing silently.

## First commercial call protocol

Design the smallest safe controlled first use after processing-mode approval.

It must:

- use exactly one operator-selected existing eligible email from the bounded selector;
- use the existing protected manual POST;
- preserve minimized projection;
- preserve all source revalidation/provenance/persistence contracts;
- preserve existing non-force initial/retry semantics;
- no scheduler/background analysis;
- no automatic email mutation/action;
- record only normal local analysis/audit state already authorized;
- define what output/result is sufficient for acceptance;
- define STOP conditions;
- define how to revoke gate immediately after the controlled first call if that is the safer rollout.

Do not select an actual commercial email in this analysis.

## Operational prerequisites

Verify/document before first commercial activation:

- branch/build accepted and clean;
- one operational process only;
- exclusive lock ownership;
- recovery/cutover state healthy;
- credential presence only;
- operational config exact endpoint/model;
- status surface expected state;
- commercial gate OFF before explicit activation;
- no reload/multi-worker;
- rollback path.

## Data minimization and privacy review

Confirm what commercial fields can be disclosed to the provider under the existing projection.

Document what remains excluded.

Do not expand data categories.

Confirm:
- no attachments;
- no full mailbox dump;
- bounded target + prior messages only;
- ephemeral aliases instead of internal IDs;
- no source digests/run IDs/stable conversation keys;
- no tools/functions;
- store=false;
- decoder/evidence validation remains local.

## Required output

Create only:

`docs/plans/phase-6g-commercial-activation-analysis.md`

Include:

1. current readiness map;
2. unresolved external processing-mode gate;
3. exact acceptable evidence for Path A (EU);
4. exact explicit-decision condition for Path B (Global);
5. current gate lifecycle assessment;
6. activation/revocation mechanism decision table;
7. whether code changes are required;
8. exact first-commercial-call protocol;
9. rollback/STOP conditions;
10. candidate Scope Lock if implementation is needed;
11. verdict: READY FOR DECISION, READY FOR PLAN, or STOP.

No code changes.
No live provider call.
No commercial data transmission.

Commit:

Analyze phase 6G commercial activation

Push only origin/codex-work.
