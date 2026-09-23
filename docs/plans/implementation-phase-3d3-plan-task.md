# Phase 3D3 Analysis/Plan Task — Full-Corpus Thread Reconstruction Service

**Status:** Approved for Analyze/Plan
**Date:** 2026-09-23
**Baseline:** current `codex-work`

## 1. Objective

Design an implementation-ready application service that connects:
- accepted 3D2 pure threading output;
- accepted 3D1 persistence primitives;

to perform a deterministic full-account reconstruction pass.

The service must:
1. read a consistent local account-scoped corpus snapshot;
2. validate/recompute source revisions;
3. invoke the pure 3D2 engine;
4. persist evidence and decisions;
5. create singleton/current conversations where needed;
6. reconcile current ConversationMembership projection with computed components;
7. create fresh Conversation rows for merges/splits/repartitions per D5;
8. record append-only membership history and lineage;
9. remain replay-safe;
10. fail atomically per approved transaction boundary.

No scheduler, UI, IMAP fetch, CRM, Calendar, AI, or external actions.

## 2. Inputs to review

At minimum:
- docs/plans/implementation-phase-3d-analysis.md
- docs/plans/implementation-phase-3d-decisions.md
- docs/plans/implementation-phase-3d-physical-decisions.md
- docs/plans/implementation-phase-3d1-plan.md
- docs/plans/implementation-phase-3d2-plan.md
- accepted 3D1 models/repositories/migration/tests
- accepted 3D2 domain engine/tests
- docs/data-model.md
- docs/architecture.md
- docs/testing-strategy.md
- app/persistence/models.py
- app/persistence/repositories.py

## 3. Fixed decisions

- full account-scoped corpus baseline;
- no incremental optimization yet;
- one current conversation per logical email after reconstruction;
- every unlinked source gets a singleton;
- current membership projection + append-only history;
- new conversation identity on merge/split/repartition;
- no old conversation survives arbitrarily as winner;
- explicit lineage;
- exact replay must not duplicate evidence, decisions, conversations, history, or lineage;
- no inferred cross-account or non-email membership;
- legacy_unresolved remains excluded until separately repaired;
- no external system access.

## 4. Required design decisions

The plan must close exactly:

1. exact service/module path;
2. repository reads required to build the corpus;
3. exact account-scoped source selection;
4. treatment of unavailable/deleted-at-source emails;
5. whether all locally retained EmailMessage records participate or only active source records;
6. exact consistent-snapshot strategy under SQLite/SQLAlchemy;
7. preflight validation before calling 3D2;
8. persistence ordering:
   - evidence;
   - decisions;
   - conversation mapping;
   - memberships;
   - lineage;
9. mapping of 3D2 evidence_index to persisted ThreadEvidence IDs;
10. mapping of 3D2 components to existing current conversations;
11. exact classification:
   - unchanged component;
   - new singleton;
   - merge;
   - split;
   - repartition;
   - correction/reassignment;
12. when an existing Conversation may be retained unchanged;
13. when fresh Conversation rows are mandatory;
14. how to compare prior membership partition vs new component partition deterministically;
15. how to generate operation/replay identities;
16. exact reason mapping for ThreadMembershipChange;
17. how accepted edge decisions associate to membership changes when a component has multiple sources;
18. behavior when a source currently belongs to legacy_unresolved conversation;
19. behavior when current membership is missing unexpectedly;
20. behavior when current membership points to superseded conversation;
21. stale-snapshot detection before commit;
22. retry semantics;
23. transaction granularity:
   - one account-wide transaction;
   - or component-level transactions;
24. exact idempotency guarantees after crash/rollback;
25. exact audit events required now, if any;
26. whether generic AuditEvent integration belongs in 3D3 or later;
27. postconditions/invariants;
28. exact repository extensions required;
29. exact test matrix;
30. exact Scope Lock.

## 5. Critical semantic rule

The service must not invent topology.

3D2 result is the only authority for graph/component membership in this phase.

Persistence may:
- preserve an existing Conversation only when its current member set exactly equals one computed component and it is active/resolved/same-account;
- otherwise use explicit new identity + lineage according to approved D5.

The service must never merge based on subject, timestamps, current conversation identity, CRM context, participants, or mailbox folder.

## 6. Legacy and exclusion rules

The plan must explicitly decide whether legacy_unresolved memberships:
- block reconstruction for those sources;
- are skipped with a degraded result;
- or require STOP/error.

Do not silently move a source out of quarantine without an approved repair policy.

## 7. Snapshot and concurrency

The design must account for:
- stored email headers changing between read and persistence;
- Phase 3C sync writing concurrently;
- source becoming unavailable during a pass;
- replay after partial failure.

No external lock may be assumed unless explicitly designed and justified.

## 8. Out of scope

- IMAP network fetch/reconciliation changes;
- scheduler/APScheduler;
- UI/endpoints;
- CRM/Calendar/AI;
- draft/move/send actions;
- legacy quarantine repair;
- incremental threading optimization;
- real mailbox/database mutation during planning.

## 9. STOP rule

If there are materially different reasonable choices for:
- active/unavailable source participation;
- quarantine behavior;
- transaction granularity;
- component-to-existing-conversation reuse;
- audit boundary;
- stale snapshot/retry semantics;

return STOPPED FOR DECISION with alternatives.

Do not implement.

## 10. Output

Create only:

`docs/plans/implementation-phase-3d3-plan.md`

Status:
- READY FOR APPROVAL
- or STOPPED FOR DECISION

Must include:
- exact service algorithm;
- exact state-transition matrix;
- replay/idempotency contract;
- transaction model;
- stale-snapshot behavior;
- repository extensions;
- test matrix;
- exact Scope Lock;
- open decisions.

## 11. Completion protocol

Commit:

`Plan phase 3D3 full-corpus reconstruction service`

Push only to `origin/codex-work`.

Do not touch `main`.
