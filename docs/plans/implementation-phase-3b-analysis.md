# Phase 3B Analysis — Read-only IMAP Adapter

**Status:** READY FOR APPROVAL  
**Date:** 2026-09-22  
**Baseline:** current `codex-work`

## 1. Objective

Define the read-only IMAP adapter that can securely connect using the already-approved configuration and credential boundary, discover folders, select configured folders read-only, search/fetch source material, and return normalized in-memory message data. It must not persist, synchronize, update checkpoints, reconstruct threads, schedule work, call AI, or mutate the mailbox.

## 2. Context and interpretation

Phase 3A now provides:

- `IMAPSettings` containing only non-secret account, host, allowlist, window, body-size, and logical credential-reference settings;
- `CredentialStore` and a minimal `KeyringCredentialStore` read boundary;
- `EmailMessage`, `IMAPMessageLocation`, and attachment-metadata persistence models, which this adapter must not write in 3B;
- declared `IMAPClient` and `keyring` dependencies.

The adapter is an external-data boundary. Folder names, headers, body text, HTML, MIME part metadata, server capability strings, and server errors are untrusted data. They are returned as data only and cannot authorize commands, disclose secrets, or cause mailbox actions.

## 3. Documentation consulted

- `AGENTS.md`
- `docs/plans/implementation-phase-3b-analysis-task.md`
- `docs/plans/implementation-phase-3-imap-analysis.md`
- `docs/plans/implementation-phase-3-imap-decisions.md`
- `docs/plans/implementation-phase-3a-plan.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `app/config.py`
- `app/security/credentials.py`
- `app/persistence/models.py`
- `pyproject.toml`

## 4. Confirmed functional and security requirements

- Use direct `IMAPClient`, not Outlook Desktop internals.
- The only supported authentication source is the configured user plus provider-approved/app password retrieved through `CredentialStore`.
- TLS is mandatory. The adapter does not create a non-TLS fallback.
- The allowlist is configurable and defaults to Inbox/Sent. Existing folders are discovered; no folder is created, renamed, moved, copied, deleted, or subscribed.
- Select folders with read-only selection only.
- Later synchronization uses UIDVALIDITY + UID; this adapter exposes both but does not persist them.
- Prefer `text/plain`; use normalized HTML only when plain text is unavailable. No raw MIME or duplicate raw HTML is returned as retained content.
- The configured 2 MB limit governs returned body content and sets `content_truncated`.
- Attachment information is metadata-only. The adapter must not fetch attachment bodies.
- Credentials, raw source bodies, and attachment bytes are never logged, persisted, placed in audit data, or sent to AI.

## 5. Current project state

There is no `app/integrations` package, IMAP adapter, IMAP fake, MIME parser, scheduler, or synchronization service. The persistence models exist but are not yet used by an ingestion flow. `KeyringCredentialStore` imports `keyring` only within `get_secret`, allowing fake-only tests while the local package is not installed.

This is an appropriate Phase 3B starting point: the adapter can be created independently of persistence and application services.

## 6. Proposed adapter API

Create a new `app/integrations/imap_adapter.py` and a package marker `app/integrations/__init__.py`.

### Constructor and lifecycle

```text
ReadOnlyIMAPAdapter(settings: IMAPSettings,
                    credential_store: CredentialStore,
                    client_factory: Callable[..., IMAPClient] = IMAPClient)
```

The factory is injectable for tests. The adapter is the only component that creates the client. It has explicit `connect()` and `disconnect()` methods and supports a context-manager-style cleanup path.

`connect()`:

1. validates that the configured host/account fields are present (they have already passed `IMAPSettings` validation);
2. obtains the password with `credential_store.get_secret(settings.credential_service, settings.credential_account)`;
3. raises a typed missing-credential error when it returns `None` or an empty string;
4. constructs `IMAPClient(settings.host, port=settings.port, ssl=True)`;
5. authenticates only with `client.login(settings.account, secret)`;
6. discards the local secret reference after the call and never stores/logs it.

`disconnect()` calls only `logout()` when a client was successfully created and then clears the in-memory client reference. It is safe after a partially failed connection.

The adapter makes no retry loop. Connection timeout/retry scheduling belongs to a later synchronization/application service; this preserves a deterministic one-attempt adapter and avoids hidden external activity.

An `imap.invalid` host is not a special mailbox state. It is syntactically non-empty configuration; fake tests use it only to exercise a simulated connection failure. The adapter must surface that failure as a typed connection error without retrying.

### Read-only methods and return types

Use explicit immutable dataclasses, not ORM objects:

- `MailboxFolder(name: str, delimiter: str | None, flags: tuple[str, ...])`
- `SelectedMailbox(name: str, uidvalidity: int | None, capabilities: tuple[str, ...])`
- `AttachmentMetadata(part_index: int, filename: str | None, media_type: str | None, byte_size: int | None, content_id: str | None, disposition: str | None)`
- `FetchedMessage(uid: int, normalized_message_id: str | None, sender_address: str | None, recipient_addresses: tuple[str, ...], subject: str | None, sent_at: datetime | None, in_reply_to: str | None, references_header: str | None, normalized_body: str | None, body_size_bytes: int, content_truncated: bool, attachments: tuple[AttachmentMetadata, ...])`

Methods:

- `list_folders() -> tuple[MailboxFolder, ...]`
- `allowed_folders() -> tuple[MailboxFolder, ...]`
- `select_read_only(folder_name: str) -> SelectedMailbox`
- `search_uids(since: date | None) -> tuple[int, ...]`
- `fetch_messages(uids: Iterable[int]) -> tuple[FetchedMessage, ...]`

Every read method requires an established connection. `select_read_only` rejects a folder not in the configured allowlist before calling the client. It also rejects an allowlisted folder absent from the discovered folder set. Neither condition triggers a server mutation.

## 7. Folder discovery, UID, search, and fetch

### Folder discovery

Use `IMAPClient.list_folders()` and map its flags, delimiter, and folder name into `MailboxFolder`. Normalize protocol bytes to safe decoded strings with replacement for malformed values; retain no raw server response. Exact equality against configured allowlist names determines eligibility. Discovery is read-only.

### Read-only selection and UIDVALIDITY

Use `client.select_folder(folder_name, readonly=True)`. Read `UIDVALIDITY` from the returned select response when present and expose it as `SelectedMailbox.uidvalidity`; absent/malformed values become `None` rather than a fabricated cursor. Capability data is read-only informational data.

### Initial-window search

`search_uids(since)` uses UID search criteria only:

- `since is None`: `ALL`;
- date supplied: `SINCE` followed by the supplied UTC/business-date value in the IMAPClient-supported date form.

The adapter does not calculate the initial window. A later service supplies `today - initial_window_days`, allowing a controlled clock. Returned UIDs are normalized to positive integers; malformed server values raise a protocol error rather than being silently used.

### Fetch fields and attachment safety

Do not fetch `RFC822`, `BODY[]`, or any whole-message/raw MIME field, because they may transfer attachment bytes. The adapter instead reads only:

- `BODY.PEEK[HEADER]` for top-level headers;
- `BODYSTRUCTURE` for MIME part classification and attachment metadata;
- `BODY.PEEK[<text-part>.MIME]` and bounded `BODY.PEEK[<text-part>]` only for the selected text candidate.

For a text part, use a partial body fetch capped at `max_body_bytes + 1`, combined with declared BODYSTRUCTURE octet metadata where available. The returned content is capped at `max_body_bytes`; `content_truncated` is true if the declared size or fetched bytes exceed the limit. `body_size_bytes` is the bounded source-byte count before decoding, capped at the configured limit. No attachment body part is ever requested.

## 8. MIME parsing and normalization

Use only the Python standard library (`email` and `html.parser`); no additional HTML dependency is required.

1. Parse top-level headers using `BytesParser(policy=default)`.
2. Decode encoded headers with standard-library header handling; malformed/unknown charsets use replacement characters and are retained as untrusted text, never executable data.
3. Normalize Message-ID, In-Reply-To, and References as technical header strings without using them to merge threads in 3B.
4. Traverse BODYSTRUCTURE to identify candidate `text/plain` parts, otherwise `text/html` parts, and non-text attachment parts. Preserve only allowed attachment metadata.
5. Reconstruct the selected text-part MIME message from its fetched MIME headers plus bounded payload; decode content-transfer encoding with the `email` parser.
6. For `text/plain`, normalize line endings and whitespace without changing semantic content beyond transport normalization.
7. For HTML fallback, use a small standard-library `HTMLParser` normalizer: ignore script/style content, convert block boundaries to newlines, unescape entities, then normalize whitespace. Do not return raw HTML.

If a message has no usable text part, return `normalized_body=None`, `body_size_bytes=0`, and its attachment metadata. A malformed individual message yields a typed per-message parse error/diagnostic; it does not cause an external retry or an unsafe fallback to full-message fetch.

## 9. Error model

Define typed adapter exceptions with non-sensitive messages only:

- `IMAPAdapterError` base;
- `IMAPCredentialMissingError`;
- `IMAPAuthenticationError`;
- `IMAPConnectionError`;
- `IMAPProtocolError`;
- `IMAPFolderNotAllowedError`;
- `IMAPFolderUnavailableError`;
- `IMAPMessageParseError`.

Map IMAPClient/client-factory transport and authentication exceptions into these types without embedding host credentials, password text, raw response bodies, or message bodies. The caller is responsible for later degraded/reconnect state, retries, persistence, and audit events. 3B only guarantees cleanup and an error that a later service can classify.

## 10. Dependencies

- Uses the already-declared `IMAPClient`; no additional package is proposed.
- Uses the existing `CredentialStore` protocol and `IMAPSettings`.
- Uses standard-library `email`, `html.parser`, dataclasses, datetime, and typing.
- Has no dependency on SQLAlchemy, Alembic, repositories, FastAPI, routes, scheduler, AI, SMTP, CRM, Calendar, or real keyring data.

## 11. Test matrix

All tests use an injected fake client factory and fake CredentialStore; they must not import a real credential, open a socket, or instantiate an IMAP connection.

| Area | Required fake test cases |
| --- | --- |
| Connection | TLS argument is true; configured host/port/account used; login receives fake secret; missing secret blocks client creation; simulated authentication/connection failures map to typed errors; logout cleanup occurs. |
| Folders | list-folder tuple mapping; allowlist intersection; non-allowlisted and missing configured folder are rejected before select; selection is `readonly=True`. |
| UID/search | UIDVALIDITY extraction; `ALL` vs `SINCE` criteria; malformed UID/UIDVALIDITY handling; no checkpoint/persistence call. |
| Fetch | only header/BODYSTRUCTURE/bounded text-part fetch keys; never whole-message fields or attachment part bodies; positive UID validation. |
| MIME | encoded/malformed headers, Message-ID/In-Reply-To/References parsing, recipients, plain preferred over HTML, HTML fallback, unknown charset replacement, message without text body. |
| Limits | below/equal/above 2 MB controlled limit; `content_truncated`; no returned body beyond configured limit. |
| Attachments | metadata mapping, nested parts, no byte payload returned or requested. |
| Security | secret absent from exception strings; no logger calls carrying secret/body; malicious-looking body content remains returned data only; no IMAP mutation method is exposed. |

## 12. Proposed subphases

1. **3B1 — connection and folder boundary:** typed contracts, fake-injected TLS/authentication lifecycle, discovery, allowlist, read-only selection, and error cleanup.
2. **3B2 — read-only message retrieval and normalization:** UID search, header/BODYSTRUCTURE/text-part reads, MIME normalization, truncation, attachment metadata, and fake contract tests.

Both subphases remain adapter-only. Persistence, source creation, checkpoints, threading, and scheduling begin only in a later explicitly approved phase.

## 13. Scope Lock for the future implementation

### IN SCOPE

- `app/integrations/__init__.py` (new)
- `app/integrations/imap_adapter.py` (new)
- `test/test_imap_adapter.py` (new)

### OUT OF SCOPE

- `app/config.py`, `app/security/credentials.py`, `pyproject.toml`, all persistence models/migrations/repositories, `main.py`, routes/UI, scheduler, services, audit implementation, and existing tests except where an existing test is demonstrably required by a new public adapter contract;
- all IMAP server access, real keyring access, mailbox mutations, SMTP, message moves, drafts, sends, threading, synchronization, source/checkpoint persistence, AI, CRM, Calendar, raw MIME retention, and attachment bytes.

### RESTRICTIONS

- No new dependency, no external/network call, and no real account or credential access.
- The adapter exports no mutating IMAP API and must only invoke read-only client methods.
- No full-message/raw MIME fetch and no attachment-body fetch.
- No retry loop, scheduler hook, persistence action, audit write, or business/CRM interpretation.

## 14. Ambiguities and decisions pending

None. The approved decisions resolve authentication, cursor semantics, identity, content retention, allowlist, deletion/move semantics, and MIME/body-limit policy. Standard-library HTML normalization avoids a new dependency and remains within the approved plain-first/HTML-fallback requirement.

## 15. Out-of-scope discoveries

- `IMAPClient` and `keyring` are declared but not locally installed. A future implementation environment must install the declared dependencies before running adapter tests; this analysis neither installs nor invokes them.
- The current `KeyringCredentialStore` has intentionally no error normalization. Mapping credential-backend faults into adapter errors belongs to 3B’s adapter boundary, not a change to the credential store.

## 16. Result

**READY FOR APPROVAL**

The adapter can be implemented in the two bounded subphases above with fake-only tests and without extending the approved model, credential contract, or external permissions.
