# Phase 6A1 Correction Task — Allow Safe Pre-Creation SQLite Identity

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-24
**Parent implementation:** ea934834fe0f272ef9e37ceb5bd262738f1fbd76
**Parent task:** docs/plans/implementation-phase-6a1-task.md

## Finding

Static review found one integration blocker.

The current lock canonicalizer requires the SQLite database file itself to already exist because it uses strict resolution/stat on the DB file.

That conflicts with the planned 6A2 startup lifecycle and with existing startup usage where a valid local SQLite URL may point to a database file that has not yet been created.

The single-instance identity must be derivable safely from the intended local SQLite path before the DB file exists.

## Exact Scope Lock

Modify only:

1. app/security/single_instance.py
2. test/test_single_instance.py

No other tracked file may change.

## Required correction

Support a valid, not-yet-existing local SQLite database file while preserving fail-closed canonical identity.

For a missing DB file:

- canonicalize/resolve the parent directory safely;
- require the parent directory to exist and be a supported fixed local Windows filesystem location;
- derive the final DB identity from the canonical parent plus the intended filename;
- reject ambiguous/device/UNC/network/URI/in-memory/non-SQLite forms exactly as before;
- do not create/open the SQLite DB merely to determine identity;
- the sidecar lock file may be created/opened as required by the lock primitive.

For an existing DB file:

- preserve existing regular-file/safe-storage checks;
- preserve alias collapse and deterministic identity.

Do not silently create missing parent directories.

## Tests

Update/add tests proving:

1. `sqlite:///missing.db` is accepted when its parent exists and maps to a deterministic canonical identity;
2. lock acquisition works before the DB file exists;
3. two processes using that same missing DB identity still conflict on the sidecar lock;
4. equivalent relative/absolute references to the same missing DB path map to the same identity;
5. after the SQLite file later appears at that path, identity/sidecar remain unchanged;
6. missing/nonexistent parent directory fails closed;
7. all previous unsupported URL/storage/device cases remain rejected;
8. existing-file behavior and subprocess release/reacquisition tests remain green.

## Restrictions

- no startup/main change;
- no DB creation as part of identity resolution;
- no repository/model/migration change;
- no dependency change;
- no OpenAI/provider/credential work;
- no unrelated refactor.

## Validation

Run:

python -m pytest test/test_single_instance.py

Then:

python -m pytest

Also:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/security/single_instance.py
- test/test_single_instance.py

## Completion

Commit:

Fix phase 6A1 pre-creation SQLite lock identity

Push only origin/codex-work.
