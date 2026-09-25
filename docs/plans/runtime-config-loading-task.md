# Runtime Configuration Loading Implementation Task

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** docs/plans/runtime-config-loading-plan.md — READY FOR IMPLEMENT
**Purpose:** unblock Phase 6F while preserving fail-closed runtime behavior

## Objective

Implement the approved canonical non-secret runtime TOML loading contract shared by:
- controlled application launcher;
- credential CLI;
- synthetic smoke CLI.

No live provider call is authorized in this task.

## Exact Scope Lock

Modify exactly these eight files:

1. app/config.py
2. test/test_config.py
3. app/main.py
4. test/test_startup.py
5. app/security/credential_cli.py
6. test/test_credential_cli.py
7. app/integrations/ai_smoke_cli.py
8. test/test_ai_smoke_cli.py

No other tracked file may change.

## Canonical runtime path

Use exactly:

%LOCALAPPDATA%\ACLIMAR\Asistente Comercial\config.toml

Resolve Windows current-user LocalAppData with stdlib ctypes + SHGetKnownFolderPath for FOLDERID_LocalAppData.

Do not use:
- os.environ["LOCALAPPDATA"];
- CWD;
- repository-relative paths;
- executable-relative paths;
- path search;
- argv config paths;
- application-specific env overrides;
- registry fallback.

## app/config.py

Implement:

- bounded RuntimeConfigError whose message is exactly:
  configuration_unavailable

- _windows_local_appdata() -> Path
  - Windows-only;
  - explicit ctypes GUID/API declarations;
  - SHGetKnownFolderPath;
  - copy result;
  - always CoTaskMemFree;
  - require successful HRESULT;
  - require nonempty absolute path;
  - any failure -> bounded RuntimeConfigError.

- operational_config_path() -> Path
  - append fixed components only;
  - validate against symlink/reparse/device/directory misuse;
  - no file creation;
  - no fallback.

- load_operational_settings() -> Settings
  - resolve once;
  - require readable regular file;
  - read once;
  - parse through approved strict schema;
  - wrap discovery/read/encoding/TOML/schema errors as RuntimeConfigError("configuration_unavailable") from None;
  - do not cache globally;
  - do not hot-reload;
  - do not log raw errors/path/content.

Preserve:
- load_settings(path=None) -> fail-closed defaults, no discovery.
- explicit load_settings(path) -> parses that path.
- create_app() and module import remain inert.

## Closed TOML schema

Allow only these top-level tables:
- server
- database
- imap
- ai

Reject:
- top-level scalars;
- unknown tables;
- dotted unknown tables;
- unknown keys inside approved tables;
- secret-bearing keys/tables such as api_key/password/token/credentials;
- invalid types including bool where integer required.

Exact allowed keys and validation must match the approved plan.

Critical AI rules:
- enabled defaults false;
- enabled=true must be explicit in TOML;
- provider must be openai;
- model remains configurable, nonempty/trimmed;
- enabled=true requires explicit base_url;
- base_url for operational enabled AI must be exactly one of:
  https://api.openai.com/v1
  https://eu.api.openai.com/v1
- timeout_seconds=60;
- max_retries=1;
- existing request/output limits retained;
- credential service/account are references only, never secrets.

Adapter allowlist remains unchanged and authoritative.

## app/main.py

Only change run():

- run(settings=None):
  - call load_operational_settings() exactly once;
  - on RuntimeConfigError, abort before create_app/DB/lock/keyring/Uvicorn/readiness;
  - bounded failure only: SystemExit("configuration_unavailable").

- run(settings=<Settings>):
  - use supplied Settings directly;
  - no runtime discovery.

Do not change:
- create_app();
- module-level app;
- lifespan semantics;
- lock/recovery behavior.

## credential CLI

Keep existing CLI syntax.

After argument/help validation but before keyring/prompt:
- call load_operational_settings() once;
- use configured AI credential_service/account;
- on RuntimeConfigError:
  - stdout exactly unavailable\n
  - empty stderr
  - exit 1
  - no keyring access;
  - no getpass prompt;
  - no default-reference fallback.

No provider call.

## smoke CLI

Keep existing CLI syntax and fixed payload.

After argument/help validation:
- call load_operational_settings() once;
- on RuntimeConfigError:
  - stdout exactly unavailable\n
  - empty stderr
  - exit 1;
  - no lock;
  - no keyring;
  - no adapter/provider.

If valid config but AI disabled:
- retain disabled\n / exit 1 before lock/keyring/provider.

If enabled with allowlisted endpoint:
- preserve existing lock + credential + adapter smoke path.

Do not inspect or mutate commercial gate.

## Tests

### test/test_config.py

Cover at minimum:
- exact canonical child path;
- CWD independence;
- no environment fallback;
- known-folder failure;
- missing file;
- directory instead of file;
- symlink/reparse/device/non-regular rejection;
- unreadable file;
- bad UTF-8;
- malformed TOML;
- bounded error without path/key/value leakage;
- unknown top-level table;
- unknown key in every approved table;
- secret-bearing table/key rejection;
- top-level scalar rejection;
- empty file valid -> disabled defaults;
- valid closed schema;
- bool rejected for integer fields;
- enabled AI requires explicit allowlisted base_url;
- unsupported enabled endpoint rejected.

Tests must monkeypatch the private resolver and never touch real LocalAppData.

### test/test_startup.py

Cover:
- run() without Settings loads operational settings exactly once;
- run(Settings) never discovers;
- config failure prevents Uvicorn, lock, DB, keyring, readiness;
- import/create_app remain inert;
- existing operational startup/recovery tests remain green.

### test/test_credential_cli.py

Cover:
- all actions use configured service/account;
- missing/invalid config -> unavailable, exit 1;
- no keyring/prompt/default fallback on config failure;
- help/invalid args do not trigger discovery;
- no raw config/secret leakage.

### test/test_ai_smoke_cli.py

Cover:
- valid enabled config reaches existing fake smoke once;
- disabled config stops before lock;
- missing/invalid/unsupported config stops before lock/keyring/provider;
- configured DB identity reaches lock;
- no gate access;
- no real provider/network.

## Restrictions

Do not modify:
- OpenAI adapter;
- activation gate;
- routes/templates;
- credentials implementation;
- persistence/models/migrations;
- domain/services;
- pyproject;
- docs;
- any other file.

Do not:
- add dependency;
- add migration;
- add CLI config-path arg;
- add environment override;
- read actual LocalAppData in tests;
- access real keyring;
- call OpenAI live;
- create the real config file;
- enable commercial authorization.

## Validation

Run:

python -m pytest test/test_config.py test/test_startup.py test/test_credential_cli.py test/test_ai_smoke_cli.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly the eight Scope-Locked files.

## STOP conditions

STOP if:
- another file is required;
- implementation needs a new dependency;
- safe Windows known-folder resolution cannot be implemented with stdlib/ctypes;
- an existing approved TOML key conflicts with the closed schema;
- create_app/import would need ambient runtime discovery;
- adapter/gate changes appear necessary;
- live provider access appears necessary.

## Completion

Commit:

Implement canonical runtime configuration loading

Push only origin/codex-work.
