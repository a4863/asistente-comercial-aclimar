# Phase 3 IMAP Analysis — Outlook Integration

**Status:** STOPPED FOR DECISION  
**Date:** 2026-09-22  
**Baseline:** `codex-work` at the Phase 3 analysis task

## 1. Objective

Assess the first mailbox integration for the one configured ACLIMAR corporate account through direct, secure IMAP. The intended capability is read-only discovery and incremental synchronization; it must not depend on Outlook Desktop, send mail, move messages, create drafts, download attachments, call AI, or connect to the real account during this task.

## 2. Context and interpretation

The assistant is a local, single-user Windows application. It owns local ingestion, source provenance, synchronization state, and audit history. The mailbox remains the external source of message state; Outlook Desktop may continue to use it independently.

This analysis concerns only a future IMAP read/synchronization workflow. External mutations are excluded. Any message content, headers, MIME parts, folder names, and server error text are untrusted data, never instructions.

## 3. Documentation consulted

- `AGENTS.md`
- `docs/plans/implementation-phase-3-imap-analysis-task.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `app/config.py`
- `app/main.py`
- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `pyproject.toml`
- Current persistence and configuration tests.

## 4. Current project state

### Existing foundation

- The approved architecture names `IMAPClient` as the IMAP adapter library and Python's `email` package for MIME/header parsing.
- Non-secret settings are TOML-backed, but `Settings` currently contains only host, port, and database URL.
- Dependencies currently do not include `IMAPClient`, `keyring`, or a scheduler package.
- Persistence already supplies `SourceRecord`, `SourceObservation`, `SynchronizationCheckpoint`, `IdempotencyIdentity`, `Conversation`, `ConversationMembership`, and `ConfigurationReference`.
- `SourceRepository` has source identity, observation, checkpoint, and idempotency helpers. `ProvenanceRepository` has conversation and membership helpers.
- There is no IMAP adapter, mailbox configuration, credential-store adapter, synchronization service, email-message representation, or IMAP fake/contract test.

### Important model gap

`docs/data-model.md` defines an `EmailMessage` representation linked to `SourceRecord`, with sender/recipients, subject, timestamps, Message-ID, In-Reply-To, References, folder, body/source reference, and attachment metadata. The current physical model and migrations do not contain an `EmailMessage` table or equivalent representation. `SourceRecord` itself has neither message headers nor a body/source-reference field.

Therefore the approved conceptual model is not yet sufficient to choose the physical persistence mapping required for Phase 3 without a separate approved data-model/migration decision.

## 5. Required future data flow

The documentation supports this boundary, subject to the pending decisions below:

```text
Configured mailbox + credential reference
        -> credential-store adapter
        -> read-only IMAP adapter
        -> synchronization service
        -> source / observation / email representation repositories
        -> thread reconstruction service
        -> audit + integration status
```

The synchronization service would own transactions, checkpoint advancement only after successful persistence, idempotency use, and degraded integration state. The IMAP adapter would be read-only and would not know application/domain rules. Thread reconstruction would consume retained technical headers and would create no conversation membership where evidence is insufficient.

## 6. Confirmed requirements

- Exactly one initially configured corporate mailbox; the supplied account identity is `alexllopez@aclimar.com`.
- Direct IMAP is required; Outlook Desktop internals are not an integration boundary.
- TLS is mandatory; credentials must be held by Windows Credential Manager through `keyring`, never in code, Git, TOML, SQLite plaintext, logs, audit payloads, or browser responses.
- The adapter discovers existing folders and never creates them.
- Initial ingestion uses a configurable historical window, defaulting to 30 days; routine synchronization is incremental and supports catch-up after downtime.
- Message identity, observations, checkpoints, idempotency, provenance, and auditability are required.
- Threading priority is Message-ID, In-Reply-To, then References. Normalized subject is only secondary evidence; participant, date, or CRM context alone cannot merge threads.
- Source changes and source deletion must be retained as local historical state rather than silently removed.
- Attachments are metadata-only in the MVP; attachment bytes are not automatically downloaded or persisted.
- This phase has no SMTP, move, draft creation, send, external action execution, real mailbox access, or AI transmission.

## 7. Dependencies and boundaries

### Internal dependencies

- `ConfigurationReference` for non-secret logical mailbox/configuration identity.
- `SourceRecord`, `SourceObservation`, `SynchronizationCheckpoint`, and `IdempotencyIdentity` for synchronized source state.
- `Conversation` and `ConversationMembership` for evidence-based thread reconstruction.
- `AuditEvent` for synchronization outcomes and degraded-state transitions.
- Local TOML settings and the approved localhost-only application boundary.

### External dependencies

- `IMAPClient`, already selected by approved architecture but not yet declared in the project dependencies.
- Python `email`, already part of the standard library.
- `keyring` backed by Windows Credential Manager, selected by approved security/architecture but not yet declared.
- A future Outlook/Exchange IMAP endpoint, which must not be contacted until a later approved implementation/configuration task.

No new dependency is authorized by this analysis.

## 8. Ambiguities and decisions required

The Phase 3 task explicitly requires a stop if authentication, UID/UIDVALIDITY, body retention, threading, or source deletion admits multiple reasonable implementations. The following decisions block an implementation plan.

### D1 — Outlook authentication method

The documents mandate `keyring`/Windows Credential Manager for storage but do not specify the authentication material or Outlook/Exchange authorization flow.

- **Option A:** OAuth 2.0 / XOAUTH2 token flow, with the token or refresh material held only in Credential Manager.
- **Option B:** IMAP username plus provider-approved app password, also held only in Credential Manager.

These differ in setup, expiry/reconnect behavior, server capability requirements, and test contracts. The user must confirm the supported corporate authentication method before code or configuration design.

### D2 — Incremental cursor and reset semantics

The requirements require incremental synchronization but do not approve one IMAP capability strategy.

- **Option A:** Persist `UIDVALIDITY` plus the highest processed UID per account/folder; if UIDVALIDITY changes, treat the folder as a new UID namespace and reconcile through the configured historical window.
- **Option B:** Require/use CONDSTORE/MODSEQ as the primary change cursor, with a defined fallback when the server does not support it.

The choice determines checkpoint shape, safe replay behavior, and handling of changed/deleted messages. It cannot be made from the current documentation.

### D3 — Source identity across folders and moves

A message can appear in multiple folders or change folder outside the assistant. The documents require stable identity and source deletion/move detection but do not state whether the canonical source identity is:

- a mailbox-global Message-ID plus account scope, with a separate per-folder location observation; or
- a per-folder UID/UIDVALIDITY identity, with a later cross-folder reconciliation policy; or
- a combination of both, including rules for missing/duplicate Message-ID values.

This affects uniqueness, observations, move detection, and idempotency. The decision must also define how messages without a Message-ID are treated.

### D4 — Physical email representation and content retention

The conceptual `EmailMessage` entity is absent from the current physical model. The documents require enough body content for later analysis and preservation, but do not specify whether the assistant persists:

- normalized plain text plus MIME/header metadata;
- a local retained raw-message reference plus a normalized extract; or
- metadata and a separate local source-content store/reference.

The choice affects the schema/migration, retention/redaction behavior, safe logging, HTML processing, size limits, and evidence references. A data-model decision and an approved migration scope are required before implementation.

### D5 — Folder selection and initial synchronization coverage

The assistant must discover existing folders and the initial sync window defaults to 30 days, but it is not defined whether first-read covers only Inbox, all selectable existing folders, or a configured allowlist. This determines duplicate handling, sync load, and which messages can later be proposed for filing.

### D6 — Deletion and move detection meaning

The requirements require detection of deleted/moved messages at source, but do not define the observation semantics for a message that disappears from one folder while remaining accessible in another folder. The decision must distinguish a folder-location change from actual source deletion without assuming Outlook-specific server behavior.

### D7 — HTML/plain-text normalization and size limits

MIME parsing and later analysis require a deterministic choice when both text/plain and text/html exist, when HTML is malformed, and when bodies exceed a size threshold. No approved limits or canonical retained representation are defined.

## 9. Risks

| Risk | Impact | Required mitigation or decision |
| --- | --- | --- |
| Unsupported or misconfigured authentication | No safe connection or repeated failed logins | Resolve D1; isolate credential failures and expose reconnect state without secrets. |
| UID namespace reset or folder-local identity collision | Duplicate ingestion or lost change detection | Resolve D2 and D3 before checkpoint design. |
| Incorrect cross-folder handling | False deletion/move records or missed messages | Resolve D3, D5, and D6; preserve observations. |
| Ambiguous thread merge | Incorrect commercial context and provenance | Use technical headers only; retain ungrouped messages when evidence is insufficient. |
| Sensitive body persistence/logging | Commercial data exposure | Resolve D4/D7; preserve only approved local content and never log bodies. |
| Attachment processing | Unapproved storage or malware/sensitive data risk | Store no bytes; decide metadata policy as part of D4/D7. |
| Embedded prompt injection | Unauthorized behavior or leakage | Treat all mailbox data as untrusted content; no AI call in Phase 3. |
| Checkpoint advancement before durable persistence | Lost messages after failure | Advance only after transactional persistence; test recovery. |

## 10. Test matrix for a later approved implementation

- IMAP adapter contract tests using a fake/mock only: TLS configuration, authentication failure, folder discovery, and no mutating IMAP commands.
- Controlled MIME fixtures: text/plain, text/html, multipart alternatives, malformed headers, absent/duplicate Message-ID, In-Reply-To, References, and attachment metadata without bytes.
- Synchronization tests: initial configurable window, incremental replay, duplicate UID, cursor recovery, restart catch-up, and checkpoint non-advancement on persistence failure.
- Identity and observation tests: stable identity, changed message observations, folder disappearance, actual deletion, and the approved move semantics.
- Thread reconstruction tests: direct reply/reference chains, insufficient evidence, and subject-only ambiguity remaining separate.
- Security tests: no secrets in TOML/SQLite/logs/audit/browser output; fake keyring only; untrusted body content remains data; no remote AI call.
- Regression tests: degraded IMAP state does not prevent local review of stored data; no attachment bytes are stored; no move/draft/send command is available.

All tests must use isolated SQLite, fake keyring, controlled clock/fakes, and synthetic messages. They must never use the real mailbox or production credentials.

## 11. Proposed subphases after decisions

1. **3A — approved data/configuration foundation:** resolve D1–D7, add the approved email representation and migration, non-secret settings, and credential-reference boundary.
2. **3B — read-only IMAP adapter:** add fake-backed secure connection, folder discovery, MIME parsing, and no-mutation contract tests.
3. **3C — synchronization and recovery:** implement the approved cursor, identity, observation, checkpoint, idempotency, deletion/move semantics, and degraded-state behavior.
4. **3D — threading and application integration:** evidence-based conversation reconstruction and local synchronization orchestration. No move/draft/send execution.

Each subphase requires its own approved plan and Scope Lock.

## 12. Scope Lock

### Current analysis scope

**IN SCOPE**

- Read-only inspection and this analysis artefact only.

**OUT OF SCOPE**

- IMAP connection, mailbox access, credential retrieval, code, dependencies, schema/migrations, configuration changes, scheduler, UI, AI, SMTP, moves, drafts, sends, and `main`.

**RESTRICTIONS**

- No real-account connection or credential handling.
- No selection of an authentication, cursor, identity, retention, or deletion strategy without an explicit decision.

### Future implementation scope

No implementation Scope Lock can be approved until D1–D7 are resolved. Candidate files must be selected only in the subsequent approved plan; they cannot be inferred as authorized now.

## 13. Out-of-scope discoveries

- The current project dependencies omit architecture-selected `IMAPClient` and `keyring`. Adding them is outside this analysis and requires an approved implementation plan.
- The existing settings loader has no mailbox or integration settings. Designing their TOML shape is blocked by D1, D2, D5, and D7.
- The physical persistence model has no `EmailMessage` representation despite the approved conceptual data model. Resolving it requires a data-model/migration scope outside this analysis.

## 14. Result

**STOPPED FOR DECISION**

Implementation cannot proceed safely until decisions D1 through D7 are approved. No implementation code, real mailbox connection, credential access, dependency change, database operation, or external-system mutation was performed.
