# Plan — Phase 3B Read-only IMAP Adapter

**Status:** READY FOR APPROVAL  
**Date:** 2026-09-22  
**Baseline:** current `codex-work`  
**Analysis:** `docs/plans/implementation-phase-3b-analysis.md`

## 1. Objective

Implement a fake-testable, read-only IMAP adapter in two bounded steps:

1. **3B1:** TLS connection, credential retrieval, folder discovery/allowlist, read-only selection, typed errors, and cleanup.
2. **3B2:** UID search, selective MIME-part fetch, message normalization, 2 MB guard, and attachment metadata.

The adapter returns in-memory data only. It does not persist, synchronize, schedule, reconstruct threads, call AI, or mutate any external mailbox state.

## 2. Existing approved contracts

- `IMAPClient` is the approved client library; TLS is mandatory.
- `IMAPSettings` supplies host, port, account, configured allowlist, initial window, maximum body size, and logical credential references. `imap.invalid` is a safe unprepared default, not a connection target with special behavior.
- `CredentialStore.get_secret(service, account)` is the only secret access boundary. A missing/empty result stops before client construction or login.
- No retries exist inside the adapter; a later service owns retry/degraded-state policy.
- Folder selection uses the configured allowlist and `readonly=True`.
- UIDVALIDITY is exposed only; no checkpoint or persistence is performed.
- Search is `ALL` or `SINCE`; full-message fetches (`RFC822`, `BODY[]`) and attachment-body fetches are prohibited.
- Plain text is preferred; HTML fallback uses standard-library parsing. Max body size is `max_body_bytes`; attachment metadata contains no bytes.

## 3. Exact public contracts

`app/integrations/imap_adapter.py` will define only immutable dataclasses, typed exceptions, and `ReadOnlyIMAPAdapter`.

### Immutable return types

```text
MailboxFolder(name, delimiter, flags)
SelectedMailbox(name, uidvalidity, capabilities)
AttachmentMetadata(part_index, filename, media_type, byte_size, content_id, disposition)
FetchedMessage(uid, normalized_message_id, sender_address,
               recipient_addresses, subject, sent_at, in_reply_to,
               references_header, normalized_body, body_size_bytes,
               content_truncated, attachments)
```

`recipient_addresses`, `flags`, `capabilities`, and `attachments` are tuples. None of these types is an ORM model or has persistence behavior.

### Exceptions

```text
IMAPAdapterError
├── IMAPCredentialMissingError
├── IMAPAuthenticationError
├── IMAPConnectionError
├── IMAPProtocolError
├── IMAPFolderNotAllowedError
├── IMAPFolderUnavailableError
└── IMAPMessageParseError
```

Exception messages are fixed/safe descriptions. They exclude secrets, raw server responses, raw headers, bodies, and attachment data.

### Adapter methods

```text
ReadOnlyIMAPAdapter(settings, credential_store, client_factory=IMAPClient)
connect() -> None
disconnect() -> None
__enter__() -> ReadOnlyIMAPAdapter
__exit__(...) -> None
list_folders() -> tuple[MailboxFolder, ...]
allowed_folders() -> tuple[MailboxFolder, ...]
select_read_only(folder_name: str) -> SelectedMailbox
search_uids(since: date | None) -> tuple[int, ...]
fetch_messages(uids: Iterable[int]) -> tuple[FetchedMessage, ...]
```

Methods requiring a connection raise `IMAPConnectionError` when no successful connection exists. The adapter exposes no methods for append, copy, move, delete, rename, create folder, draft, SMTP, or persistence.

## 4. 3B1 implementation plan

### 4.1 Files

- Create `app/integrations/__init__.py`.
- Create `app/integrations/imap_adapter.py` with 3B1 types/methods.
- Create `test/test_imap_adapter.py` with fake-only connection/folder tests.

### 4.2 Connection and authentication

1. Resolve the secret only by calling `credential_store.get_secret(settings.credential_service, settings.credential_account)`.
2. If it is missing or empty, raise `IMAPCredentialMissingError`; do not invoke the factory or client login.
3. Construct the client as `client_factory(settings.host, port=settings.port, ssl=True)`.
4. Call `client.login(settings.account, secret)` exactly once after construction.
5. Translate authentication failures to `IMAPAuthenticationError`; transport/factory failures to `IMAPConnectionError`; unexpected protocol failures to `IMAPProtocolError`.
6. Clear the in-memory client reference on connection failure. `disconnect()` logs out only an initialized client, suppresses cleanup-only logout errors, and clears the reference in all cases.
7. Context-manager exit delegates to safe `disconnect()`.

No retry, network probing, or special connection to `imap.invalid` is added. Fakes model any connection failure.

### 4.3 Folder operations

1. Map `client.list_folders()` protocol tuples into `MailboxFolder`, decoding protocol bytes with replacement and retaining no raw protocol structure.
2. `allowed_folders()` returns only exact-name matches in `settings.folder_allowlist` that discovery reported.
3. `select_read_only()` first rejects names outside the allowlist with `IMAPFolderNotAllowedError`; then rejects absent discovered names with `IMAPFolderUnavailableError`.
4. Call `client.select_folder(name, readonly=True)` only after both checks.
5. Extract a positive integer UIDVALIDITY when available; use `None` for absent/malformed values. Convert safe capability strings to an immutable tuple.

### 4.4 3B1 test matrix

- fake factory receives host, port, and `ssl=True`;
- fake credential store supplies a fake secret only to fake `login`;
- missing/empty secret creates no fake client and performs no login;
- authentication, construction, and protocol failures map to the approved typed errors without secret text;
- disconnect/context manager clears a connected or partially connected client and performs no external retry;
- folder flags/delimiter/name mapping; exact allowlist intersection; rejected non-allowlisted/missing folders; `readonly=True`; UIDVALIDITY/capability extraction.

## 5. 3B2 implementation plan

### 5.1 UID search

1. Require an established client and a successfully selected read-only mailbox.
2. For `since=None`, issue an IMAP UID search using `ALL`.
3. For a supplied date, issue `SINCE` with that date; the adapter does not calculate the initial window.
4. Normalize only positive integer UIDs; malformed server UID values raise `IMAPProtocolError`.

### 5.2 Selective fetch contract

For requested positive UIDs only, use fields limited to:

```text
BODY.PEEK[HEADER]
BODYSTRUCTURE
BODY.PEEK[<selected-text-part>.MIME]
BODY.PEEK[<selected-text-part>]<0.max_body_bytes+1>
```

The implementation must not request `RFC822`, `BODY[]`, `BODY.PEEK[]`, a whole-message equivalent, or any attachment part body. BODYSTRUCTURE is traversed before a text-part body is fetched.

### 5.3 MIME normalization

1. Parse top-level headers with `email.parser.BytesParser(policy=default)`.
2. Decode header values/charsets with replacement for malformed values.
3. Return normalized Message-ID, In-Reply-To, References, sender, recipients, subject, and parsed date only as source metadata.
4. Traverse BODYSTRUCTURE recursively to identify text candidates and attachment metadata.
5. Prefer a `text/plain` candidate; use `text/html` only when plain is absent.
6. Reconstruct selected-part MIME headers plus the bounded payload for standard-library content-transfer/charset decoding.
7. Normalize plain-text line breaks/whitespace. For HTML fallback, use a small `HTMLParser` normalizer that ignores script/style, creates block newlines, unescapes entities, and returns normalized text only.
8. If no usable text part exists, return `normalized_body=None` and `body_size_bytes=0` with metadata only.
9. An individual malformed message raises `IMAPMessageParseError`; it never triggers a whole-message fallback.

### 5.4 Body-size and attachment rules

- Fetch at most `max_body_bytes + 1` bytes of the selected text part.
- Return at most `max_body_bytes` bytes’ decoded/normalized source representation.
- `content_truncated` is true when declared part size or fetched content exceeds the limit.
- `body_size_bytes` is the retained bounded source-byte count.
- Attachment metadata includes only part index, filename, media type, declared byte size, content ID, and disposition. It never includes bytes or raw MIME.

### 5.5 3B2 test matrix

- `ALL` and `SINCE` criteria, positive UID validation, and no checkpoint/repository call;
- fetch-key audit proving no whole-message/attachment-body request;
- headers with encoded text, malformed headers, absent Message-ID, In-Reply-To, and References;
- plain-over-HTML priority, HTML-only fallback, unknown charset replacement, no-text message;
- body below/equal/above configured cap with correct content truncation;
- nested attachment metadata mapping with no bytes in return types/fake fetches;
- malicious-looking text/HTML remains inert data; parse/connection exceptions contain no fake secret or body.

## 6. Error mapping

| Source condition | Adapter result | Cleanup |
| --- | --- | --- |
| Missing/empty credential | `IMAPCredentialMissingError` | No factory/client/login call |
| Client factory/transport failure | `IMAPConnectionError` | Clear client reference |
| Login authentication rejection | `IMAPAuthenticationError` | Logout if initialized; clear reference |
| Invalid client response/UID/BODYSTRUCTURE | `IMAPProtocolError` | Keep no raw response |
| Folder outside allowlist | `IMAPFolderNotAllowedError` | No select call |
| Allowlisted folder absent | `IMAPFolderUnavailableError` | No select call |
| Malformed selected message | `IMAPMessageParseError` | No full-message fallback |

## 7. Scope Lock

### 3B1 IN SCOPE

- `app/integrations/__init__.py`
- `app/integrations/imap_adapter.py`
- `test/test_imap_adapter.py`

### 3B2 IN SCOPE

- `app/integrations/imap_adapter.py`
- `test/test_imap_adapter.py`

### OUT OF SCOPE FOR BOTH

- all existing configuration, credential, persistence, migration, repository, service, scheduler, route/UI, audit, and main files;
- any actual server/keyring/mailbox access, connection outside fakes, SMTP, external mutation, threading, synchronization, checkpoints, source persistence, AI, CRM, Calendar, raw MIME retention, and attachment bytes.

### RESTRICTIONS

- No dependency additions or installations.
- No real credentials, logs of fake/real secrets, or secret-bearing exceptions.
- No IMAP mutation method/call; no whole-message or attachment-body fetch.
- No retries, persistence, audit write, business interpretation, or scheduler integration.

## 8. STOP conditions

Stop before implementation if any required IMAPClient operation cannot be represented by the injected fake contract without a real connection; if a new package is needed; if body extraction requires full-message/attachment fetch; if an existing configuration/credential/persistence file must change; or if any request expands to synchronization, threading, or external mutation.

## 9. Definition of Done

- Only the three Scope Lock files change.
- 3B1 and 3B2 public contracts, typed errors, and fake-only tests are present.
- TLS is explicitly enabled; missing credentials prevent client creation; all selection is read-only.
- No whole-message/attachment fetch, persistence, real keyring access, network use in tests, or IMAP mutation occurs.
- Focused adapter tests and the full pytest suite are green.
- Diff review confirms no changes outside Scope Lock and no `main` modification.
