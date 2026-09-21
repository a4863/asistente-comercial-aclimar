# Plan: Implementation Phase 1 Foundation

**Status:** Approved for planning; requires explicit implementation approval

**Date:** 2026-09-21

**Baseline:** `codex-work` after the approved documentation and Phase 1 analysis.

## 1. Objective

Create a runnable, localhost-only FastAPI foundation with non-secret configuration, isolated SQLite/SQLAlchemy/Alembic bootstrap, minimal status UI, safe audit/logging/session groundwork, and pytest smoke coverage.

## 2. Preconditions

- Scope Lock below is explicitly approved for the later Implement Task.
- Python 3.11+ is available.
- Dependencies are installed only during the later implementation task.
- No production credentials, mailbox, Calendar, CRM, AI, or user database are used.

## 3. Scope

### Includes

- Approved FastAPI/Uvicorn/Jinja2/SQLite/SQLAlchemy/Alembic/pytest foundation.
- TOML non-secret configuration and `127.0.0.1` default enforcement.
- Initial assistant database bootstrap and migration smoke test.
- Health/status route and template.
- Minimal repository/session, audit/logging, and session/CSRF boundaries without external mutations.

### Excludes

- IMAP, Calendar, CRM, AI, real keyring, APScheduler jobs, Windows Task Scheduler, business workflows, full commercial model, real credentials, external calls, and production integration tests.

## 4. Authorized files

```text
app/__init__.py
app/main.py
app/config.py
app/web/routes.py
app/web/templates/status.html
app/persistence/database.py
app/persistence/models.py
app/persistence/repositories.py
app/audit.py
app/security/session.py
alembic/env.py
alembic/versions/<initial_baseline>.py
alembic.ini
pyproject.toml
config.example.toml
test/conftest.py
test/test_startup.py
test/test_status.py
test/test_config.py
test/test_migrations.py
```

No other file may be created or modified. The listed set is sufficient for a static initial Alembic baseline and upgrade smoke test; automatic future revision generation is deferred.

## 5. Dependencies

Add only FastAPI, Uvicorn, Jinja2, SQLAlchemy 2.x, Alembic, pytest, and direct required dependencies. Do not add IMAPClient, Google libraries, httpx, APScheduler, keyring, HTMX, or AI SDKs.

## 6. Implementation order

1. Create package skeleton and dependency manifest.
2. Implement typed non-secret configuration loading and loopback-only validation.
3. Add SQLAlchemy engine/session bootstrap and empty/minimal foundation metadata.
4. Configure Alembic and add initial baseline migration.
5. Add repository/session boundary and minimal audit/logging interface with safe payload rules.
6. Add session/CSRF groundwork with no mutation endpoints or external execution.
7. Add FastAPI app, health/status route, and Jinja2 status template.
8. Add isolated pytest fixtures and the five tests below.
9. Run migration smoke and pytest; inspect diff and status.

## 7. Configuration and startup

`config.example.toml` contains only non-secret localhost host/port, SQLite path, and safe settings. It contains no credential values. Uvicorn starts manually for Phase 1 and binds only to `127.0.0.1`; Task Scheduler is deferred.

## 8. Exact tests and commands

- `test_startup.py`: application creation and loopback startup configuration.
- `test_status.py`: health/status route response and template render without external calls or secrets.
- `test_config.py`: valid test config and rejection of non-loopback host defaults.
- `test_migrations.py`: Alembic upgrade against an empty isolated SQLite database.
- `conftest.py`: temporary isolated database/configuration and no production credential access.

Commands for the later implementation task:

```text
pytest
alembic upgrade head
```

The migration command must point only to the isolated test database during verification.

## 9. Acceptance criteria

- Local FastAPI application starts with valid test configuration.
- It binds only to `127.0.0.1` by default.
- Status/health UI works without external integrations.
- Alembic upgrades an empty isolated SQLite database.
- Tests are deterministic and do not use production systems or secrets.
- Logs/audit groundwork does not emit secret or source-content payloads.
- Only authorized files change.

## 10. Negative validations and STOP conditions

STOP before expanding scope if implementation needs a commercial entity, business lifecycle, external adapter, real keyring lookup, scheduler job, real credential, non-loopback binding, external call, or file outside section 4.

Reject secret values in TOML, source, test fixtures, SQLite plaintext data, logs, and browser responses. Reject tests that contact real mailbox, Calendar, CRM, AI, or `crm.db`.

## 11. Rollback and recovery

No user data or external state exists in this phase. Revert code/migration through reviewed Git changes; never delete a user database as a recovery shortcut. Isolated test databases may be recreated.

# SCOPE LOCK

### IN SCOPE

Only the files in section 4, their approved dependencies, local startup, isolated database bootstrap, migration smoke behavior, status UI, and listed tests.

### OUT OF SCOPE

Everything listed in section 3 exclusions, all external systems, and all approved documentation other than this plan.

### RESTRICTIONS

- No external effects or real credentials.
- No change to `main`.
- No technology outside the approved stack.
- No scope expansion without a new analysis/approval.

## 12. Definition of Done

The exact authorized files are implemented, `pytest` and isolated migration smoke tests pass, the diff/status contain no unauthorized changes, Scope Lock is respected, and the result is reviewed before the next phase.
