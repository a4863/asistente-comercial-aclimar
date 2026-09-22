# Plan — Phase 3A Email Data and Credential Foundation

**Status:** READY FOR APPROVAL  
**Date:** 2026-09-22  
**Baseline:** current `codex-work`  
**Prerequisites:** approved `implementation-phase-3-imap-decisions.md`; Phase 2A/2B persistence foundation

## 1. Objective

Create only the local data, non-secret configuration, and credential-store foundation required before any IMAP synchronization. Phase 3A introduces no IMAP connection, mailbox operation, scheduler, thread reconstruction, UI, AI processing, SMTP, move, draft, or send behavior.

The implementation will make the approved EmailMessage representation persistent, represent IMAP locations separately from a logical email, retain only normalized local content and attachment metadata, declare the approved packages, and expose a narrow credential boundary backed by Windows Credential Manager through `keyring`.

## 2. Approved decisions applied

This plan applies, without reopening, the approved Phase 3 IMAP decisions:

- Authentication is the configured mailbox user plus a provider-approved password/app password, stored only via `keyring` / Windows Credential Manager.
- Incremental synchronization will later use UIDVALIDITY plus UID, with a checkpoint per account/folder.
- A logical email identity and its IMAP locations are separate. A normalized Message-ID is a logical identity when present; no Message-ID authorizes no aggressive merge.
- Email content persists as normalized text, not raw MIME. The maximum processed body is 2 MB; `content_truncated` records truncation. Attachments are metadata-only.
- Folder selection will later be a configurable allowlist, defaulting to Inbox and Sent.
- A move is not a deletion. Location history and reconciliation are deferred to synchronization.
- MIME selection will later prefer `text/plain`, then normalized HTML fallback.

## 3. Current state

The application already has local SQLite/SQLAlchemy/Alembic persistence; source records, source observations, checkpoints, idempotency identities, conversations, configuration references, and audit records exist.

`docs/data-model.md` requires an EmailMessage representation, but no physical email-message, IMAP-location, or attachment-metadata model exists. Existing configuration has only server/database settings. The declared dependencies do not yet include `IMAPClient` or `keyring`.

## 4. Exact persistent model

Phase 3A creates exactly three new tables/models. It does not change existing 2A/2B tables or repositories.

### 4.1 `email_message`

One `EmailMessage` is linked to exactly one `SourceRecord`; each email representation has one source record.

| Field | Shape | Rule |
| --- | --- | --- |
| `id`, `created_at` | existing common pattern | integer PK and UTC creation timestamp |
| `source_record_id` | FK to `source_record.id`, unique, required | one source record per physical email representation |
| `normalized_message_id` | nullable string | normalized technical Message-ID when available; deliberately not globally unique |
| `sender_address` | nullable string | source header value, not an identity resolution |
| `recipient_addresses` | nullable text | canonical serialized list of header recipient addresses; no CRM resolution |
| `subject` | nullable string | source header text |
| `sent_at` | nullable UTC datetime | parsed message date when available |
| `received_at` | nullable UTC datetime | server/received timestamp when available |
| `in_reply_to` | nullable string | normalized technical header reference |
| `references_header` | nullable text | normalized ordered References values |
| `normalized_body` | nullable text | canonical plain-text content only; never raw MIME/HTML duplicate |
| `body_size_bytes` | nullable integer | size of the supplied/processed text representation for observability and the 2 MB guard |
| `content_truncated` | required boolean, default false | true whenever the configured 2 MB maximum limits retained body content |
| `provenance` | required string | retained source/provenance label |

`EmailMessage` stores source data only. It does not create conversations, facts, inferences, proposals, or CRM associations. It will not impose a unique Message-ID because the approved identity rule permits duplicates and absent IDs without unsafe merging.

### 4.2 `imap_message_location`

This table represents a technical occurrence/location, separate from the logical email representation.

| Field | Shape | Rule |
| --- | --- | --- |
| `id`, `created_at` | existing common pattern | integer PK and UTC creation timestamp |
| `email_message_id` | FK to `email_message.id`, required | links location to a retained email representation |
| `account_scope` | required string | non-secret configured mailbox scope, not a password |
| `folder_name` | required string | discovered/configured IMAP folder name |
| `uidvalidity` | required unsigned/integer-compatible value | IMAP UID namespace identifier |
| `uid` | required unsigned/integer-compatible value | message UID within the location namespace |
| `location_state` | required string, default `active` | only `active` and `unavailable` are allowed; later synchronization determines transitions |
| `last_observed_at` | required UTC datetime | latest local observation time |
| `provenance` | required string | synchronization/source provenance |

Physical constraints:

- unique `(account_scope, folder_name, uidvalidity, uid)`;
- index for `(account_scope, folder_name, uidvalidity, uid)` lookup;
- check constraint restricting `location_state` to `active` / `unavailable`.

No unique constraint on `email_message_id` is used: a logical message may be observed in more than one synchronized folder. Phase 3A does not implement the later reconciliation that creates/updates these records.

### 4.3 `email_attachment_metadata`

This table contains no attachment bytes and no raw MIME part.

| Field | Shape | Rule |
| --- | --- | --- |
| `id`, `created_at` | existing common pattern | integer PK and UTC creation timestamp |
| `email_message_id` | FK to `email_message.id`, required | attachment metadata belongs to one retained email representation |
| `part_index` | required integer | deterministic MIME-part position, non-negative |
| `filename` | nullable string | available source metadata only |
| `media_type` | nullable string | available MIME media type only |
| `byte_size` | nullable integer | available declared size, non-negative when known |
| `content_id` | nullable string | source metadata only |
| `disposition` | nullable string | source metadata only |
| `provenance` | required string | synchronization/source provenance |

Physical constraints:

- unique `(email_message_id, part_index)`;
- checks for non-negative `part_index` and known `byte_size`.

## 5. SourceRecord and observation mapping

The later ingestion service will create `SourceRecord` rows with `source_type="email_message"`, `manual_entry=false`, and an IMAP account source-system scope. The exact stable external identifier will follow the approved logical-identity/location strategy:

- normalized Message-ID when present, scoped to the configured account; or
- an IMAP occurrence identity derived from account/folder/UIDVALIDITY/UID when Message-ID is absent.

`SourceObservation` remains the history for synchronization observations and changed external state. `IMAPMessageLocation` is not a replacement for `SourceObservation`; it is the source-specific technical representation needed for later move-versus-deletion reconciliation.

No repository or synchronization method is added in 3A because no mailbox data is read yet.

## 6. Migration 0004

Create an explicit Alembic revision:

```text
revision: 0004
down_revision: 0003
```

`upgrade()` creates `email_message`, `imap_message_location`, and `email_attachment_metadata`, their foreign keys, checks, unique constraints, and the location lookup index. It must use explicit Alembic operations only and must not import SQLAlchemy application metadata.

`downgrade()` drops the three 0004 tables/indexes in reverse dependency order only:

1. `email_attachment_metadata`;
2. `imap_message_location` index and table;
3. `email_message`.

It must leave every 0001–0003 object unchanged and support isolated `0003 -> 0004 -> 0003 -> 0004` testing.

## 7. Non-secret configuration

Extend `Settings`/`load_settings` with a nested immutable IMAP configuration object. It contains only:

- `host`;
- `port` (default `993`);
- configured mailbox user/account identity;
- `account_scope` for source/checkpoint/location scoping;
- `folder_allowlist` (default `("INBOX", "Sent")`);
- `initial_window_days` (default `30`);
- `max_body_bytes` (fixed default `2 * 1024 * 1024`);
- logical credential service name and account key used by the credential store.

TOML validation rejects an empty host, non-positive port, empty configured account/scope, duplicate/empty allowlist folders, negative initial window, and a non-positive body limit. It continues to reject non-loopback server binding.

The TOML schema does not contain an IMAP password, app password, token, secret, raw credential reference value, or anything copied from Credential Manager.

## 8. Credential boundary

Create `app/security/credentials.py` with only a minimal adapter boundary:

```text
CredentialStore.get_secret(service: str, account: str) -> str | None
KeyringCredentialStore
```

`KeyringCredentialStore` delegates retrieval to `keyring.get_password(service, account)`. It does not log, persist, display, cache, transmit, or return a secret through any application response. No setter, credential bootstrap UI, IMAP authentication, or real Credential Manager access is part of 3A.

Tests use a fake credential store / mocked `keyring` API. They never call the real Windows Credential Manager.

## 9. Dependency declaration

Add the architecture-approved runtime dependencies to `pyproject.toml` only:

- `IMAPClient` for the later adapter;
- `keyring` for the approved credential boundary.

Phase 3A may import only `keyring` at the credential boundary. It creates no `IMAPClient` client and performs no network activity. Installing packages is an implementation-environment action, not part of this planning task.

## 10. Files and Scope Lock

### IN SCOPE

- `pyproject.toml`
- `app/config.py`
- `app/security/credentials.py` (new)
- `app/persistence/models.py`
- `alembic/versions/0004_phase_3a_email_data_foundation.py` (new)
- `test/test_config.py`
- `test/test_credentials.py` (new)
- `test/test_persistence_models.py`
- `test/test_migrations.py`

### OUT OF SCOPE

- `app/main.py`, routes, templates, UI, scheduler, repositories, application services, and audit API changes;
- IMAP adapter implementation, any socket/network connection, mailbox listing, authentication attempt, synchronization, checkpoints writes, message parsing, threading, source ingestion, move/delete detection, or catch-up;
- real credential storage/retrieval, account setup, SMTP, drafts, moves, sends, Calendar, CRM, AI, attachments bytes, raw MIME, and external actions;
- changes to 0001–0003, Phase 2A/2B records, `main`, or approved documentation.

### RESTRICTIONS

- Do not use real credentials, real keyring data, real mailbox data, or an IMAP connection.
- Do not store secrets in configuration, models, migrations, database rows, logs, audit events, exception text, or tests.
- Do not add a generic configuration store, a credential setter, a scheduler, an IMAP client instance, or repository methods beyond the listed model/configuration/credential boundary.
- Do not change the physical schema beyond the three named tables and their defined constraints.

## 11. Implementation order

1. Declare `IMAPClient` and `keyring` in the project dependencies; do not install or use the IMAP library in code.
2. Add the three SQLAlchemy models and physical integrity constraints.
3. Create explicit reversible migration `0004` matching only those models.
4. Add the nested non-secret IMAP configuration parsing and validation.
5. Add the narrow credential-store protocol/adapter without invoking it from startup or routes.
6. Add isolated model, migration, configuration, and mocked credential-boundary tests.
7. Execute the focused tests, then the full suite, and review that only Scope Lock files changed.

## 12. Test plan

### Model and migration tests

- EmailMessage requires exactly one SourceRecord and permits absent/duplicate normalized Message-ID values.
- Location uniqueness rejects duplicate account/folder/UIDVALIDITY/UID and permits multiple locations for one EmailMessage.
- Attachment metadata rejects duplicate part indexes and negative known sizes/part indexes.
- No table contains raw MIME or attachment bytes.
- Empty isolated database upgrades to 0004; `0003 -> 0004 -> 0003 -> 0004` is reversible and leaves earlier tables unchanged.

### Configuration tests

- Defaults are port 993, Inbox/Sent allowlist, 30-day window, and 2 MB body limit.
- TOML accepts valid non-secret IMAP configuration.
- Invalid host/port/account/scope/folder allowlist/window/body-limit values fail locally.
- A TOML fixture containing password-like IMAP keys is rejected rather than silently accepted.
- Existing localhost-only server validation remains green.

### Credential boundary tests

- Keyring adapter calls the mocked `get_password` with only configured logical service/account values.
- Missing credential returns `None` for a later reconnect/configuration state; no exception/log path reveals a supplied fake secret.
- No real keyring, mailbox, or network operation is used.

### Commands for the future implementation task

```text
python -m pytest test/test_config.py test/test_credentials.py test/test_persistence_models.py test/test_migrations.py
python -m pytest
```

## 13. Risks and STOP conditions

Stop immediately if implementation would require:

- a new authentication flow or secret format beyond the approved user/app-password decision;
- access to a real account, Windows Credential Manager, network, or mailbox;
- a schema change beyond the three named tables;
- repository, service, scheduler, UI, or IMAP adapter behavior;
- raw MIME, attachment bytes, or secret persistence;
- a change to 0001–0003 or `main`;
- a dependency beyond `IMAPClient` and `keyring`.

The main implementation risks are schema drift from 0004, accidental secret logging, accepting secret TOML keys, and inadvertently introducing an IMAP call while establishing the credential boundary. The Scope Lock and fake-only tests address these risks.

## 14. Definition of Done

- Only Scope Lock files are modified.
- The three approved email foundation tables and their constraints are represented in SQLAlchemy and explicit reversible migration 0004.
- IMAP configuration remains non-secret and validates locally.
- The credential boundary uses `keyring` only through a fake-tested read interface and is not called by startup/UI.
- No network, real keyring, mailbox, SMTP, AI, Calendar, CRM, or external mutation occurs.
- Focused and full pytest suites are green.
- The diff confirms no changes to `main`, 0001–0003, or out-of-scope components.
