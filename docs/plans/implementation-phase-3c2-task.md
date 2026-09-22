# Phase 3C2 Implementation Task — Initial and Incremental IMAP Synchronization

**Status:** Approved for Implement
**Date:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3c-plan.md`

## 1. Objective

Implement only initial and incremental synchronization orchestration.

This phase must:
- use the accepted read-only IMAP adapter;
- persist through IMAPSyncRepository;
- process one message occurrence per transaction;
- maintain folder checkpoints;
- support idempotent replay;
- continue other folders when one folder fails.

This phase must NOT yet:
- mark locations unavailable;
- perform move reconciliation;
- reactivate old unavailable locations;
- reconcile UIDVALIDITY history beyond starting the new namespace/window;
- implement threading/AI/scheduler/UI.

## 2. Authorized files

Only:

```text
app/services/__init__.py
app/services/imap_sync.py
test/test_imap_sync.py
```

No other file may change.

## 3. Public service contract

Create:

`synchronize_account(adapter, settings, session_factory, clock) -> SyncResult`

Use immutable result dataclasses as needed.

Result must contain only safe technical data:
- overall state: success/degraded;
- per-folder processed/created/updated/skipped counts;
- safe failure codes;
- no message body;
- no raw headers/MIME;
- no attachment bytes;
- no credentials/server exception text.

## 4. Run flow

For each allowlisted folder that exists:

1. select read-only;
2. obtain selected UIDVALIDITY;
3. obtain a complete UID inventory with `search_uids(None)`;
4. retain that inventory in-memory only as technical UID presence data;
5. inspect existing checkpoint.

If any folder inventory fails:
- mark run degraded;
- that folder fails safely;
- other folders may continue;
- do not perform 3C3 reconciliation in this phase anyway.

## 5. Initial synchronization

If no checkpoint exists for folder:

- compute:
  `since = clock.today() - timedelta(days=settings.initial_window_days)`
- search `search_uids(since)`;
- process positive UIDs in ascending order;
- empty initial result may persist checkpoint:
  `v1:<uidvalidity>:0`
  with successful technical outcome.

Boundary date is inclusive as delegated to adapter SINCE behavior.

## 6. Incremental synchronization

If checkpoint exists and checkpoint UIDVALIDITY == selected UIDVALIDITY:

- use full inventory already obtained;
- filter UIDs strictly greater than highest_committed_uid;
- sort ascending;
- process each in order;
- holes are normal;
- empty set keeps same highest UID and records successful check time.

Do not infer missing UIDs as deletion.

## 7. UIDVALIDITY change in 3C2

If checkpoint UIDVALIDITY != selected UIDVALIDITY:

- do not reuse old highest UID;
- begin new namespace;
- search exactly the same initial historical window:
  `today - initial_window_days`
- process returned UIDs ascending;
- new checkpoint uses new UIDVALIDITY;
- old locations remain untouched;
- no unavailable/move decision here;
- full reset reconciliation semantics remain for 3C3.

## 8. Per-message transaction

For each UID:

1. fetch exactly that UID via adapter;
2. require exactly one FetchedMessage corresponding to requested UID;
3. open one DB session/transaction;
4. instantiate IMAPSyncRepository;
5. resolve exact location first;
6. otherwise apply D1-C conservative candidate matching only when safely possible within 3C2 inputs;
7. persist source/email/location/attachments/idempotency;
8. append ingestion/update observation only when required;
9. append safe audit;
10. advance checkpoint to current UID in same transaction;
11. commit.

If any step fails:
- rollback that message transaction;
- checkpoint must not advance to failed UID;
- stop processing that folder at first failed UID;
- mark folder/run degraded;
- continue other folders.

Repository methods themselves do not commit.

## 9. D1-C correlation in 3C2

For a new location:

- if normalized_message_id absent -> independent occurrence;
- find all account-scoped candidates with same Message-ID;
- reuse only when exactly one candidate exists AND:
  - existing and incoming normalized_body are both complete (content_truncated=False);
  - normalized_body matches exactly;
  - non-null sender matches exactly;
  - non-null sent_at matches exactly;
  - no material conflict in non-null:
    - subject
    - recipient_addresses
    - in_reply_to
    - references_header
- if multiple candidates, missing corroboration, conflict, or uncertainty -> independent occurrence.

3C2 may only correlate across locations if complete folder inventories for all currently allowlisted synchronized folders were successfully obtained in the run. Otherwise create independent occurrence.

Do not use subject/date/body alone as identity.

## 10. Existing exact location replay

If exact location already exists:

- update last_observed_at/state active as needed;
- compare approved email fields;
- replace attachment metadata only if changed;
- append `updated` observation only for material change;
- unchanged replay adds no observation/audit beyond what is explicitly required by plan;
- reserve/reuse occurrence idempotency identity;
- advance checkpoint safely.

Do not change SourceRecord stable identity.

## 11. Canonical persistence mapping

Map FetchedMessage to EmailMessage fields exactly.

Recipient tuple must be serialized deterministically using one explicit stable representation suitable for round-trip comparison in tests.

AttachmentMetadata must map to repository metadata dicts with provenance `imap_sync`.

No raw MIME or bytes may enter persistence.

## 12. Content digest

Create deterministic SHA-256 digest for observation idempotency over the canonical persisted email+attachment metadata state.

Requirements:
- no Python hash();
- deterministic across runs;
- explicit field order;
- safe treatment of nulls;
- body included only as normalized text already approved for persistence;
- digest itself may be stored in observation marker;
- raw content never in audit/result/checkpoint/idempotency.

## 13. Session/transaction behavior

- one DB session/transaction per message occurrence;
- commit only in service;
- rollback on any exception;
- close session safely;
- empty-folder checkpoint update may use one dedicated transaction;
- no transaction spans network fetch calls.

## 14. Tests required

Create `test/test_imap_sync.py` with fake adapter + isolated SQLite/session factory.

Cover:

### Initial sync
- initial_window_days boundary;
- empty folder -> checkpoint UID 0;
- multiple UIDs sorted ascending;
- two folders.

### Incremental
- same UIDVALIDITY;
- checkpoint high-water filtering;
- UID holes;
- restart catches later UID;
- empty incremental run retains high-water mark.

### UIDVALIDITY reset
- old high-water ignored;
- exact initial window used;
- new checkpoint namespace;
- old locations untouched.

### Persistence
- first ingest creates source/email/location/identity/attachments/observation/audit/checkpoint;
- exact replay unchanged is idempotent;
- exact replay changed updates email/attachments and adds update observation;
- missing Message-ID -> independent;
- duplicate Message-ID -> independent;
- one unambiguous conservative candidate -> linked location;
- conflict -> independent;
- partial inventory disables cross-location correlation.

### Failures
Inject failures at:
- select;
- inventory search;
- historical search;
- fetch;
- repository write;
- audit;
- commit.

Verify:
- safe degraded result;
- no raw exception content;
- no checkpoint past failed UID;
- rollback removes partial rows;
- later folder can continue;
- retry succeeds idempotently.

### Security/scope
Assert:
- no adapter mutation method called;
- no keyring/network real access;
- no scheduler;
- no AI;
- no unavailable/move/reactivation transition in 3C2.

## 15. STOP conditions

STOP if implementation requires:
- changes outside authorized files;
- repository/model/migration changes;
- adapter changes;
- new dependency;
- scheduler/main/UI changes;
- external mailbox mutation;
- reconciliation/unavailable logic that belongs to 3C3.

## 16. Validation

Run:

`python -m pytest test/test_imap_sync.py`

Then:

`python -m pytest`

Both must pass.

## 17. Completion protocol

Commit:
`Implement phase 3C2 IMAP synchronization service`

Push only to `origin/codex-work`.

Do not touch `main`.
