# Implementation Phase 1 Analysis

**Status:** READY FOR APPROVAL

## 1. Objective and context

Create the smallest executable vertical slice for the approved local architecture: a localhost-only FastAPI application with non-secret configuration, SQLite/SQLAlchemy/Alembic bootstrap, a minimal health/status UI, audit/logging groundwork, and an isolated pytest suite. No commercial integrations, credentials, or business workflows are included.

## 2. Documentation consulted

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/plans/technical-stack-decisions.md`
- `docs/plans/remote-ai-data-policy.md`
- `docs/plans/templates/implementation-plan.md`
- `docs/plans/implementation-phase-1-task.md`

## 3. Current state

**NO IMPLEMENTATION YET.** The repository contains approved documentation and plans only.

## 4. Proposed Phase 1 increment

Phase 1 should prove the local technical foundation without connecting to IMAP, Google Calendar, CRM, AI, or Windows Credential Manager.

It includes:

- Python package and application entry point;
- FastAPI/Uvicorn localhost-only startup;
- Jinja2 minimal health/status page and health endpoint;
- TOML loading for non-secret settings only;
- SQLAlchemy data-access bootstrap for the assistant SQLite database;
- Alembic migration configuration and an initial empty/schema-baseline migration appropriate to the foundation;
- repository/session boundary and minimal audit/logging abstractions without sensitive payloads;
- CSRF/session groundwork for future state-changing UI operations, without external actions;
- pytest setup, isolated SQLite test database, application startup test, health-route test, configuration validation test, and migration smoke test.

## 5. Proposed files and module boundaries

The later implementation task should create only the following foundation paths, subject to final review of the implementation plan:

```text
app/
  __init__.py
  main.py
  config.py
  web/routes.py
  web/templates/status.html
  persistence/database.py
  persistence/models.py
  persistence/repositories.py
  audit.py
  security/session.py
alembic/
  env.py
  versions/<initial_baseline>.py
alembic.ini
pyproject.toml
config.example.toml
test/
  conftest.py
  test_startup.py
  test_status.py
  test_config.py
  test_migrations.py
```

`main` must bind to `127.0.0.1` by default. The domain layer remains free of FastAPI, SQLAlchemy, and future adapters. Persistence is assistant-only; no CRM database path or connection is introduced.

## 6. Dependencies

Use only approved Phase 1 dependencies: Python 3.11+, FastAPI, Uvicorn, Jinja2, SQLAlchemy 2.x, Alembic, TOML parsing from the selected Python-supported standard/approved mechanism, pytest, and their direct required runtime dependencies. Do not add IMAPClient, Google libraries, httpx, APScheduler, keyring, HTMX, or an AI SDK in Phase 1 because no approved Phase 1 behavior needs them.

## 7. Configuration, secrets, and startup

`config.example.toml` documents non-secret localhost host/port, SQLite database path, and safe logging/synchronization placeholders. Actual configuration is local and excluded from Git as appropriate. Secrets are prohibited in TOML; a secret-provider interface may exist only as a non-functional boundary with no real keyring access or credentials.

Windows Task Scheduler configuration is deferred. The Phase 1 startup acceptance command runs Uvicorn manually with localhost binding. Weekend scheduling and APScheduler workflows are deferred.

## 8. Database, migration, and recovery approach

The first migration establishes only the minimum assistant database foundation required by Phase 1, without prematurely implementing full commercial entities or external integrations. The migration must be reproducible against an empty isolated SQLite database. Runtime database files are local, never committed, and test databases are temporary/isolated.

Rollback is migration-version controlled: a failed Phase 1 change is reverted through the reviewed code/migration path, never by deleting a user database. Since no real user data or integrations exist yet, recovery scope is limited to clean bootstrap and test database recreation.

## 9. Test suite and acceptance criteria

- Application starts with valid non-secret test configuration.
- Binding configuration rejects non-loopback defaults or otherwise enforces `127.0.0.1`.
- Health/status route renders without secrets or external calls.
- Isolated SQLite database initializes through Alembic migration smoke test.
- Repository/session setup is isolated per test and leaves no shared production data.
- Logging/audit groundwork does not emit secrets or source content.
- No test requires production credentials, live services, or external mutation.

## 10. Deferred to later phases

- Full data-model entity implementation beyond the bootstrap required by this increment.
- IMAP, thread reconstruction, drafts, and filing.
- Google Calendar, CRM API, AI, keyring integration, and APScheduler synchronization workflows.
- Manual note/WhatsApp workflows, business UI, approval execution, CSRF-protected mutation endpoints, and full audit/provenance behavior.
- Windows Task Scheduler setup, real secret configuration, and non-production integration tests.

## 11. Risks and dependencies

- Database bootstrap must not silently choose or implement unapproved business semantics.
- Session/CSRF groundwork must not be mistaken for authorization of external mutations.
- Configuration and logging must avoid creating a secret-storage bypass.
- Alembic setup must remain testable on Windows and isolated from user data.

## 12. Implementation task sizing

A single implementation task is safe because the increment has no external integrations, no real credentials, no external mutations, and a bounded set of foundation files. It must stop if a full business entity, external adapter, real secret access, or scheduler workflow becomes necessary.

## 13. Proposed implementation Scope Lock

### In scope

- Create the files listed in section 5.
- Add only Phase 1 approved dependencies.
- Implement localhost startup, non-secret configuration, SQLite/SQLAlchemy/Alembic bootstrap, health/status UI, minimal safe audit/logging groundwork, and listed isolated tests.

### Out of scope

- All external adapters, real credentials, APScheduler jobs, business workflows, full commercial data model, external mutations, Windows Task Scheduler setup, and changes to approved documentation.

### Restrictions

- No binding outside `127.0.0.1`.
- No secrets in files, tests, logs, TOML, or SQLite plaintext fields.
- No external system calls or side effects.
- No new foundational technology beyond the approved stack.
- No modification of `main`.

## 14. Result

**READY FOR APPROVAL**

The Phase 1 foundation can proceed as one later Implement Task after explicit approval of this plan and Scope Lock.
