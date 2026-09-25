# Phase 6C Acceptance — Interactive AI Credential CLI

**Status:** ACCEPTED
**Date:** 2026-09-25

## Scope

Accepted implementation:
- `app/security/credential_cli.py`
- `test/test_credential_cli.py`
- `app/security/credentials.py`
- `test/test_credentials.py`
- `pyproject.toml`

Implementation commit:
- `9254977c42983307f1812cb81aab305c407833f0`

## Accepted behavior

- dedicated local credential CLI is registered;
- supported actions are set/status/delete only;
- secret input for set uses non-echoing interactive getpass;
- non-interactive stdin is rejected for secret entry;
- secret is not accepted through argv/options;
- empty/blank input is rejected;
- configured AI credential service/account are reused unchanged;
- status returns only present/missing/unavailable;
- delete returns bounded deleted/missing/unavailable semantics;
- backend errors are bounded and raw error text is not surfaced;
- no OpenAI/provider validation occurs;
- no commercial activation state is changed;
- no secret is persisted outside the existing keyring backend.

## Validation

User-reported validation:

`python -m pytest test/test_credential_cli.py test/test_credentials.py`
- 19 passed

`python -m pytest`
- 596 passed
- 2 skipped

Commit diff contains only the five approved Scope Lock files.

## Result

**ACCEPTED.**

Proceed to Phase 6D only after resolving the synthetic-only authorization boundary.
