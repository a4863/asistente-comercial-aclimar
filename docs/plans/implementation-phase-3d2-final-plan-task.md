# Phase 3D2 Final Plan Task — Canonical Threading Engine

**Status:** Approved for Plan Revision
**Date:** 2026-09-23

## Inputs
- docs/plans/implementation-phase-3d2-plan.md
- docs/plans/implementation-phase-3d2-decisions.md
- docs/plans/implementation-phase-3d-decisions.md
- docs/plans/implementation-phase-3d-physical-decisions.md
- docs/plans/implementation-phase-3d1-plan.md
- accepted 3D1 implementation

## Objective
Revise Phase 3D2 into an implementation-ready plan with no unresolved parser/graph semantics.

Do not implement code.

## Required exact plan
The plan must define:
- exact pure module paths;
- immutable dataclasses/types and function signatures;
- exact ASCII Message-ID grammar;
- exact 32 KiB/998-char/100-token bounds;
- exact evidence representation for missing, malformed, over-limit and multiple In-Reply-To cases;
- exact References parsing and linking candidate rule;
- duplicate Message-ID index behavior;
- direct-parent/ancestor decision algorithm;
- corpus-wide conflict handling;
- corpus-wide deterministic cycle handling;
- accepted edge construction;
- connected-component algorithm;
- singleton treatment;
- exact subject normalization;
- exact source_revision compatibility contract with 3D1;
- exact reconstruction_key serialization/domain/version;
- output ordering;
- exact mapping to 3D1 evidence/decision outcomes;
- test matrix;
- exact Scope Lock.

## Scope preference
Prefer only:
- app/domain/__init__.py
- app/domain/email_threading.py
- test/test_email_threading.py

If more files are necessary, STOPPED FOR DECISION.

## Out of scope
No persistence/model/migration/repository changes.
No 3C changes.
No external systems.
No scheduler/UI/AI/CRM/Calendar.
No real mailbox/network.

## Output
Modify only:
docs/plans/implementation-phase-3d2-plan.md

Status must be READY FOR APPROVAL or STOPPED FOR DECISION.

## Completion
Commit:
Finalize phase 3D2 canonical threading plan
Push only origin/codex-work.
