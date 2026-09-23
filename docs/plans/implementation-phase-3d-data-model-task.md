# Phase 3D Data Model Design Task — Thread Evidence and History

**Status:** Approved for Analyze/Design
**Date:** 2026-09-23
**Baseline:** current `codex-work`
**Inputs:**
- `docs/plans/implementation-phase-3d-analysis.md`
- `docs/plans/implementation-phase-3d-decisions.md`

## 1. Objective

Design the minimum physical data-model extension required to implement the approved Phase 3D threading contract.

Do not implement schema, migration, repository, or service code.

## 2. Required design outcomes

Define exactly:

1. Conversation account scope.
2. Stable local conversation identity/key.
3. Conversation supersession/successor representation supporting:
   - merge A+B -> C;
   - split A -> B+C;
   - multiple predecessors/successors;
   - acyclic lineage constraints where enforceable.
4. Current ConversationMembership representation.
5. Append-only membership assignment history.
6. Append-only parsed header evidence / edge decision representation.
7. Representation of:
   - accepted direct-parent edge;
   - accepted ancestor/support edge;
   - ambiguous target;
   - malformed token;
   - self-link;
   - cycle rejection;
   - conflict between In-Reply-To and References;
   - missing external ancestor.
8. Bounded evidence reference strategy without raw unbounded header duplication.
9. Normalization versioning.
10. Deterministic/replay-safe identifiers or uniqueness constraints.
11. Current versus historical state query model.
12. Whether existing Conversation.superseded_at remains sufficient or needs replacement/extension.
13. Whether existing ConversationMembership can be preserved or must be modified.
14. Exact foreign keys, unique constraints, indexes, nullable/non-nullable fields and enum/check domains.
15. Migration behavior for existing databases:
   - existing Conversation rows;
   - existing memberships;
   - no conversation data case.
16. Repository operations required later.
17. Transaction unit for one reconstructed component change.
18. Audit interaction versus dedicated history tables.
19. Retention behavior.
20. Fake-only migration/model test matrix.

## 3. Guardrails

- Preserve approved one-current-conversation-per-source behavior.
- Preserve ambiguity: never require forced membership because of a conflicting edge.
- Do not store raw email body or raw full References header in new history/audit rows.
- Do not change Phase 3C tables unless strictly necessary and justified.
- No network, IMAP, keyring, AI, CRM, Calendar, UI, scheduler.
- No implementation.

## 4. Schema-gap / STOP rule

If two materially different minimal schemas are both reasonable, STOPPED FOR DECISION and present alternatives.

Do not silently choose a design whose merge/split lineage or evidence semantics are ambiguous.

## 5. Output

Create only:

`docs/plans/implementation-phase-3d-data-model-design.md`

Status:
- READY FOR APPROVAL
- or STOPPED FOR DECISION

The document must include:
- proposed entities/tables;
- exact fields;
- relationships;
- constraints;
- indexes;
- lifecycle/state semantics;
- migration strategy;
- repository implications;
- test matrix;
- Scope Lock for later migration/model implementation;
- open decisions.

## 6. Completion protocol

Commit:

`Design phase 3D thread evidence data model`

Push only to `origin/codex-work`.

Do not touch `main`.
