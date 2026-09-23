# Phase 4A2 Implementation Task — Alembic 0007 Analysis Foundation

**Status:** Approved for Implement
**Date:** 2026-09-23
**Prerequisite:** Phase 4A1 ACCEPTED
**Approved plan:** docs/plans/implementation-phase-4-plan.md

## Objective

Implement only Alembic revision 0007 for the Phase 4 analysis foundation already defined in ORM models during 4A1.

Do NOT modify ORM models, repositories, services, domain logic, AIService, CRM, scheduler, UI, or external integrations.

## Exact Scope Lock

Modify only:

1. alembic/versions/0007_phase_4_analysis_foundation.py
2. test/test_migrations.py

No other tracked path may change.

## Migration revision

Create:

alembic/versions/0007_phase_4_analysis_foundation.py

with:

down_revision = "0006"

Use the exact table/column/check/index/FK semantics already present in:
- app/persistence/models.py
- docs/data-model.md
- docs/plans/implementation-phase-4-plan.md

Do not change 4A1 model definitions to fit the migration. If parity cannot be achieved within these two files, STOP.

## Upgrade requirements

Create the Phase 4 tables in safe FK order:

- analysis_run
- analysis_source_evidence
- analysis_derivation_link
- analysis_summary
- analysis_operational_link

Add Phase 4 commitment columns:
- responsible_party
- date_certainty
- date_expression

Because SQLite is used, rebuild commitment if required to add the approved CHECK constraints safely.

Preserve:
- existing commitment IDs;
- existing timestamps;
- existing state/due_at/resolution/provenance data;
- all existing indexes and FKs;
- all legacy rows with new fields NULL.

Do not fabricate responsible/date-certainty values for legacy rows.

Run PRAGMA foreign_key_check in migration tests.

## Required parity

The migrated schema must match 4A1 SQLAlchemy metadata for:

### analysis_run
- fields and nullability
- FK RESTRICT semantics
- request_mode/status/failure_code checks
- lifecycle check
- non-self supersession check
- unique account+target+run_version
- unique supersedes_run_id
- both approved indexes

### analysis_source_evidence
- offset/digest/quote_state checks
- unique span identity
- source/body index
- FK RESTRICT semantics

### analysis_derivation_link
- exactly-one derivation FK
- evidence FK
- partial unique indexes
- run index

### analysis_summary
- one summary per run
- 1..4000 length
- digest check

### analysis_operational_link
- type/FK matching CHECK
- unique per operational object
- run/type index

### commitment extension
- nullable legacy compatibility
- responsibility enum
- date certainty enum
- date expression <=255
- phase4 paired-field rule
- exact/resolved_relative due_at rules
- uncertain/none due_at NULL rule
- due/state index retained

## Downgrade requirements

Downgrade 0007 -> 0006 must refuse if ANY Phase 4 data would be lost:

Refuse when:
- any row exists in any Phase 4 table; OR
- any commitment has non-null responsible_party/date_certainty/date_expression.

The refusal must:
- raise a bounded, explicit migration exception;
- leave schema/data intact;
- not partially drop tables or rebuild commitment.

If safe to downgrade:
- drop Phase 4 tables in FK-safe order;
- restore commitment exactly to pre-4A1/0006 physical layout;
- preserve all legacy commitment data;
- preserve previous indexes/constraints.

## Required tests

Extend test/test_migrations.py with focused isolated-SQLite coverage:

1. upgrade empty DB 0006 -> 0007;
2. schema contains all five Phase 4 tables;
3. migrated constraints/indexes/FKs reflect ORM model;
4. populated legacy commitment survives upgrade with NULL Phase 4 fields;
5. legacy IDs/timestamps/state/due_at/resolution/provenance preserved;
6. valid Phase 4 commitment accepted after upgrade;
7. invalid responsibility rejected;
8. invalid date certainty rejected;
9. invalid exact/no due date rejected;
10. invalid resolved_relative/no expression rejected;
11. invalid uncertain/none with due_at rejected;
12. analysis_run lifecycle constraints work;
13. evidence/derivation/summary/operational constraints work;
14. FK RESTRICT behavior works with foreign_keys ON;
15. PRAGMA foreign_key_check is clean;
16. downgrade empty/new-tables-empty DB succeeds;
17. downgrade restores 0006 commitment layout;
18. 0006 -> 0007 -> 0006 -> 0007 roundtrip succeeds;
19. downgrade refuses when analysis_run contains data;
20. downgrade refuses when another Phase 4 child table contains data;
21. downgrade refuses when commitment has new Phase 4 fields;
22. refusal leaves all schema/data intact;
23. migration failure/rollback does not leave partial schema.

Use isolated temporary SQLite DBs only.

## Restrictions

- do not modify app/persistence/models.py;
- do not modify docs/data-model.md;
- do not modify repositories/services/domain/tests outside test_migrations;
- no production DB;
- no new dependencies;
- no real integrations;
- no cache/untracked inspection.

## Validation

Run:

python -m pytest test/test_migrations.py test/test_persistence_models.py

Then:

python -m pytest

Tracked diff must contain exactly:
- alembic/versions/0007_phase_4_analysis_foundation.py
- test/test_migrations.py

## Completion

Commit:

Implement phase 4A2 analysis foundation migration

Push only origin/codex-work.

If any model change is required, STOP.
