# Runtime Configuration Loading Acceptance

**Status:** ACCEPTED
**Date:** 2026-09-25

## Scope

Accepted implementation:
- `app/config.py`
- `test/test_config.py`
- `app/main.py`
- `test/test_startup.py`
- `app/security/credential_cli.py`
- `test/test_credential_cli.py`
- `app/integrations/ai_smoke_cli.py`
- `test/test_ai_smoke_cli.py`

Implementation commit:
- `90fc879a25f06aa5d16c1e052935470c4d7f6945`

## Accepted behavior

- canonical runtime config is resolved from Windows current-user LocalAppData known folder plus:
  - ACLIMAR
  - Asistente Comercial
  - config.toml
- no CWD/repository/argv/application-env config discovery is introduced;
- `load_settings(None)` remains defaults-only and does not discover ambient config;
- `create_app()` and module import remain inert with respect to operational config;
- `run(settings=None)`, credential CLI and smoke CLI use the shared operational loader;
- explicit `Settings` injection bypasses ambient discovery for tests/composition;
- missing/invalid operational config fails closed with bounded output;
- runtime loader does not create or rewrite config files;
- closed TOML schema rejects unknown tables/keys and secret-bearing configuration;
- actual credentials remain in keyring/Windows Credential Manager;
- AI technical enablement remains independent of commercial authorization;
- enabled operational AI requires an adapter-allowlisted endpoint;
- smoke invalid/disabled configuration fails before lock/keyring/provider;
- no live OpenAI call was performed.

## Validation

User-reported focused validation:
- 126 passed

Full suite:
- 731 passed
- 2 skipped

`git diff --check` passed.

Commit diff contains exactly the eight approved Scope Lock files.

## Result

**ACCEPTED.**

Phase 6F may resume only after the real canonical non-secret TOML exists and its values are preflighted. The prior one-live-call authorization remains unused because no live call occurred.
