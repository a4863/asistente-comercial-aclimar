# Phase 3C3 Implementation Task — IMAP Reconciliation and Recovery

**Status:** Approved for Implement
**Date:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3c-plan.md`
**Decisions:** `docs/plans/implementation-phase-3c-decisions.md`

## 1. Objective

Implement only reconciliation/recovery behavior on top of the accepted 3C2 service.

This phase closes:
- cross-folder move recognition under D1-C;
- active -> unavailable after complete allowlist reconciliation;
- unavailable -> active reactivation;
- UIDVALIDITY reset recovery semantics;
- safe retry of reconciliation transitions.

No threading, AI, scheduler, UI, mailbox mutation, or real-account access.

## 2. Authorized files

Only:

```text
app/services/imap_sync.py
app/persistence/repositories.py
test/test_imap_sync.py
test/test_persistence_repositories.py
```

No other file may change.

## 3. D2-A complete reconciliation gate

A reconciliation pass is eligible only if:

- every currently configured allowlisted synchronized folder that exists was successfully selected;
- every such folder produced a complete `ALL` UID inventory;
- every UID required for this run was fetched/persisted successfully;
- no folder in the account run is degraded.

If any condition fails:
- do not mark any location unavailable;
- do not execute move/unavailable/reactivation reconciliation transitions;
- return degraded/safe technical result as already defined.

“Complete” means complete inside the synchronized allowlist, not the entire mailbox.

## 4. Reconciliation order

After successful ingestion for all eligible folders:

1. build the set of currently observed location tuples from inventories;
2. inspect persisted active/unavailable locations for the account;
3. resolve exact reappearance first;
4. resolve unambiguous cross-folder move evidence under D1-C;
5. only then classify unmatched active locations as unavailable;
6. preserve all sources/emails/attachments/history.

Each location transition must use its own local DB transaction.

## 5. Reactivation

If a persisted location currently `unavailable` is present again in the complete inventory with same:
- account_scope
- folder_name
- uidvalidity
- uid

Then:

- transition to `active`;
- update last_observed_at;
- append `reactivated` SourceObservation;
- append safe `imap_location_transitioned` AuditEvent;
- never delete prior observations;
- transition is idempotent on replay.

If exact reactivation was already handled during ingestion logic, integrate safely so there is one transition/observation only.

## 6. Move recognition

A move means:
- old active location no longer present;
- newly persisted location exists elsewhere in synchronized allowlist;
- both locations resolve to the same EmailMessage/SourceRecord under accepted D1-C correlation;
- complete reconciliation evidence exists.

Then:
- new location remains active;
- old location becomes unavailable;
- append transition observation for old location;
- append a move/reconciliation observation sufficient to retain evidence without duplicating unchanged events;
- safe audit only;
- source/email identity remains unchanged.

Do not create a user-visible deletion state.

## 7. Unavailable transition

For each persisted `active` location absent from its exact complete inventory:

- if a move match has already linked same logical email, mark old location unavailable as move outcome;
- otherwise, after complete allowlist reconciliation, mark location unavailable with outcome `unavailable`;
- append SourceObservation;
- append safe audit;
- do not alter SourceRecord retention_state;
- do not delete EmailMessage or attachments.

Replay with unchanged unavailable state must append nothing.

## 8. UIDVALIDITY reset recovery

When folder checkpoint namespace changed in 3C2:

- new namespace ingestion remains exactly initial_window_days;
- old-namespace locations stay untouched until complete allowlist reconciliation succeeds;
- after successful full reconciliation, old locations not present in any current exact inventory may become unavailable;
- if new namespace location correlated to same logical email under D1-C, treat as move/replacement-location evidence;
- ambiguity remains separate; never force merge;
- reset alone never marks unavailable.

## 9. Repository additions allowed

Only repository methods necessary for 3C3, such as:
- list all account locations with email/source relation;
- list locations across account regardless of current namespace;
- helper query for exact current inventory membership/correlation;
- transition helper if needed.

Repository remains:
- session-injected;
- non-committing;
- no adapter/network calls.

No model/migration changes.

## 10. Transaction and retry rules

- each transition in its own transaction;
- observation + audit + state change commit atomically;
- rollback on any failure;
- failed transition leaves prior state unchanged;
- later service run retries safely;
- no unbounded immediate retry loop;
- failure codes sanitized.

## 11. Result reporting

Extend SyncResult/FolderSyncResult only if necessary, preserving compatibility.

May report safe counts such as:
- moved;
- unavailable;
- reactivated;
- reconciliation_skipped.

Never include:
- subject/body/content;
- raw headers/MIME;
- attachment bytes;
- credentials;
- exception/server strings.

## 12. Tests required

### Complete vs partial coverage
- complete allowlist permits reconciliation;
- one failed inventory blocks all unavailable transitions;
- one failed message persistence blocks reconciliation;
- partial coverage preserves active states.

### Move
- old location disappears, new correlated location elsewhere -> old unavailable/new active/same source;
- ambiguous Message-ID/correlation does not force move;
- replay does not duplicate observations.

### Unavailable
- unmatched active location absent after full reconciliation -> unavailable;
- source retention unchanged;
- email/attachments retained;
- replay unchanged -> no new transition.

### Reactivation
- exact unavailable location reappears -> active;
- new reactivated observation every real recurrence;
- repeated unchanged run -> no duplicate;
- active -> unavailable -> active -> unavailable -> active history preserved.

### UIDVALIDITY
- reset alone does not mark old namespace unavailable when reconciliation incomplete;
- full successful reconciliation may mark absent old namespace location unavailable;
- correlated new namespace location keeps same logical source where D1-C is satisfied;
- ambiguous reset occurrence remains independent.

### Failure recovery
Inject failure in:
- location state update;
- observation append;
- audit append;
- transition commit.

Verify:
- rollback;
- prior state preserved;
- safe degraded result;
- later retry succeeds;
- no duplicate observations/audit.

### Scope/security
Assert no:
- mailbox mutation;
- real network/keyring;
- scheduler;
- threading;
- AI;
- CRM/Calendar;
- raw content in results/audit/checkpoint/idempotency.

## 13. STOP conditions

STOP if implementation requires:
- schema/model/migration change;
- adapter modification;
- changes outside authorized files;
- new dependency;
- mailbox mutation;
- deletion state invention;
- weakening D1-C/D2-A/D3-A/D4.

## 14. Validation

Run:

`python -m pytest test/test_imap_sync.py test/test_persistence_repositories.py`

Then:

`python -m pytest`

Both must pass.

## 15. Completion protocol

Commit:
`Implement phase 3C3 IMAP reconciliation and recovery`

Push only to `origin/codex-work`.

Do not touch `main`.
