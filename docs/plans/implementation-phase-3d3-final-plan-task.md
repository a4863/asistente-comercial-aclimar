# Phase 3D3 Final Plan Task — Full-Corpus Reconstruction Service

**Status:** Approved for Plan Revision
**Date:** 2026-09-23

## Inputs
- docs/plans/implementation-phase-3d3-plan.md
- docs/plans/implementation-phase-3d3-decisions.md
- docs/plans/implementation-phase-3d1-plan.md
- docs/plans/implementation-phase-3d2-plan.md
- accepted 3D1 and 3D2 implementations

## Objective
Revise 3D3 into an exact implementation-ready plan with no unresolved policy choices.

Do not implement code.

## Required final plan decisions

The plan must define exactly:

1. service/module path and public result contract;
2. account-wide write-transaction acquisition strategy for SQLite;
3. 3-attempt busy/retry_later behavior;
4. exact SourceRecord eligibility predicate for locally retained/non-redacted email records;
5. full account corpus read query/shape;
6. legacy_unresolved preflight that fails the entire account pass;
7. source revision creation and 3D2 invocation;
8. evidence_index -> ThreadEvidence.id mapping;
9. decision persistence ordering;
10. old current partition extraction;
11. deterministic overlap-group algorithm comparing old conversations with new components;
12. exact classifications:
   - unchanged
   - initial
   - merge
   - split
   - repartition
   - correction 1→1;
13. fresh conversation creation rules;
14. when an existing conversation is retained exactly;
15. correction lineage model/schema/repository change;
16. reason mapping per source;
17. source-local evidence_decision selection;
18. behavior for missing current membership;
19. behavior for superseded current membership;
20. replay detection before creating opaque conversation identities;
21. crash-before-commit and crash-after-commit idempotency;
22. postconditions;
23. repository extensions;
24. exact migration/model change needed for correction lineage;
25. exact test matrix;
26. exact Scope Lock.

## Correction lineage requirement

Extend 3D1 lineage semantics only as required:
- ThreadLineageOperation.kind includes correction;
- correction shape exactly 1 predecessor -> 1 successor;
- same account, disjoint predecessor/successor IDs, non-self edge, no cycle;
- predecessor superseded atomically;
- append-only lineage remains unchanged otherwise.

If this requires a new Alembic revision, include it explicitly in Scope Lock and plan.

## Transaction rule

Use one account-wide SQLite write transaction:
- acquire write reservation before corpus read;
- all corpus read, 3D2 compute, persistence and projection update belong to the same pass;
- no partial component commits;
- no optimistic stale-revalidation protocol after read;
- busy lock acquisition may retry at most 3 attempts;
- failure after 3 attempts returns busy/retry_later with no changes.

## Replay rule

Exact replay must create no new:
- Conversation;
- ThreadEvidence;
- ThreadEvidenceDecision;
- ThreadMembershipChange;
- ThreadLineageOperation;
- ThreadLineageEdge.

Random conversation stable keys must therefore only be created after deterministic lookup proves the transition has not already been committed.

## Legacy rule

Any eligible source currently assigned to legacy_unresolved => fail the entire pass before topology persistence.
No degraded subset.
No repair.

## Audit rule

Do not add generic AuditEvent writes in 3D3.

## Output

Modify only:
docs/plans/implementation-phase-3d3-plan.md

Status must be READY FOR APPROVAL or STOPPED FOR DECISION.

## Completion

Commit:
Finalize phase 3D3 reconstruction service plan

Push only origin/codex-work.
