# Runtime Configuration Loading Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-25
**Depends on:** runtime-config-loading-analysis.md — READY FOR PLAN
**Purpose:** unblock Phase 6F without weakening fail-closed runtime behavior

## Objective

Produce an implementation-ready plan for a single canonical non-secret runtime TOML configuration contract shared by:
- controlled application launcher;
- credential CLI;
- synthetic smoke CLI.

Do not implement code in this task.

## Fixed decisions

Canonical local configuration path:

`%LOCALAPPDATA%\ACLIMAR\Asistente Comercial\config.toml`

Interpret this as the Windows current-user LocalAppData known folder plus fixed child components:
- `ACLIMAR`
- `Asistente Comercial`
- `config.toml`

No CWD-relative fallback, repository-relative file, path search, argv path, application-specific environment override, or arbitrary user-supplied path is allowed.

## Required contract

The plan must preserve:

1. `load_settings(path: Path | None = None)` as an explicit parser/defaults API for tests and inert composition.
2. A separate operational resolver/loader in `app/config.py`.
3. `create_app()` and module-level `app = create_app()` must remain inert and must not discover/read runtime config.
4. `run(settings=None)` must use the operational loader exactly once; explicit `Settings` injection bypasses discovery.
5. `credential_cli` and `ai_smoke_cli` must use the same operational loader.
6. Missing/unreadable/invalid operational config must fail closed with bounded errors and no fallback to defaults.
7. Runtime loader must never create directories/files or rewrite TOML.
8. Runtime TOML must contain only approved non-secret configuration.
9. Unknown top-level tables and unknown keys in every supported table must be rejected.
10. Secret-bearing keys/tables must be rejected without echoing values.
11. Credential service/account remain non-secret references; actual secrets remain only in keyring/Windows Credential Manager.
12. AI technical enablement remains independent of commercial authorization.
13. Adapter endpoint allowlist remains authoritative.
14. Runtime settings are loaded once per process/command, not hot-reloaded.
15. No dependency, migration or database schema change.

## Planning questions to resolve exactly

1. Exact Windows LocalAppData resolution implementation using stdlib/ctypes.
2. Exact helper names/signatures in `app/config.py`.
3. Exact exception/bounded error contract for:
   - known-folder resolution failure;
   - missing file;
   - non-regular path;
   - unreadable file;
   - malformed TOML;
   - unknown table/key;
   - invalid field.
4. Exact set of supported top-level tables and allowed keys per table.
5. Whether empty approved tables are valid.
6. Exact rules for operational AI config:
   - enabled false;
   - enabled true;
   - required base_url;
   - model/provider validation;
   - numeric defaults.
7. Exact behavior of `run()` on operational config failure.
8. Exact CLI output/exit codes on config failure for credential and smoke CLIs.
9. Exact way tests inject/override the Windows known-folder resolver without touching real LocalAppData.
10. Exact Scope Lock and per-file changes.
11. Exact regression tests proving import/create_app inertness.
12. Exact tests proving CLIs use the same file and configured credential references.
13. Exact tests proving unsupported endpoint/config never reaches keyring/lock/provider.
14. Exact rollback behavior if implementation exposes incompatibility with existing approved TOML schema.

## Expected Scope Lock

Plan should normally cover exactly:

Production:
- app/config.py
- app/main.py
- app/security/credential_cli.py
- app/integrations/ai_smoke_cli.py

Tests:
- test/test_config.py
- test/test_startup.py
- test/test_credential_cli.py
- test/test_ai_smoke_cli.py

If any other file is required, STOP and explain why.

## Restrictions

Do not:
- change OpenAI adapter;
- change commercial gate;
- change routes/templates;
- change persistence/models/migrations;
- add config-path CLI args;
- add env overrides;
- add dependency;
- create/read real LocalAppData during tests;
- access real keyring;
- call OpenAI.

## Deliverable

Create only:

`docs/plans/runtime-config-loading-plan.md`

Include:
- exact runtime config contract;
- exact supported TOML schema;
- exact operational loader API;
- exact CLI/launcher behavior;
- exact Scope Lock;
- per-file implementation steps;
- offline test matrix;
- fail-closed/rollback behavior;
- STOP findings;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan runtime configuration loading contract

Push only origin/codex-work.
