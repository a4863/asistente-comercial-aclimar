# Approved Technical Stack — 2026-09-21

## Status

Approved by user.

This document resolves the remaining technical choices required before creating `docs/architecture.md`.

It is authoritative for the architecture-document task.

---

## 1. Language and web framework

**Decision**

- Python 3.11+
- FastAPI
- Jinja2 server-rendered UI
- minimal JavaScript, with HTMX allowed only where it materially simplifies interaction

**Rationale**

- consistent with the existing CRM technology family;
- reduces operational complexity on the same Windows PC;
- suitable for a localhost-only, single-user application;
- avoids unnecessary SPA/frontend infrastructure.

The application remains a local web application accessed through localhost.

---

## 2. Persistence

**Decision**

- SQLite
- SQLAlchemy 2.x
- Alembic

**Rules**

- SQLite is the assistant database only.
- The assistant must never access the CRM database directly.
- CRM integration remains API-only.
- SQLAlchemy provides the persistence/data-access abstraction.
- Alembic is the migration mechanism.

---

## 3. Scheduling and synchronization

**Decision**

- APScheduler running inside the main FastAPI application process.

**Rules**

- no Celery;
- no Redis;
- no distributed queue;
- no separate Windows background service in the MVP;
- synchronization checkpoints are persisted in the assistant database;
- APScheduler triggers synchronization, but persistence owns checkpoint state;
- after downtime or weekend shutdown, synchronization resumes incrementally from the last successful checkpoint.

The application is expected to remain running 24 hours per day Monday through Friday.

---

## 4. IMAP and email parsing

**Decision**

- IMAPClient for IMAP access;
- Python standard-library `email` package for MIME/header parsing.

**Rules**

- no automatic email sending;
- no mailbox folder creation in MVP;
- message moves require explicit approval;
- mailbox draft creation requires explicit approval;
- thread reconstruction follows Message-ID / In-Reply-To / References first;
- synchronization and draft creation must be idempotent.

SMTP is not part of automatic execution in the MVP.

---

## 5. Google Calendar

**Decision**

Use Google's official Python client libraries:

- `google-api-python-client`
- appropriate Google OAuth libraries

**Scope**

- one configured primary Calendar;
- automatic reads;
- create/modify only after explicit approval;
- delete outside MVP.

---

## 6. CRM integration

**Decision**

- `httpx` as HTTP client;
- integration only through the CRM FastAPI/API contract.

**Prohibited**

- direct `crm.db` access;
- HTML scraping;
- arbitrary database-field updates.

---

## 7. Windows credential storage

**Decision**

- Python `keyring` package;
- Windows Credential Manager as the secure backend.

**Rules**

Credentials/tokens/secrets must never be stored in:

- source code;
- Git;
- SQLite plaintext fields;
- normal configuration files;
- logs.

Application persistence may store only logical credential references/identifiers when necessary.

Each integration must remain independently configurable and revocable.

---

## 8. Non-secret configuration

**Decision**

Use a local TOML configuration file for non-secret application settings.

Suitable examples:

- synchronization intervals;
- local CRM base URL;
- configured mailbox identity;
- Calendar ID;
- local server host/port;
- non-sensitive feature flags.

Secrets are prohibited in TOML.

---

## 9. AI architecture

**Decision**

Create a provider-agnostic AI service abstraction.

A conceptual interface such as `AIService` or equivalent separates domain/application rules from the eventual AI provider.

**Not selected yet**

- OpenAI;
- any other remote provider;
- model family;
- local model.

Before remote AI is implemented, `docs/security.md` must define the exact classes of commercial data allowed to leave the device.

---

## 10. Local startup and network binding

**Decision**

- FastAPI served by Uvicorn;
- Windows Task Scheduler starts the application at user logon;
- application binds to `127.0.0.1` only;
- browser accesses the application locally.

**Rules**

- do not bind to LAN interfaces by default;
- no hosted backend;
- no SaaS deployment;
- no public network exposure.

The process is expected to remain active Monday through Friday.

Weekend shutdown is permitted.

On restart, persisted checkpoints drive incremental catch-up.

---

## 11. Application structure

**Decision**

Modular monolith.

Conceptual dependency direction:

```text
UI / routes
    ↓
application services
    ↓
domain
    ↓
repository / integration abstractions
```

External adapters include:

- IMAP;
- Google Calendar;
- CRM API;
- AI;
- Windows Credential Manager;
- persistence.

Domain rules must not depend directly on FastAPI, IMAPClient, Google client libraries, httpx, SQLAlchemy, APScheduler, keyring, or a specific AI provider.

No microservices or distributed infrastructure.

---

## 12. Testing stack

**Decision**

- pytest

Tests must isolate real external systems with fixtures, fakes, mocks, or controlled test doubles.

Automated tests must not:

- send real email;
- move real mailbox messages;
- create real drafts unintentionally;
- modify real Google Calendar;
- write to the real CRM;
- use production credentials unnecessarily.

---

## 13. Architecture implications

`docs/architecture.md` may now use these concrete technologies as approved MVP choices:

- Python 3.11+
- FastAPI
- Jinja2
- minimal JavaScript / optional HTMX
- SQLite
- SQLAlchemy 2.x
- Alembic
- APScheduler
- IMAPClient
- Python `email`
- Google official Python API/OAuth libraries
- httpx
- keyring + Windows Credential Manager
- TOML configuration
- Uvicorn
- Windows Task Scheduler
- pytest

No other materially different foundational technology should be selected silently.

---

## Result

The remaining technical blockers for the architecture document are resolved.

Codex may now execute `docs/plans/architecture-document-task.md` and create `docs/architecture.md`, subject to that task's Scope Lock.
