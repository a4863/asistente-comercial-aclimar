# Phase 3C Decisions — IMAP Synchronization and Recovery

**Status:** APPROVED
**Date:** 2026-09-22

## D1 — Duplicate Message-ID and move-correlation policy

**Approved: D1-C — Conservative composite correlation.**

Rules:
- A normalized Message-ID is strong evidence, not an absolute unique key.
- Reuse an existing logical email only when normalized Message-ID matches within the configured account scope and there is no material conflict.
- If there are multiple plausible existing candidates, contradictory evidence, or ambiguity, do not auto-merge; preserve the new occurrence/location independently until later reconciliation.
- If Message-ID is absent, preserve the occurrence independently.
- Do not merge based only on subject, participants, dates, CRM context, or other weak evidence.
- A move between synchronized folders may reuse the same logical email when the conservative correlation rule yields one unambiguous candidate.
- Genuine duplicate Message-IDs must remain representable.

## D2 — Reconciliation sufficiency and unavailable/reactivation evidence

**Approved: D2-A — Full reconciliation of all currently allowlisted synchronized folders is required before marking a location unavailable.**

Rules:
- Disappearance from one folder alone never marks a location unavailable.
- A location can move from active to unavailable only after reconciliation has covered every currently configured allowlisted synchronized folder relevant to the account.
- “Full reconciliation” means full within the synchronized allowlist, not every folder in the mailbox.
- If the allowlist expands later, the newly synchronized folders become part of future reconciliation evidence.
- Reactivation changes unavailable -> active and appends a new SourceObservation.
- Historical observations and prior location state evidence are retained; no history is erased.

## D3 — Folder checkpoint and transaction semantics

**Approved: D3-A — One transaction per fetched message; checkpoint advances monotonically after each successfully committed message.**

Rules:
- Commit unit is one message occurrence/location ingestion at a time.
- Checkpoint represents the highest successfully committed positive UID for the folder namespace.
- UID holes are normal; checkpoint is highest committed UID, not message count.
- Checkpoint must advance only in the same durable transaction as the successfully persisted message/location/observation state.
- On failure, checkpoint must not advance past the failed message.
- Safe replay must not duplicate source, email, location, attachment, observation, or idempotency rows.
- Failures may be recorded only with safe technical identifiers/outcomes; no raw message body, raw MIME, attachment bytes, or credentials.

Canonical checkpoint semantics to be fixed in plan:
- scope keyed by account_scope + folder;
- marker contains UIDVALIDITY + highest committed UID in a deterministic format.

## D4 — UIDVALIDITY reset reconciliation window

**Approved.**

Rules:
- On UIDVALIDITY change, the old cursor is not reused.
- Start a new namespace for the new UIDVALIDITY.
- Historical reconciliation window is exactly the configured initial_window_days.
- The window is applied per folder.
- Cross-namespace/cross-folder correlation follows D1-C.
- Old locations are not marked unavailable merely because UIDVALIDITY changed.
- Unavailable requires the reconciliation sufficiency defined by D2-A.
- If correlation is ambiguous after reset, preserve the new occurrence independently rather than forcing a merge.

## Implementation consequence

Proceed to planning with:
- 3C1 persistence/repository boundary;
- 3C2 initial + incremental transactional synchronization;
- 3C3 reconciliation/recovery.

No implementation may weaken these decisions without a new explicit decision record.
