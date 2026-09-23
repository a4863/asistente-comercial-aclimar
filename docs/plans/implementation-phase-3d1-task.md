# Phase 3D1 Implementation Task — Threading Persistence

**Status:** Approved for Implement
**Date:** 2026-09-23
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3d1-plan.md`

## 1. Objective

Implement exactly the approved Phase 3D1 persistence layer:
- logical data-model correction for singleton current membership;
- Conversation account scope/stable key/legacy status;
- append-only membership history;
- parsed thread evidence;
- evidence decisions;
- grouped merge/split/repartition lineage;
- Alembic revision 0005;
- narrow guarded repository primitives;
- synthetic model/migration/repository tests.

Do NOT implement parser, graph reconstruction, full-corpus thread service, scheduler, UI, IMAP changes, AI, CRM, Calendar, or external actions.

## 2. Scope Lock — authorized files only

Modify only:

- `docs/data-model.md`
- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/versions/0005_phase_3d1_threading_persistence.py`
- `test/test_persistence_models.py`
- `test/test_migrations.py`
- `test/test_persistence_repositories.py`

No other file may change.

## 3. Implementation authority

Follow `docs/plans/implementation-phase-3d1-plan.md` exactly for:
- fields/types/lengths/nullability;
- FK behavior;
- CHECK/UNIQUE/index contracts;
- replay-key domains;
- legacy classification/backfill;
- baseline membership history;
- fail-closed populated downgrade;
- repository validation;
- merge/split/repartition lineage shape;
- append-only semantics;
- caller-owned transaction boundaries.

If implementation requires deviation from the plan, STOP.

## 4. Critical invariants

1. Every new normal 3D conversation is:
   - account-scoped;
   - resolved;
   - assigned one opaque lowercase UUIDv4 stable key;
   - never keyed from Message-ID/subject/members.

2. `ConversationMembership` remains authoritative current projection:
   - one current row per source;
   - new resolved email assignments are guarded;
   - every real change has one matching ThreadMembershipChange in same transaction.

3. Thread history is append-only:
   - no repository update/delete APIs for evidence, decisions, membership changes, lineage operation/edges.

4. Evidence:
   - no full raw References header;
   - no body;
   - no credentials;
   - bounded canonical token only when valid;
   - malformed raw token not stored;
   - SHA-256 fields lowercase hex/64 chars.

5. Decisions:
   - accepted target only for accepted_direct_parent / accepted_ancestor;
   - accepted target must be different email source in same account;
   - ambiguous/rejected outcomes have null target.

6. Lineage:
   - merge >=2 predecessors -> 1 successor;
   - split 1 predecessor -> >=2 successors;
   - repartition >=2 predecessors and >=2 successors;
   - sets disjoint;
   - self-edge prohibited;
   - same account;
   - predecessor not already superseded;
   - graph cycle checked before mutation;
   - predecessor superseded_at updated atomically with operation+edges.

7. Replay:
   - exact replay is no-op;
   - same replay key with different payload raises;
   - rollback removes provisional rows/state.

8. Legacy:
   - derive account only from valid email memberships in one source scope;
   - no configured-mailbox inference;
   - orphan/mixed/non-email/missing EmailMessage/empty scope/already-superseded -> legacy_unresolved;
   - preserve old rows and evidence summaries;
   - append exactly one legacy_assignment_baseline history row per existing membership.

9. Downgrade:
   - only empty dataset may downgrade to 0004;
   - populated conversation/current-membership/history/evidence/lineage must fail closed before dropping anything.

10. Repository methods do not commit.

## 5. Existing repository boundary

Update existing generic conversation repository behavior so it cannot create new unscoped/unhistoried resolved email conversation state.

Preserve unrelated repository behavior.

Do not broaden this task into conversation reconstruction.

## 6. Tests required

At minimum cover all plan tests, including:

### Models/schema
- exact columns/types/nullability;
- named CHECK/UNIQUE/indexes;
- UUID stable-key shape;
- current membership uniqueness;
- evidence token/digest constraints;
- decision outcome/target constraints;
- membership change reason/old-new constraints;
- lineage non-self and uniqueness.

### Repository
- account/email validation;
- cross-account rejection;
- non-email rejection;
- append evidence exact replay;
- replay-key payload disagreement;
- decision exact replay/new reconstruction decision;
- current assignment + history atomicity;
- unchanged assignment no history duplicate;
- stale current assignment rejection;
- rollback behavior;
- merge;
- split;
- repartition;
- cycle rejection;
- already-superseded predecessor rejection;
- immutable/no delete-update surface.

### Migration
- empty 0004 -> 0005;
- valid legacy resolved classification;
- orphan quarantine;
- mixed-account quarantine;
- non-email quarantine;
- missing EmailMessage quarantine;
- empty scope quarantine;
- already-superseded quarantine;
- UUID key assigned to every conversation;
- exactly one baseline history row per old membership;
- legacy evidence strings unchanged;
- FK/constraints/indexes present;
- empty downgrade/re-upgrade;
- populated downgrade refused without partial loss.

### Regression/security
- all prior persistence tests remain green;
- no raw complete References/body/secrets in new persisted history fixtures;
- no real DB/network/mailbox/keyring/AI/CRM/Calendar.

## 7. Validation

Run:

`python -m pytest test/test_persistence_models.py test/test_migrations.py test/test_persistence_repositories.py`

Then:

`python -m pytest`

Both must pass.

## 8. Completion protocol

Verify exact diff against this task baseline.

Commit:

`Implement phase 3D1 threading persistence`

Push only to `origin/codex-work`.

Do not touch `main`.
