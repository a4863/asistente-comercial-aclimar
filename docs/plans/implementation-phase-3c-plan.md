# Phase 3C Plan — IMAP Synchronization and Recovery

**Status:** READY FOR APPROVAL
**Date:** 2026-09-22
**Baseline:** `17c00f9` (`codex-work`)
**Inputs:** `implementation-phase-3c-analysis.md`, `implementation-phase-3c-decisions.md`, and the approved 3A/3B contracts

## 1. Objective and boundary

Add a local application service that ingests the configured, allowlisted IMAP folders, persists normalized messages and technical locations, resumes from durable folder checkpoints, and reconciles unavailable/reactivated locations conservatively. The service reads through the existing read-only adapter. No scheduler, UI, conversation reconstruction, semantic extraction, AI, mailbox mutation, or real account connection is included.

The three separately approvable implementation blocks are 3C1 (repository boundary), 3C2 (initial/incremental ingestion), and 3C3 (reconciliation/recovery). Approval of this plan alone does not authorize implementation.

## 2. Approved decisions applied

- **D1-C:** Message-ID is evidence, not a unique key. Reuse requires one unambiguous account-scoped candidate plus corroboration and no material conflict. Missing or conflicting IDs remain separate occurrences.
- **D2-A:** Only a successful complete UID inventory of every currently allowlisted synchronized folder can support an `active → unavailable` transition. Reappearance appends an observation.
- **D3-A:** One transaction per message occurrence. A folder checkpoint advances in the same commit as that occurrence and never past a failed UID. Holes in UID sequences are normal.
- **D4:** A changed UIDVALIDITY creates a new namespace; read the exact configured `initial_window_days` for that folder. Old locations are not invalidated solely by the reset.

## 3. Current state and files

The existing `ReadOnlyIMAPAdapter` provides read-only selection, `search_uids(since)` and bounded `fetch_messages(uids)`. The 3A tables hold one `EmailMessage` per `SourceRecord`, multiple `IMAPMessageLocation` rows per email, metadata-only attachments, generic observations, checkpoints, idempotency identities, and audit events. `SourceRepository` exposes generic source/observation/checkpoint/idempotency helpers but no email-specific lookup or upsert. No synchronization service exists.

Proposed implementation files, subject to the subphase Scope Locks below:

- `app/persistence/repositories.py` and `test/test_persistence_repositories.py` for 3C1;
- `app/services/__init__.py`, `app/services/imap_sync.py`, and `test/test_imap_sync.py` for 3C2/3C3.

No model or migration change is required by the plan. If a later implementation proves a field or constraint essential, stop and obtain a separate model/migration decision before changing schema.

## 4. Exact identity and correlation contract

### Technical identifiers

Define a local deterministic SHA-256 helper over UTF-8, length-prefixed components to avoid delimiter ambiguity. Its input is never logged. `location_key = SHA256(account_scope, folder_name, uidvalidity, uid)`; `SourceRecord.source_system_scope = account_scope`, `source_type = "email_message"`, and `stable_external_id = "imap-occ:v1:" + location_key` at creation. That stable ID remains unchanged if another location is later linked to the same source. Every new independent occurrence has its own source and email row, including a duplicate or missing Message-ID. The unique location tuple remains the authoritative location identity.

Use `IdempotencyIdentity(operation_kind="imap_occurrence", scope="imap-account:v1:" + SHA256(account_scope), identity_key="v1:" + location_key, source_record_id=<resolved source>)`. An existing identity/location must resolve to the same source; disagreement is an error, not a merge. An additional location linked to an existing email gets its own occurrence identity. The unique database constraints are the final replay guard; conflicts roll back the message transaction and are re-read before any retry.

### Conservative cross-location correlation

First resolve an exact existing location; never re-correlate it. For a new location, search account-scoped `EmailMessage` rows by non-empty normalized Message-ID. Reuse only when exactly one candidate exists, the candidate has a complete (not truncated) normalized body, the incoming body is complete, both normalized bodies match byte-for-byte, and non-null sender address and parsed `sent_at` match exactly. A different non-null subject, recipients, `In-Reply-To`, or `References` is a material conflict. Null/missing corroboration, multiple candidates, conflicting fields, or a currently present old location in the complete folder inventory means create an independent occurrence. No subject, participant, date, CRM context, or body match alone permits a merge. This intentionally leaves some true moves as separate records when evidence is insufficient; it never forces a merge. A later, separately approved reconciliation may resolve them.

The complete folder inventory used for the “old location absent” check must cover all currently allowlisted synchronized folders. If that inventory is unavailable, do not correlate across locations in that run. A duplicate Message-ID with conflicting data is therefore representable as its own source/email. A Message-ID absent from a message always creates an independent source/email for a new location.

## 5. Observation, checkpoint, and audit contract

`SourceObservation` is appended only on first persisted occurrence, a material content/header/attachment change, a location transition, or a completed reconciliation finding. It is not appended for an unchanged read. Use the bounded marker `imap:v1:<64-hex-location-key>:<event-kind>:<ordinal>:<64-hex-canonical-content-digest>`. The ordinal is one greater than the count of prior committed observations for that source and the marker prefix identifying that location/event series, computed within the transaction; retrying an unchanged committed state appends nothing. `observed_state` is `active` or `unavailable`; `outcome` is a bounded technical value such as `ingested`, `updated`, `moved`, `unavailable`, or `reactivated`. `provenance` contains only an IMAP synchronization label. The source record’s retention state is not changed merely because one or all synchronized locations are unavailable; unavailability is not proof of deletion from the mailbox.

Checkpoint scope is `"imap-folder:v1:" + SHA256(account_scope, folder_name)` (below the 100-character column limit). Marker is ASCII `"v1:<positive UIDVALIDITY>:<nonnegative highest_committed_UID>"` (below 255 characters). `0` means no committed UID in that namespace. Malformed markers fail closed with a safe synchronization error. `last_success_at` changes only after a successful committed occurrence or completed empty inventory; `last_outcome` remains a bounded technical status. No checkpoint for a folder is advanced when selecting, searching, fetching, parsing, or persisting that folder fails. Sort UIDs numerically; commit each positive UID in ascending order; stop the folder at its first failed UID. The next run replays from the committed high-water mark. A gap in UID numbering is not a failure.

`AuditEvent` records only technical operation names, affected local record IDs, safe outcome/failure codes, and timestamps. It never contains body text, raw headers/MIME, attachment bytes, credentials, or server exception strings. A failure before a source exists may be attached to the folder checkpoint record when present; otherwise it remains a sanitized service result/local log, with no invented source row. Failed audit writes roll back the same message transaction.

## 6. 3C1 — persistence/repository boundary

Add an email synchronization repository in `app/persistence/repositories.py` with session-injected, non-committing methods to:

1. find location by its unique tuple and load its email/source;
2. find all account-scoped email candidates by normalized Message-ID without assuming uniqueness;
3. create a source/email or link a new location to a resolved email;
4. create/reuse the exact occurrence idempotency identity;
5. update location state and `last_observed_at`;
6. compare and update approved email metadata/body fields;
7. replace attachment metadata by `part_index` only when the canonical metadata set materially changes, keeping no bytes;
8. append the defined observation and safe audit event;
9. read/upsert the exact folder checkpoint;
10. list active locations for an account/folder/UIDVALIDITY and locations related to a source.

The repository must not call the IMAP adapter or commit its session. Keep the existing generic repository public behavior stable. Persistence tests exercise uniqueness, source reuse, duplicate/missing Message-ID, metadata replacement, observation idempotency, and rollback on a synthetic SQLite database.

## 7. 3C2 — initial and incremental synchronization

Service API: `synchronize_account(adapter, settings, session_factory, clock) -> SyncResult`, with per-folder counts, safe failure codes, and degraded/success state; no secrets or message data in the result. The caller supplies a fake adapter and isolated session factory in tests. The service does not start a scheduler or open a real mailbox on import.

At run start, discover existing allowlisted folders and select each read-only. Take a complete UID inventory (`ALL`) of every selected folder for D1 correlation and later D2 reconciliation. If any inventory fails, ingestion of successfully inventoried folders may continue, but cross-location correlation and unavailable transitions are disabled for that run.

For a folder without a checkpoint, search `SINCE` at `clock.today() - initial_window_days`, including the boundary date. For a valid same-UIDVALIDITY checkpoint, search `ALL`, filter UIDs strictly above its committed high-water mark, and process in ascending order; this catches downtime without a historical rescan. A zero-day window is the current configured date. Fetch each UID through the bounded adapter, then begin one local transaction. Resolve exact location or conservative logical candidate, write source/email/location/attachments/idempotency/observation/audit, and advance checkpoint to that UID in the same commit. On fetch or transaction failure, stop processing that folder at that UID; other folders may continue independently. Empty successful initial or incremental inventory may record marker UID `0`/existing high-water mark and successful check time without fabricating a message.

An exact location replay checks for material data change and avoids duplicate source/email/location/attachment/idempotency/observation rows. If content or headers differ, update the local representation and append a new observation in the same transaction. `received_at` remains null unless a source-provided server timestamp is available; it is not inferred from the local clock. Recipient addresses use a canonical deterministic serialization. Existing `SourceRecord` identity and initial ingestion timestamp never change. An existing email’s body/metadata is updated only by an exact location observation or an unambiguous correlated location with consistent fields; conflicting data creates a separate source.

## 8. 3C3 — reconciliation and recovery

After all allowlisted folders have been successfully inventoried and all fetched UIDs required for this run have committed, compare active location tuples against the complete inventories. A location missing from its current folder inventory is not immediately unavailable. First use D1-C to see whether a newly observed location unambiguously represents the same email. Record a move as the new location plus an observation; then transition the old location to `unavailable` with its own observation. If no match exists, transition the missing location to `unavailable` only after the same complete allowlist reconciliation. Keep the source, email, attachment metadata, and historical observations. An old location observed again becomes `active` and gets a `reactivated` observation. Apply each location transition in its own transaction with a safe audit event; on failure leave it unchanged and retry later.

When UIDVALIDITY differs from the checkpoint, do not use the old high-water mark. Start a new marker with the selected namespace and search `SINCE` using exactly `initial_window_days` for that folder. Correlate only under D1-C. Retain old-namespace locations through the reset until a subsequent complete allowlist inventory and successful processing/reconciliation establish their current state. A reset alone does not imply source deletion, and an ambiguous new occurrence remains separate. The full UID inventories may include older UIDs for presence evidence; the reset ingestion fetch window stays exactly the configured historical interval.

Failure handling is bounded at the service level: close the adapter/session safely; return an IMAP-specific degraded result and safe failure code; perform no immediate unbounded retry. A later caller may invoke the same idempotent service again. A previous committed message remains durable, a failed message’s transaction rolls back, and its checkpoint does not advance. Previously stored local data remains available. The service never executes mailbox mutations.

## 9. Dependencies and risks

Internal dependencies are the accepted adapter/configuration, existing SQLAlchemy session factory and 3A models, source/checkpoint/audit repositories, and an injected clock. No new package is required. The adapter must stay read-only and no test may access real keyring or IMAP.

Main risks are falsely merging duplicate IDs, classifying disappearance on partial folder coverage, advancing a cursor before persistence, repeating observations after retry, and exposing source content in operational records. The correlation guard, complete inventory gate, per-message transaction, deterministic identity, and sanitized audit/result contracts address them. The conservative rule can leave a real move represented as two logical emails; this is an explicit safe ambiguity outcome, not a reason to merge weak evidence.

## 10. Fake-only verification matrix

### 3C1

- Isolated SQLite repository tests for exact location uniqueness, one-to-one source/email, multiple locations, duplicate and absent Message-ID, idempotency replay, canonical attachment replacement, observation uniqueness, and no secret/raw MIME/bytes fields.

### 3C2

- Fake adapter tests for initial window boundary, incremental UID gaps, ascending order, checkpoint marker/scoping, two folders, restart catch-up, unchanged replay, changed content, missing Message-ID, duplicate/conflicting Message-ID, and one transaction per message.
- Inject failures at fetch, parse, source/attachment insert, audit append, and commit; verify rollback and no checkpoint past the failed UID.

### 3C3

- Full versus partial allowlist inventory; cross-folder move with one unambiguous candidate; ambiguity retained separately; missing location after full inventory; reactivation with a new observation; allowlist expansion; UIDVALIDITY reset with exact per-folder historical window; old namespace retained until sufficient reconciliation; failure during transition and safe replay.
- Assert no real network/keyring, `APPEND`, `MOVE`, `COPY`, draft/send, full-message fetch, attachment-body fetch, threading, AI, Calendar, CRM, scheduler, or UI call.

For each implementation block, run its focused tests and then `python -m pytest`; verify the complete diff before commit. All fixtures are synthetic.

## 11. Scope Lock per implementation block

### 3C1 — IN SCOPE

- `app/persistence/repositories.py`
- `test/test_persistence_repositories.py`

### 3C2 — IN SCOPE

- `app/services/__init__.py` (new)
- `app/services/imap_sync.py` (new)
- `test/test_imap_sync.py` (new)

### 3C3 — IN SCOPE

- `app/services/imap_sync.py`
- `app/persistence/repositories.py` only for reconciliation queries/transitions already specified here
- `test/test_imap_sync.py`
- `test/test_persistence_repositories.py` only for those repository changes

### OUT OF SCOPE FOR ALL BLOCKS

`app/integrations/imap_adapter.py`, `app/config.py`, credentials, models, migrations, `app/main.py`, routes/templates, scheduler, threading/conversation code, AI, Calendar, CRM, SMTP, mailbox mutation, real account/keyring/network access, dependency changes, and `main`.

### RESTRICTIONS

- Each block needs its own approved implementation task and file list; no block inherits permission to implement the next.
- Do not modify schema or invent a source deletion state. If the existing schema cannot support an approved invariant, stop for a separate decision.
- Do not place raw message content, credentials, or server exceptions in logs, audit, checkpoint, idempotency, or result fields.
- Do not advance checkpoints outside the message commit, or mark unavailable without complete allowlist coverage.

## 12. Acceptance and open decisions

The plan is ready for approval if an implementer can build 3C1–3C3 using only the listed files, fake-only tests prove the D1–D4 invariants, and no schema or external action is required. The four decisions from the analysis are resolved by `implementation-phase-3c-decisions.md` and are not reopened here. No further functional decision is required for this plan. Any newly discovered schema need or contradictory real protocol behavior is a stop condition, not implied authorization to expand scope.
