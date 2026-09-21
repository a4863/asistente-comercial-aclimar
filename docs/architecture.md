# Architecture — Asistente Comercial ACLIMAR

## 1. Objectives and execution context

The MVP is a local, single-user modular monolith running on Alejandro's Windows PC. It is a Python 3.11+ FastAPI application served by Uvicorn and bound exclusively to `127.0.0.1`. Jinja2 provides the server-rendered local UI; JavaScript remains minimal, with HTMX permitted only when it materially simplifies an interaction.

There is no hosted backend, SaaS, multi-tenancy, LAN binding, microservice, distributed queue, message broker, cloud database, or direct CRM database access.

## 2. Component diagram

```text
Browser on localhost
        ↓
FastAPI routes + Jinja2 UI
        ↓
Application services
        ↓
Domain workflows and rules
        ↓
Repository / adapter abstractions
   ┌────┼────────┬─────────┬─────────┬──────────┐
SQLite  IMAP     Calendar  CRM API   AI service  Credential store
SQLAlchemy       Google    httpx     boundary    keyring/Windows CM
Alembic          client
```

APScheduler runs inside the FastAPI process and invokes application synchronization services. Domain rules do not depend directly on FastAPI, SQLAlchemy, APScheduler, IMAPClient, Google libraries, httpx, keyring, or an AI provider.

## 3. Layers and responsibilities

- **UI/routes:** localhost dashboard, review, approvals, manual note/WhatsApp entry, configuration and integration-status views. Routes do not perform external mutations directly.
- **Application services:** coordinate use cases, transactions, synchronization, analysis, approvals, and execution.
- **Domain:** enforces facts versus inferences versus proposals; approved lifecycles; follow-up precedence; ambiguity preservation; and approval requirements.
- **Persistence:** SQLite assistant database, SQLAlchemy 2.x data-access layer, and Alembic migrations. It implements the approved data model, current state, history, checkpoints, idempotency identities, and audit events.
- **Adapters:** isolate IMAP, Calendar, CRM API, AI, and Windows Credential Manager from domain rules.

## 4. Sources and integrations

### IMAP

IMAPClient reads the one configured mailbox; Python's `email` package parses MIME and headers. Incremental reads persist source observations and checkpoints. Thread reconstruction prioritizes Message-ID, In-Reply-To, and References; insufficient evidence leaves messages separate.

The adapter discovers existing folders. It never sends mail or creates folders. A move or draft creation can occur only through an approved action proposal and execution flow. Synchronization and draft creation are idempotent.

### Google Calendar

Google's official Python client and OAuth libraries access one configured primary Calendar. Reads occur during synchronization. Create/modify operations require approved action proposals; deletion is outside the MVP. Changed or deleted-at-source events are reconciled through source observations while retaining historical references.

### CRM

`httpx` calls only the explicit CRM FastAPI/API contract. The adapter reads context and executes only approved, explicit CRM business operations. It never accesses `crm.db`, scrapes HTML, or performs arbitrary field updates.

### Manual sources

Manual notes and pasted WhatsApp text enter through application services, preserve original text as source evidence, and are then eligible for analysis. WhatsApp remains manual and text-only.

## 5. AI boundary

An `AIService`-equivalent provider-agnostic abstraction separates analysis from domain rules. It receives only context required for a specific analysis and returns structured candidate facts, inferences, proposals, summaries, questions, commitments, tasks, and next steps. Domain services apply approved business rules and preserve provenance.

No AI provider or model is selected. Remote AI implementation is prohibited until `docs/security.md` specifies allowed data classes. Credentials, attachments, whole databases, and unrelated commercial data must never be supplied as model context.

## 6. Synchronization, checkpoints, and recovery

APScheduler runs periodic jobs in the main application process while it is active. The assistant is expected to run 24 hours per day Monday through Friday; a separate Windows service is outside the MVP.

Each integration persists its last successful checkpoint and synchronization observations in the assistant database. On startup after downtime, including Monday after a weekend shutdown, the coordinator resumes incremental synchronization and reconciliation from the last successful checkpoint. It must not require a full historical resynchronization merely because the application was stopped.

Integration failures are isolated: IMAP, Calendar, CRM, or AI failures produce integration-specific degraded/reconnect state and audit/log events, while local UI and previously stored data remain usable.

## 7. Approval, execution, idempotency, and revalidation

All external mutations flow through:

```text
ActionProposal → ApprovalDecision → target revalidation → ExecutionResult → AuditEvent
```

One action proposal represents one concrete action. Before execution, the application revalidates external state where it may have changed, such as a message moved in Outlook. Idempotency identities and persisted execution attempts prevent duplicate source processing, drafts, activities, tasks, Calendar actions, and CRM proposals. Failures remain auditable and distinguishable from approved but unexecuted actions.

## 8. Configuration, secrets, and startup

Non-secret local settings use TOML: intervals, mailbox identity, Calendar ID, CRM base URL, localhost host/port, and non-sensitive feature flags. TOML never stores secrets.

Python `keyring` uses Windows Credential Manager for credentials and tokens. Each integration has independently manageable references; credentials remain outside source code, Git, SQLite plaintext fields, normal configuration, and logs.

Windows Task Scheduler starts the local Uvicorn application at user logon. The browser accesses localhost. Weekend shutdown is permitted; weekday operation relies on the running main process and persisted recovery state.

## 9. Audit, logging, and local observability

The architecture persists the data model's append-only audit events for source provenance, analysis derivation, approvals, execution outcomes, failures, corrections, and source deletion/redaction metadata. Logs provide minimum local observability: application startup/shutdown, checkpoint status, synchronization results, integration degradation, and action outcomes. Logs must not contain credentials or unnecessary sensitive source content.

## 10. Security assumptions

All email, WhatsApp, notes, Calendar, CRM, and attachment content is untrusted data, never executable instruction. The application remains local-user scoped and localhost-only. Credentials are isolated in the OS secure store. Exact data-disclosure classes, retention controls, encryption details, and security verification remain for `docs/security.md`.

## 11. Testing boundaries

pytest is the test framework. Tests isolate SQLite persistence, adapters, scheduler/clock, AI service, keyring, and network clients with fixtures, fakes, mocks, or controlled test doubles. They must never send real email, move real messages, create real drafts, alter real Calendar/CRM data, or use production credentials unnecessarily.

Required boundaries include domain lifecycle tests, repository/migration tests, adapter contract tests, synchronization/recovery/idempotency tests, revalidation tests, audit/provenance tests, and degraded-integration tests.

## 12. Deferred and out-of-MVP architecture

Deferred: concrete AI provider/model, exact remote-AI data classes, encryption details, database schema/index specifics, and local packaging refinements. These require later security or implementation decisions.

Out of MVP: automatic email sending, automatic WhatsApp integration, Calendar deletion, autonomous CRM writes, multi-user operation, hosted backend, SaaS, native mobile app, separate Windows synchronization service, microservices, distributed infrastructure, and cloud persistence.
