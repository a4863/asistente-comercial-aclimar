# Phase 4 Decisions — Email/Thread Analysis and AIService Boundary

**Status:** APPROVED
**Date:** 2026-09-23
**Analysis:** docs/plans/implementation-phase-4-analysis.md

This document records the user-approved decisions that unblock Phase 4 planning.

## D1 — Analysis unit and trigger
**Approved: D1-B**

Analyze the new or changed message together with a bounded prior-context subset from the same reconstructed thread.

Triggers:
- after synchronization + Phase 3D3 reconstruction when relevant message content is new or changed;
- explicit manual reanalysis request;
- thread merge/split/repartition may trigger reanalysis of affected conversations.

Do not indiscriminately analyze the full historical conversation.

## D2 — Replay identity and changed content
**Approved: D2-B**

Analysis identity is based on a digest of:
- the exact analysis input selected for disclosure;
- the analysis contract/policy version.

The Phase 3D3 reconstruction key is not sufficient because body changes may not change thread topology.

Exact successful replay of the same input must not call AI again unnecessarily.

Explicit manual reanalysis may create a new version while retaining previous history.

Different model output must never silently overwrite prior analysis.

## D3 — Exact-question evidence
**Approved: D3-A**

Store exact question wording in Question.question_text and link it to source-local evidence:
- source_record_id;
- bounded message-local span/reference.

Quoted historic questions must not be treated as newly asked questions merely because they appear in quoted content.

Question transition to answered requires later source evidence or explicit user confirmation. AI output alone cannot close a question.

## D4 — Commitment ownership and dates
**Approved: D4-A**

Represent commitment responsibility explicitly with bounded values:
- self;
- counterparty;
- unknown.

Represent date certainty explicitly with bounded values:
- exact;
- resolved_relative;
- uncertain;
- none.

AI-detected promises remain detected unless there is explicit, unambiguous source evidence.

An explicit source promise may justify confirmed state without separate user confirmation.

Relative dates are resolved against the source-message date while preserving that the original expression was relative.

## D5 — Candidate-to-record semantics
**Approved: D5-A**

Persist typed derivations first:
- ExtractedFact;
- Inference;
- Proposal.

Operational objects are created from validated derivations/evidence.

Initial operational states:
- Question -> detected;
- Commitment -> detected or confirmed according to D4;
- Task -> proposed;
- NextStep -> proposed.

AI may create internal candidates/operational records under application rules but has no authority to approve or execute external actions.

response_needed, commercial_risk, and priority are inferences with bounded values, not facts.

Alerts are derived later through application rules, not directly because AI asserted them.

## D6 — Reanalysis and correction
**Approved: D6-A**

Use append-only versioned analysis runs.

New analysis may supersede prior derivations but does not delete history.

A stale Question, Task, Commitment, or NextStep must not silently disappear or transition to answered/completed/cancelled solely because a newer run omits it.

Lifecycle changes still require valid later evidence or user confirmation.

## D7 — Remote disclosure selection
**Approved: bounded D7-B**

For MVP, disclose a bounded current-thread subset without sophisticated automatic quote/signature removal.

Default configurable limits:
- current/new-or-changed message;
- up to 6 previous messages from the same reconstructed thread;
- maximum 30,000 characters total.

When truncated:
- preserve the current message first;
- then the most recent prior context.

Metadata may include sender, relevant recipients, subject, and date only when useful.

Never disclose:
- whole mailbox;
- whole database;
- unrelated CRM history;
- credentials/tokens/secrets;
- logs/audit payloads;
- attachment bytes.

A future quote/signature minimizer requires separate scope because unsafe trimming could destroy evidence.

## D8 — CRM boundary
**Approved: D8-A**

Phase 4 performs no live CRM API lookup.

Phase 4 may:
- reuse an already confirmed IdentityLink;
- reuse already confirmed local CRM context when available;
- surface text-only candidate mentions.

Phase 4 must not:
- confirm entities by text similarity;
- infer work/opportunity/offer solely from a confirmed contact identity;
- write to CRM.

Live read-only CRM lookup belongs to a later separately approved phase.

## D9 — Failure and transaction model
**Approved: D9-B**

Introduce a persisted AnalysisRun-style status record with retryable state.

AI/provider call occurs outside the long-lived local write transaction.

Before persisting results:
- revalidate that the analysis input/snapshot identity is unchanged.

If source/thread input changed while AI was running:
- do not persist stale derivations;
- mark the run stale/retryable;
- reanalyze against the new input.

Provider failure:
- persist only bounded failure/status metadata;
- no partial facts/inferences/proposals/tasks.

Persistence failure:
- rollback all derived records atomically.

No raw provider/SQLite error text should be surfaced as domain state.

## Consolidated approval

Approved block:

D1-B, D2-B, D3-A, D4-A, D5-A, D6-A,
D7-B bounded (current + up to 6 previous / 30,000 chars),
D8-A, D9-B.

These decisions authorize planning only, not implementation.
