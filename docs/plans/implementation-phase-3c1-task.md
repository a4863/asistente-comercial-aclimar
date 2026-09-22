# Phase 3C1 Implementation Task — IMAP Synchronization Persistence Boundary

**Status:** Approved for Implement
**Date:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3c-plan.md`

## 1. Objective

Implement only the persistence/repository boundary required by Phase 3C.

No synchronization service, adapter calls, scheduler, threading, AI, or external access.

## 2. Authorized files

Only:

```text
app/persistence/repositories.py
test/test_persistence_repositories.py
```

No other file may change.

## 3. Repository boundary

Add an email synchronization repository using an injected SQLAlchemy Session.

Repository methods must not commit the session and must not call IMAP.

Required capabilities:

1. Find exact IMAP location by:
   - account_scope
   - folder_name
   - uidvalidity
   - uid
   and load related EmailMessage + SourceRecord.

2. Find all account-scoped EmailMessage candidates by non-empty normalized Message-ID.
   - never assume uniqueness;
   - return all candidates.

3. Create a new SourceRecord + EmailMessage for an independent occurrence.

4. Link a new IMAPMessageLocation to an already resolved EmailMessage.

5. Create/reuse occurrence IdempotencyIdentity using:
   - operation_kind = `imap_occurrence`
   - scope = `imap-account:v1:` + deterministic SHA-256(account_scope)
   - identity_key = `v1:` + deterministic location key
   - source_record_id = resolved source

6. Update IMAPMessageLocation:
   - state active/unavailable
   - last_observed_at
   - reactivation supported.

7. Compare/update approved EmailMessage fields:
   - normalized_message_id
   - sender_address
   - recipient_addresses
   - subject
   - sent_at
   - received_at
   - in_reply_to
   - references_header
   - normalized_body
   - body_size_bytes
   - content_truncated
   - provenance
   Return whether material state changed.

8. Replace attachment metadata by part_index only when canonical metadata changes.
   - no bytes;
   - deterministic comparison;
   - no unnecessary delete/reinsert when unchanged if avoidable.

9. Append SourceObservation using the approved bounded version-marker contract.
   - first ingestion;
   - material update;
   - location transition;
   - completed reconciliation finding.
   - unchanged replay adds nothing.

10. Append safe AuditEvent.
    - technical operation;
    - local record identifiers;
    - bounded outcome;
    - timestamp;
    - no message body/raw headers/raw MIME/attachment bytes/credentials/server error text.

11. Read/upsert folder checkpoint:
    - scope = `imap-folder:v1:` + SHA-256(account_scope, folder_name)
    - marker = `v1:<uidvalidity>:<highest_committed_uid>`
    - malformed marker fails closed.
    - no commit inside repository.

12. List:
    - active locations for account/folder/UIDVALIDITY;
    - all locations related to a source/email as needed for later reconciliation.

## 4. Deterministic identity helpers

Implement only internal helpers necessary for repository semantics.

Location key:
- SHA-256 over UTF-8 length-prefixed components:
  - account_scope
  - folder_name
  - uidvalidity
  - uid

Do not use ambiguous delimiter concatenation.

Stable external ID for new independent occurrence:
- `imap-occ:v1:<location_key>`

Source:
- source_system_scope = account_scope
- source_type = `email_message`

Do not change stable_external_id later if another location is linked to the same email.

## 5. Constraints

- Existing models only.
- No migration.
- No model changes.
- No repository commit.
- No adapter import/call.
- No network/keyring.
- No service layer.
- No main/routes/UI.
- No schema invention.
- Preserve existing repository behavior.

## 6. Tests required

Extend `test/test_persistence_repositories.py` with isolated SQLite tests covering:

### Exact location
- create/find exact location;
- unique tuple replay resolves same logical records;
- multiple locations can point to one EmailMessage.

### Message-ID candidates
- one candidate;
- duplicate Message-ID returns multiple candidates;
- missing Message-ID excluded from candidate lookup.

### Independent occurrence
- stable external ID derived from location key;
- source/email one-to-one preserved;
- duplicate Message-ID can create separate SourceRecord/EmailMessage.

### Idempotency
- same location reuses identity;
- identity disagreement with another source fails safely;
- no duplicate identity rows.

### Email update
- unchanged values -> changed=False;
- material field update -> changed=True;
- no unapproved fields modified.

### Attachments
- unchanged metadata remains idempotent;
- changed metadata replaced/upserted deterministically;
- removed metadata handled deterministically;
- no payload/bytes field introduced.

### Observation
- first ingestion marker;
- update/transition marker;
- unchanged replay produces no new observation;
- marker bounded and unique.

### Checkpoint
- deterministic scope;
- parse valid marker;
- reject malformed marker;
- highest UID supports holes;
- upsert without commit.

### Location state
- active -> unavailable;
- unavailable -> active;
- last_observed_at update;
- history not deleted.

### Transaction behavior
- repository methods do not commit;
- caller rollback removes staged changes;
- uniqueness conflict is recoverable by re-read.

## 7. STOP conditions

STOP if implementation requires:
- model change;
- migration;
- new dependency;
- changes outside two authorized files;
- direct adapter/network/keyring access;
- service orchestration;
- schema field not present for an approved invariant.

## 8. Validation

Run:

`python -m pytest test/test_persistence_repositories.py`

Then:

`python -m pytest`

Both must pass.

## 9. Completion protocol

Commit:
`Implement phase 3C1 IMAP synchronization repositories`

Push only to `origin/codex-work`.

Do not touch `main`.
