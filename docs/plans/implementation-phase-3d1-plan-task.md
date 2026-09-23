# Phase 3D1 Plan Task — Threading Models and Migration

**Status:** Approved for Plan
**Date:** 2026-09-23

## Inputs
- docs/plans/implementation-phase-3d-analysis.md
- docs/plans/implementation-phase-3d-decisions.md
- docs/plans/implementation-phase-3d-data-model-design.md
- docs/plans/implementation-phase-3d-physical-decisions.md
- docs/data-model.md
- app/persistence/models.py
- app/persistence/repositories.py
- alembic revisions/tests

## Objective
Produce an implementation-ready plan for only the 3D1 persistence layer:
1. update logical data-model documentation for singleton current membership;
2. extend Conversation / ConversationMembership as required;
3. add ThreadMembershipChange;
4. add ThreadEvidence;
5. add ThreadEvidenceDecision;
6. add ThreadLineageOperation;
7. add ThreadLineageEdge;
8. create Alembic migration after current head;
9. add model/migration/repository primitives and tests needed for these tables only.

No header parser, graph engine, reconstruction service, scheduler, UI, IMAP/AI/CRM/Calendar work.

## Required exact plan decisions
Specify:
- exact SQLAlchemy fields/types/lengths/nullability/defaults;
- FK targets/actions;
- CHECK constraints;
- UNIQUE constraints;
- indexes;
- Conversation account_scope, stable_key, legacy status;
- membership evidence summary fields retained/changed;
- replay-key format/length domains;
- evidence header_kind/ordinal/token/digest/normalization_version/source_revision fields;
- evidence-decision domains and nullable target semantics;
- membership-change old/new conversation semantics and reasons;
- lineage-operation kind/group/replay identity;
- lineage-edge uniqueness/self-edge rule;
- service/repository checks required for same-account, email-only, acyclic lineage, append-only behavior;
- legacy migration/backfill/quarantine algorithm;
- destructive downgrade guard;
- isolated SQLite migration tests;
- repository methods authorized in 3D1;
- exact file Scope Lock.

## STOP rule
If any exact physical contract remains ambiguous, STOPPED FOR DECISION.
Do not implement.

## Output
Create only:
docs/plans/implementation-phase-3d1-plan.md

Status READY FOR APPROVAL or STOPPED FOR DECISION.

## Completion
Commit:
Plan phase 3D1 threading persistence
Push only origin/codex-work.
