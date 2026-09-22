# Phase 3C Analysis — IMAP Synchronization and Recovery

**Status:** STOPPED FOR DECISION  
**Date:** 2026-09-22  
**Baseline:** `codex-work` after Phase 3B2

## 1. Objective

Assess the local, persistent synchronization and recovery service between the accepted read-only IMAP adapter and the approved email persistence model. The proposed capability is limited to reading, retaining, observing, reconciling, checkpointing, and recovering. It excludes threading, semantic analysis, UI, scheduling, and every external mutation.

## 2. Context and interpretation

Phase 3A supplies `EmailMessage`, `IMAPMessageLocation`, attachment metadata, non-secret IMAP settings, and the credential boundary. Phase 3B supplies a fake-testable read-only adapter that searches UIDs and selectively retrieves normalized message data. Phase 3C must join those boundaries through an application service while preserving provenance, historical state, idempotency, and safe recovery after an interrupted run.

Mailbox data, folder names, headers, bodies, and protocol errors remain untrusted data. No mailbox content is an instruction, and this phase has no authority to mutate the mailbox.

## 3. Documentation consulted

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/plans/implementation-phase-3c-analysis-task.md`
- `docs/plans/implementation-phase-3-imap-analysis.md`
- `docs/plans/implementation-phase-3-imap-decisions.md`
- `docs/plans/implementation-phase-3a-plan.md`
- `docs/plans/implementation-phase-3b-analysis.md`
- `docs/plans/implementation-phase-3b-plan.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `app/integrations/imap_adapter.py`
- current persistence and IMAP adapter tests.

## 4. Current state

The accepted adapter is read-only, fake-testable, and returns normalized `FetchedMessage` values plus attachment metadata. It has no synchronization, source persistence, transaction, retry, checkpoint, or reconciliation behavior.

The physical model contains:

- `SourceRecord`, `SourceObservation`, `SynchronizationCheckpoint`, and `IdempotencyIdentity`;
- `EmailMessage` with a one-to-one `SourceRecord` link;
- `IMAPMessageLocation`, unique by `(account_scope, folder_name, uidvalidity, uid)`, with `active`/`unavailable` current state;
- metadata-only attachments.

`SourceRepository` can create/reuse a source by stable external identifier, append observations, upsert one opaque checkpoint marker per scope, and reserve idempotency identities. It has no email/location synchronization repository or application service. No source records, checkpoints, locations, or observations are yet created from IMAP data.

## 5. Confirmed constraints and affected elements

### Confirmed requirements

- The cursor is account + folder + UIDVALIDITY + highest processed UID; a UIDVALIDITY change starts a namespace and requires historical-window reconciliation.
- Location identity is account + folder + UIDVALIDITY + UID. A normalized Message-ID is a logical identity when present; absent IDs preserve an occurrence and never permit aggressive merging.
- A disappearance from one folder is not deletion. A local historical record is retained, and a source is only unavailable/deleted after sufficient reconciliation.
- Only normalized body and metadata-only attachment information may persist; raw MIME and attachment bytes are forbidden.
- Checkpoints advance only after durable successful work. Retries must be idempotent, failures must be isolated and auditable, and no real mailbox or credential access is permitted in tests.

### In scope for a later approved implementation

- one IMAP synchronization application service;
- email/location/source/observation/checkpoint/idempotency persistence boundaries;
- transaction and recovery behavior;
- fake-only synchronization, failure, idempotency, and reconciliation tests.

### Out of scope

- IMAP adapter changes; real IMAP or keyring access; scheduler; UI; threading; AI; CRM/Calendar; schema changes until separately approved; SMTP, drafts, moves, sends, or any external mutation.

## 6. Candidate service boundary, pending the decisions below

The architecture supports an application-level service, conceptually `IMAPSynchronizationService`, dependent on the read-only adapter, a unit-of-work/session boundary, and synchronization-specific persistence methods. It would select an allowlisted folder read-only, derive the incremental UID set, retrieve bounded messages, persist source/location/observations, and advance a folder checkpoint only in the committing transaction.

The adapter must remain unaware of persistence, transactions, retries, source identity, or move semantics. Repositories must remain unaware of IMAP protocol calls. This is an architectural boundary, not an authorization to implement it.

## 7. Schema and decision-gap analysis

The current tables can retain multiple technical locations for one `EmailMessage`, UIDVALIDITY namespaces, current `active`/`unavailable` location state, and a checkpoint marker scoped by a caller-provided string. They do not by themselves settle the following required semantics.

1. `SourceRecord` has a unique `(source_system_scope, stable_external_id)` while `EmailMessage` is one-to-one with it. Using normalized Message-ID as that stable identifier would collapse genuine duplicate Message-IDs; using location identity instead would create a separate email/source for a move. The approved documents prohibit both an aggressive merge and treating a move as conceptually new. A correlation policy is therefore required.
2. `SourceObservation` belongs to a source, not to an IMAP location, and has a unique source/version marker. The required representation of repeated folder observations, unavailable transitions, reactivation, and reconciliation evidence is unspecified.
3. `SynchronizationCheckpoint` has only an opaque marker and one caller-defined scope. It can technically store a serialized UIDVALIDITY/highest-UID cursor, but the canonical scope and marker format, reset handling, and success/failure semantics are not approved.
4. `IMAPMessageLocation` has current state but no location-transition history or reconciliation-run reference. Whether the existing `SourceObservation` is sufficient depends on the required marker and evidence rules, which are not defined.

No schema change is proposed by this analysis. The gaps require decisions before a safe implementation plan can decide whether existing fields/repositories suffice or a migration is necessary.

## 8. Decisions required

### D1 — Duplicate Message-ID and move-correlation policy

Choose how a newly observed location is associated with an existing logical email.

- **A. Message-ID is sufficient within the account scope.** This preserves cross-folder moves but can incorrectly merge genuine duplicates.
- **B. Location identity is always distinct.** This preserves duplicates but treats a move as a new physical email/source until a later user/system reconciliation rule exists.
- **C. Correlate only with an approved conservative composite evidence rule.** This can preserve moves and duplicates, but the exact evidence, conflict handling, and no-match behavior must be approved.

This decision controls `SourceRecord` reuse, `EmailMessage` reuse, idempotency, and location creation.

### D2 — Reconciliation sufficiency and unavailable/reactivation evidence

Define when a location may move from `active` to `unavailable` and how a reappearance is recorded.

- **A. Full allowlisted-folder UID reconciliation is required.** Strongest evidence, potentially higher read cost.
- **B. The configured historical window is sufficient.** Lower cost, but older moved/disappeared locations cannot be conclusively assessed.
- **C. A separately persisted reconciliation coverage/run marker establishes sufficiency.** Precise and auditable, but may require schema or a defined marker contract.

The decision must state whether reactivation appends a new `SourceObservation`, which observation markers are unique, and whether any current source retention state changes.

### D3 — Folder checkpoint and transaction semantics

Define the exact checkpoint scope/marker and commit unit.

- **A. One transaction per fetched message, advancing the checkpoint monotonically after each committed message.** Allows partial progress; recovery resumes after the last committed UID.
- **B. One transaction per folder batch, advancing only after the whole batch commits.** Simpler checkpoint relation; safely replays the entire batch after a failure.

Either choice must specify: canonical `source_system_scope`; UIDVALIDITY/highest-UID marker encoding; treatment of holes (highest successful positive UID, not count); outcome on a fetch/persistence failure; and the audit/observation record for a failed run. The current generic marker does not define these semantics.

### D4 — UIDVALIDITY-reset reconciliation window and cross-folder move detection

The approved decision requires a historical-window reconciliation after reset, but does not define whether the window is exactly `initial_window_days`, whether it is per folder or account, or the evidence that permits matching a reset namespace location to an older one. This must be decided together with D1 and D2; otherwise reset recovery can either duplicate sources or falsely mark records unavailable.

## 9. Identity, idempotency, and lifecycle implications

Once D1–D4 are approved, a future plan must define all of the following exactly:

- source stable identifier for a Message-ID, absent Message-ID, and a true duplicate Message-ID;
- idempotency operation kind, scope, and key for ingestion versus location observation;
- whether a retained email body/headers can be updated on an existing logical email, and the observation marker that proves the update;
- attachment metadata replacement/upsert rule and its relationship to the unique `(email_message_id, part_index)` constraint;
- an initial sync bounded by the approved historical window;
- incremental search strictly above the highest successfully committed UID, with holes handled by UID ordering rather than message counts;
- failed-run behavior: no checkpoint advancement beyond durable work, safe replay, no duplicate source/location/attachment rows, and a safe audit/degraded-state record;
- reactivation and move/unavailable transitions that add history rather than erase prior location evidence.

## 10. Risks

| Risk | Consequence | Required mitigation |
| --- | --- | --- |
| Message-ID-only correlation | False merge of different messages | Decide D1 before persistence design. |
| Location-only identity | One move becomes multiple logical emails | Decide D1 before source reuse. |
| Insufficient reconciliation | False unavailable/deleted state | Decide D2 and D4. |
| Checkpoint commits too early | Lost messages after a crash | Decide D3; commit checkpoint with durable work only. |
| Retry without stable identity | Duplicate sources, attachments, or observations | Define idempotency keys and transaction model. |
| Unsafe logs/audit | Commercial-content or credential exposure | Store only minimum safe identifiers/outcomes; no raw MIME/body/secrets. |
| External content | Prompt-injection or behavior confusion | Treat all fetched content as inert data; no AI in 3C. |

## 11. Required test matrix after approval

- fake-only first-window and incremental UID selection, including holes;
- checkpoint scope/marker and advancement only after the approved commit point;
- rollback/retry after fetch, parse, persistence, and audit failures;
- no duplicate source, email, location, attachment, observation, or idempotency identity on replay;
- UIDVALIDITY reset and the approved historical reconciliation rule;
- appearance in another synchronized folder, disappearance, unavailable transition, and reactivation;
- duplicate and absent Message-ID cases under the approved D1 policy;
- metadata/body update and attachment replacement behavior;
- audit/provenance and degraded-state outcomes without raw content or secrets;
- no real network, keyring, mailbox mutation, attachment bytes, threading, scheduler, CRM, Calendar, or AI activity.

## 12. Proposed subphases after decisions

1. **3C1 — persistence/repository boundary:** only the approved repository methods and, if explicitly necessary, an approved migration.
2. **3C2 — initial and incremental folder synchronization:** fake adapter orchestration, transactional ingestion, checkpoint progression, and idempotent replay.
3. **3C3 — reconciliation and recovery:** UIDVALIDITY reset, cross-folder correlation, unavailable/reactivation, and degraded/recovery audit behavior.

Each subphase requires a separate approved plan and Scope Lock. The split prevents reconciliation semantics from being inferred while implementing basic ingestion.

## 13. Scope Lock for any future 3C implementation

### IN SCOPE

Only files named in a later approved subphase plan: synchronization application service, explicitly required persistence repositories/models/migration, and their focused fake-only tests.

### OUT OF SCOPE

IMAP adapter behavior, credentials/configuration, real IMAP/keyring/network access, UI/routes/main, scheduler, threading, AI, Calendar, CRM, SMTP, mailbox mutations, raw MIME, attachment bytes, and unrelated persistence changes.

### RESTRICTIONS

- No implementation before D1–D4 are approved.
- No schema change unless the subsequent approved plan proves it necessary.
- No external system access or mutation in normal tests.
- No checkpoint advancement outside the approved transaction model.
- No merge based on subject, participants, dates, CRM context, or other non-approved identity evidence.

## 14. Out-of-scope discoveries

- The existing generic source/checkpoint repository lacks email/location-specific methods. This is expected after 3A/3B and must not be expanded until a 3C subphase is approved.
- `IMAPMessageLocation` records current state but has no explicit reconciliation-run/history model. Whether the generic observation table is sufficient depends on D2/D3 and is not decided here.

## 15. Result

**STOPPED FOR DECISION**

Implementation planning is blocked until D1 (duplicate Message-ID/move correlation), D2 (sufficient reconciliation and reactivation evidence), D3 (checkpoint scope/transaction semantics), and D4 (UIDVALIDITY-reset reconciliation window) are approved. No code, schema, dependency, database, credential, mailbox, Calendar, CRM, or other external-system change was made during analysis.
