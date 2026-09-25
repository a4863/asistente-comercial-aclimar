# Phase 6C Implementation Task — Interactive AI Credential CLI

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-25
**Depends on:** Phase 6B2 ACCEPTED
**Plan:** docs/plans/implementation-phase-6-plan.md
**Decision:** D4

## Objective

Add a small local interactive CLI for setting/replacing, checking presence of, and deleting the OpenAI API credential using the existing Windows Credential Manager/keyring abstraction.

This task manages only the credential. It must not call OpenAI, activate commercial processing, or alter AI configuration.

## Exact Scope Lock

Create only:

1. app/security/credential_cli.py
2. test/test_credential_cli.py

Modify only:

3. app/security/credentials.py
4. test/test_credentials.py
5. pyproject.toml

No other tracked file may change.

## Required CLI behavior

Provide a dedicated console command through `pyproject.toml`.

Supported actions must be bounded and explicit:

- set/replace credential;
- show presence/status only;
- delete credential.

The CLI must use the configured AI credential service/account from normal application settings.

### Set/replace

- obtain the secret interactively using non-echoing input (`getpass` or equivalent stdlib mechanism);
- do not accept the API key as a positional argument, command-line option, environment variable, stdin pipe contract, or config value;
- reject empty input;
- write through the existing credential abstraction/keyring backend;
- return/output only a bounded success/failure message;
- never print the secret, length, prefix, suffix, hash, or provider-derived information.

### Status

- use the bounded credential presence API;
- output only present/missing/unavailable;
- do not retrieve/display the secret in CLI code;
- no provider validation.

### Delete

- delete only the configured AI credential reference;
- bounded result such as deleted/missing/unavailable;
- no raw backend exception;
- repeated delete must be safe/bounded.

## Credential abstraction

Extend `KeyringCredentialStore` with the smallest write/delete API required.

Requirements:
- use keyring/Windows Credential Manager only;
- `set_secret(service, account, secret)` or equivalent;
- bounded delete method;
- no caching of secret;
- no repr/logging containing secret;
- backend errors converted to bounded result/error at the appropriate layer;
- existing get/presence semantics remain compatible.

Do not change the credential service/account identifiers.

## Security requirements

The secret must never be supplied through:
- argv;
- environment variables;
- TOML;
- SQLite;
- logs;
- exception text deliberately surfaced by this CLI;
- shell history.

Do not create files containing the key.

Do not invoke OpenAI to test the key.

The CLI is local/operator tooling only.

## Tests

Use fake keyring/getpass/settings only. No real keyring writes.

Prove at minimum:

1. set prompts through non-echoing input;
2. set writes the exact supplied synthetic secret to the configured service/account;
3. secret is absent from stdout/stderr/logs/repr;
4. empty secret is rejected and not written;
5. replacement uses the same configured credential reference;
6. status returns/displays only present/missing/unavailable;
7. status does not call provider/network;
8. delete removes the configured credential;
9. repeated/missing delete is bounded;
10. backend set/delete/read failure is bounded and does not expose raw error text;
11. CLI does not accept a secret argument or environment-based secret path;
12. help text contains no suggestion to pass a secret on command line;
13. existing get_secret/credential_presence tests remain green;
14. no commercial gate state is changed;
15. no OpenAI client/import is required for normal CLI execution.

## Restrictions

Do not modify:
- app/main.py
- routes/templates
- activation.py
- OpenAI adapter
- config schema/defaults
- persistence/models/migrations
- startup/recovery
- docs

Do not:
- call OpenAI;
- validate the key remotely;
- enable commercial processing;
- store the key anywhere except existing keyring backend;
- add third-party dependencies.

## Validation

Run:

python -m pytest test/test_credential_cli.py test/test_credentials.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/security/credential_cli.py
- test/test_credential_cli.py
- app/security/credentials.py
- test/test_credentials.py
- pyproject.toml

## STOP conditions

STOP if:
- secure non-echoing input cannot be implemented with stdlib/current dependencies;
- another production/test file is required;
- credential service/account identifiers would need changing;
- backend writes require persistence outside keyring;
- any provider/network call appears necessary.

## Completion

Commit:

Implement phase 6C interactive credential CLI

Push only origin/codex-work.
