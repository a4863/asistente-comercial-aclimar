# Phase 3D3 Implementation Task — Full-Corpus Reconstruction Service

**Status:** Approved for Implement
**Date:** 2026-09-23
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3d3-plan.md`

## Objective

Implement exactly the approved Phase 3D3 account-wide reconstruction service and the controlled 3D1 correction-lineage extension.

## Scope Lock — authorized paths only

- `docs/data-model.md`
- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/versions/0006_phase_3d3_correction_lineage.py`
- `app/services/email_thread_reconstruction.py`
- `test/test_migrations.py`
- `test/test_persistence_models.py`
- `test/test_persistence_repositories.py`
- `test/test_email_thread_reconstruction.py`

No tenth path may change. If another path is required, STOP.

## Required implementation

Follow `docs/plans/implementation-phase-3d3-plan.md` exactly, including:
- account-wide `BEGIN IMMEDIATE` before corpus read;
- max 3 lock-acquisition attempts;
- locally retained/non-redacted corpus regardless of IMAP location availability;
- fail whole pass on eligible source in `legacy_unresolved`;
- full 3D2 invocation exactly once per pass;
- evidence/decision persistence before topology projection;
- deterministic overlap grouping;
- unchanged/initial/merge/split/repartition/correction classification;
- fresh identities for all changed groups;
- exact source-local decision attribution;
- one account commit only;
- rollback on any failure;
- exact replay with zero new conversation/history/lineage rows;
- no generic AuditEvent.

## Correction lineage extension

Add only:
- `ThreadLineageOperation.kind='correction'`;
- shape exactly 1 predecessor -> 1 successor;
- same account;
- predecessor/successor disjoint;
- non-self;
- no cycle;
- predecessor superseded atomically;
- append-only lineage behavior unchanged.

Create revision:
`0006_phase_3d3_correction_lineage.py`

Preserve existing 0005 data and edges. Downgrade must fail closed if any correction operation exists.

## Critical service invariants

1. One logical email node per SourceRecord+EmailMessage.
2. IMAP location state never controls corpus inclusion.
3. Eligible source predicate exactly as approved.
4. Every eligible source ends with exactly one current active resolved same-account conversation.
5. Existing conversation retained only when its full current member set exactly equals one computed 3D2 component.
6. Any changed partition gets fresh identity/identities and explicit lineage.
7. No old arbitrary winner.
8. No topology from subject/current IDs/CRM/folders/dates.
9. Excluded sources are not reassigned.
10. Quarantine is never repaired silently.
11. No repository commit.
12. No raw full headers/body/secrets in history/errors.
13. Exact replay does not duplicate any of the six threading persistence entities.

## Transaction behavior

Use one fresh SQLite connection per attempt:
- verify FK;
- busy_timeout=0;
- explicit `BEGIN IMMEDIATE`;
- bind one Session to same connection;
- read + compute + persist + postcondition validation;
- one commit.

Only lock-acquisition busy/locked is retried.
Exactly 3 attempts total with 100 ms delay between attempts.
After third failure return `busy_retry_later` with zero changes.

## Result contract

Implement the exact frozen+slots result/error contract from the plan.

Errors must expose bounded codes only, never raw email content.

## Tests required

Implement the complete plan test matrix, including at minimum:

### Migration/model
- correction kind accepted;
- other lineage shapes unchanged;
- 0005→0006 populated preservation;
- edge IDs/pairs preserved;
- FK check clean;
- 0006→0005 works with no correction rows;
- downgrade refuses with correction rows;
- failure leaves schema/data intact.

### Repository
- snapshot includes unavailable-location emails;
- excludes valid redacted/deleted local sources;
- invalid retention/timestamp state rejected;
- full old member sets loaded;
- legacy_unresolved detectable;
- superseded current membership detectable;
- correction shape/replay/cycle/account guards.

### Service
- empty corpus;
- initial singleton;
- initial multi-email component;
- unchanged exact set;
- merge;
- split;
- repartition;
- correction 1→1;
- newly unassigned source entering changed group;
- excluded old member forces non-unchanged;
- source-local evidence pointer;
- root null evidence pointer;
- legacy quarantine rolls back before topology mutation;
- superseded/mixed/non-email state fails;
- evidence-index mapping;
- exact replay zero topology/history inserts;
- new reconstruction key but unchanged partition;
- rollback injected after evidence/decision/conversation/lineage/membership stages;
- crash/retry semantics;
- busy exactly three attempts then busy_retry_later;
- concurrent writer coverage;
- no generic AuditEvent;
- no network/IMAP/keyring/CRM/Calendar/AI.

## Validation

Run:

`python -m pytest test/test_migrations.py test/test_persistence_models.py test/test_persistence_repositories.py test/test_email_thread_reconstruction.py`

Then:

`python -m pytest`

Both must pass.

Inspect exact diff and confirm only the nine authorized paths changed.

## Completion

Commit:
`Implement phase 3D3 full-corpus reconstruction`

Push only to `origin/codex-work`.

Do not touch `main`.
