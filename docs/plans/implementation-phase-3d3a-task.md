# Phase 3D3A Implementation Task — Correction Lineage Foundation

**Status:** Approved for Implement
**Date:** 2026-09-23
**Parent plan:** docs/plans/implementation-phase-3d3-plan.md

## Objective
Implement only the approved 1→1 correction-lineage extension required by Phase 3D3.

Do NOT implement the reconstruction service, account snapshot repository, transaction orchestration, or concurrency behavior in this task.

## Exact Scope Lock
Modify/create only:
- docs/data-model.md
- app/persistence/models.py
- app/persistence/repositories.py
- alembic/versions/0006_phase_3d3_correction_lineage.py
- test/test_migrations.py
- test/test_persistence_models.py
- test/test_persistence_repositories.py

No other tracked file may change.

## Required changes

### Logical model
Update only the Phase 3D conversation-lineage paragraph to state:
- changed 1 predecessor -> 1 successor member-set transition creates a fresh conversation;
- predecessor is superseded;
- explicit correction lineage is recorded.

### ORM model
Extend ThreadLineageOperation.kind CHECK:
- merge
- split
- repartition
- correction

No other model semantics change.

### Repository
Extend ThreadPersistenceRepository.record_lineage_operation:
- correction requires exactly 1 unique predecessor and exactly 1 unique successor;
- predecessor and successor IDs must be disjoint;
- both resolved and same-account;
- successor active;
- predecessor not already superseded;
- cycle prevention remains;
- replay/payload equality remains;
- predecessor superseded atomically;
- do not weaken existing merge/split/repartition rules.

### Migration 0006
Create:
alembic/versions/0006_phase_3d3_correction_lineage.py

down_revision = 0005.

SQLite migration must rebuild only what is necessary to expand the CHECK while preserving:
- thread_lineage_operation IDs and rows;
- reconstruction/replay keys;
- timestamps/provenance;
- thread_lineage_edge IDs and pairs;
- indexes/unique/check/FK behavior.

Run PRAGMA foreign_key_check in migration.

Downgrade:
- if any kind='correction' row exists: raise RuntimeError before destructive rebuild;
- otherwise restore the 0005 kind CHECK and preserve all merge/split/repartition data/edges.

## Required tests

Migration:
- 0005 -> 0006 -> 0005 -> 0006 on isolated DB;
- populated merge/split/repartition rows preserved;
- edge IDs/pairs preserved;
- foreign_key_check clean;
- downgrade refuses when correction exists.

Model:
- correction accepted physically;
- unsupported lineage kind rejected.

Repository:
- valid correction 1->1 succeeds;
- 1->2, 2->1, 2->2 correction rejected;
- self/overlap rejected;
- cross-account rejected;
- superseded predecessor rejected;
- replay exact returns existing operation;
- replay payload mismatch rejected;
- cycle guard preserved.

## Validation
Run only first:
python -m pytest test/test_migrations.py test/test_persistence_models.py test/test_persistence_repositories.py

Do NOT run the full suite until the focal tests pass.

Then run:
python -m pytest

## Completion
Confirm exact tracked diff contains only the seven authorized paths.

Commit:
Implement phase 3D3A correction lineage

Push only origin/codex-work.

If any additional file is required, STOP.
