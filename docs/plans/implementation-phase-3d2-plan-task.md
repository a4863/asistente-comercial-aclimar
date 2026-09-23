# Phase 3D2 Analysis/Plan Task — Canonical Header Parser and Pure Thread Graph Engine

**Status:** Approved for Analyze/Plan
**Date:** 2026-09-23
**Baseline:** current `codex-work`

## 1. Objective

Define an implementation-ready plan for Phase 3D2 only:

1. a pure canonical parser/normalizer for:
   - Message-ID;
   - In-Reply-To;
   - References;
   - secondary subject normalization;
2. a pure deterministic threading decision engine over an in-memory corpus snapshot.

3D2 must not persist conversations, mutate memberships, create lineage operations, touch IMAP, query network services, or invoke AI.

## 2. Inputs

Review at minimum:
- `docs/plans/implementation-phase-3d-analysis.md`
- `docs/plans/implementation-phase-3d-decisions.md`
- `docs/plans/implementation-phase-3d-physical-decisions.md`
- `docs/plans/implementation-phase-3d1-plan.md`
- accepted 3D1 models/repositories/migration/tests
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/testing-strategy.md`

## 3. Fixed decisions

### D1 normalization
- 3D-local normalization only.
- trim outer whitespace and angle brackets for comparison.
- comparison case-insensitive.
- malformed identifiers never create edges.
- multiple identifiers in In-Reply-To are ambiguous.
- References preserves order.
- explicit token and chain limits required.

### D2 conservative conflicts
- unique valid In-Reply-To is strongest direct-parent evidence.
- References may corroborate / provide ancestor support.
- incompatible local components -> no automatic merge.
- duplicate Message-ID target -> ambiguous.
- self-links and cycles invalid.
- no transitive merge through ambiguous evidence.

### D3 singleton / subject
- subject never creates a merge.
- subject normalization is diagnostic/secondary only.
- independent same-subject messages remain separate.
- late parent arrival may change graph result on full recomputation.

### D6 full-corpus baseline
- full account-scoped deterministic computation.
- no persistence in this phase.

## 4. Required exact decisions

The plan must close:

1. exact Message-ID token grammar accepted by the application;
2. exact handling of comments, folding whitespace, brackets and stray text;
3. whether local-part/domain are both case-folded or entire token lowercased per approved D1;
4. max token length;
5. max References token count;
6. behavior when limits are exceeded;
7. exact parsing of malformed mixed-valid References;
8. exact behavior for In-Reply-To containing 0, 1, or >1 valid IDs;
9. representation of parse evidence for missing/malformed/multiple values;
10. subject normalization:
    - Re:
    - Fw:
    - Fwd:
    - localized/common variants if any;
    - whitespace collapsing;
    - repeated prefixes;
    - whether bracketed tags are untouched;
11. pure input dataclasses/types;
12. pure output dataclasses/types;
13. evidence outcome mapping to 3D1 domains;
14. local Message-ID index semantics preserving duplicates;
15. parent-edge evaluation order;
16. References ancestor evaluation order;
17. conflict detection;
18. orphan handling;
19. missing external ancestor representation;
20. self-link detection;
21. cycle detection;
22. connected-component computation using accepted edges only;
23. singleton components;
24. component determinism/order;
25. full reconstruction key input contract;
26. source revision input contract compatibility with 3D1;
27. changed subject with intact technical links;
28. forwarded-message behavior;
29. two components bridged by conflicting evidence;
30. late-root recomputation expectations;
31. exact test matrix;
32. exact Scope Lock.

## 5. Critical semantic rule

The engine must distinguish:
- parsed evidence;
- evidence decision;
- accepted graph edge;
- conversation component.

A parsed token is not automatically an accepted edge.

A message with ambiguous/conflicting technical evidence must never bridge two components.

Subject similarity alone must never affect connectivity.

## 6. Suggested implementation boundary

Prefer pure modules with no SQLAlchemy/import of repositories.

Possible shape:
- `app/domain/email_threading.py` or equivalent;
- parser functions;
- immutable dataclasses;
- graph computation function.

The plan must decide exact path/API rather than assume this suggestion.

## 7. Out of scope

- persistence writes;
- ThreadPersistenceRepository mutations;
- migration/model changes;
- IMAP adapter/sync changes;
- scheduler;
- UI;
- CRM;
- Calendar;
- AI;
- reply drafting;
- filing/move actions;
- real mailbox/network.

## 8. STOP rule

If two materially different parser/graph semantics remain reasonable, return STOPPED FOR DECISION.

Do not implement until the plan is approved.

## 9. Output

Create only:

`docs/plans/implementation-phase-3d2-plan.md`

Status:
- READY FOR APPROVAL
- or STOPPED FOR DECISION

Must include:
- exact parser grammar;
- normalization limits;
- immutable input/output contracts;
- decision algorithm;
- conflict/cycle handling;
- component-building algorithm;
- deterministic/replay contract;
- test matrix;
- exact Scope Lock;
- open decisions.

## 10. Completion protocol

Commit:

`Plan phase 3D2 canonical threading engine`

Push only to `origin/codex-work`.

Do not touch `main`.
