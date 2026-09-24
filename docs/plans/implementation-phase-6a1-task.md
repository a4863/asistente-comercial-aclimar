# Phase 6A1 Implementation Task — Windows Single-Instance Lock Primitive

**Status:** APPROVED FOR IMPLEMENT
**Date:** 2026-09-24
**Plan:** docs/plans/implementation-phase-6-plan.md
**Decisions:** docs/plans/phase-6-activation-decisions.md
**Analysis:** docs/plans/phase-6-single-instance-analysis.md

## Objective

Implement and test the Windows-only single-instance lock primitive that will later provide exclusive operational ownership for the assistant.

This task implements only the lock primitive. It must not wire the lock into application startup, recovery, routes, AI composition or provider calls.

## Exact Scope Lock

Create only:

1. app/security/single_instance.py
2. test/test_single_instance.py

No other tracked file may change.

## Required behavior

Implement a small ownership object/API that:

- accepts or derives identity from a SQLite database URL/path supplied by the caller;
- supports only local file-backed SQLite identities suitable for the approved operational design;
- canonicalizes to one deterministic absolute Windows filesystem identity;
- rejects:
  - non-SQLite URLs;
  - in-memory SQLite;
  - unsupported URI/ambiguous forms;
  - paths that cannot be safely canonicalized;
  - unsuitable/nonlocal storage if this can be established safely;
- derives a deterministic sidecar lock-file path from that canonical DB identity;
- acquires an **exclusive Windows file handle with no sharing** using Win32 APIs through stdlib/ctypes;
- creates/opens the sidecar without treating file existence as ownership;
- makes the handle non-inheritable;
- holds the live handle strongly for the lifetime of the ownership object;
- provides an explicit ownership predicate that is based on a valid held handle, not PID/text/file existence;
- releases exactly once and is safe/idempotent on repeated close;
- fails closed with bounded local error codes/messages;
- never exposes raw Win32 error text containing sensitive paths beyond what is necessary for local safe diagnostics.

No PID file, heartbeat, lease, mutex, SQLite row or new dependency.

## Windows API contract

Use the approved CreateFileW-style exclusive-handle design with zero sharing.

The implementation must not:
- delete/unlink a sidecar merely because acquisition failed;
- use file existence as ownership proof;
- silently fall back to an unlocked mode;
- use port number, PID or current working directory as lock identity;
- allow handle inheritance to child processes.

If exact Win32 constants/semantics cannot be established confidently from installed Python/Windows documentation or stdlib facilities, STOP before coding.

## Canonical database identity

Tests must prove at minimum:

- the same SQLite DB referenced through equivalent relative/absolute path aliases maps to the same lock identity;
- different application ports do not affect identity;
- different DB files map to different lock identities;
- current working directory differences do not accidentally create distinct locks for the same canonical DB;
- unsupported SQLite forms fail closed.

Do not mutate or open the application SQLite database itself in this task except if a synthetic temporary file is needed solely to establish canonical path identity.

## Concurrency/subprocess tests

Use synthetic temporary paths only.

On Windows, tests must prove:

1. first process/owner acquires the lock;
2. a second process cannot acquire the same lock while first holds it;
3. second process can acquire after normal release;
4. forced process termination eventually allows reacquisition without deleting the sidecar;
5. stale sidecar filename alone does not block acquisition;
6. different DB identities can be locked independently;
7. ownership remains valid across thread changes within the same process;
8. handle is non-inheritable;
9. repeated close is safe;
10. acquisition failure never reports success.

Subprocess tests must use bounded timeouts and must not hang the test suite.

On non-Windows:
- tests may skip cleanly;
- production API must fail closed rather than pretending ownership exists.

## Security / logging

No provider calls.
No credentials.
No real production paths.
No network.

Do not log:
- secrets;
- environment contents;
- arbitrary raw OS exception bodies.

The sidecar path itself is not a secret, but errors should remain bounded and deterministic.

## Restrictions

- no app/main.py change;
- no startup/lifespan wiring;
- no repository/model/migration change;
- no OpenAI adapter change;
- no routes/templates/config changes;
- no pyproject/dependency change;
- no real keyring/provider/database data;
- no docs edits;
- no activation.

## Validation

Run:

python -m pytest test/test_single_instance.py

Then:

python -m pytest

Also run:

git diff --name-only
git diff --check

Tracked diff must contain exactly:
- app/security/single_instance.py
- test/test_single_instance.py

## STOP conditions

STOP if:
- another production/test file is required;
- a third-party dependency appears necessary;
- safe canonicalization cannot be implemented for the supported SQLite forms;
- Windows exclusive-handle ownership cannot be demonstrated with bounded subprocess tests;
- implementation would need startup/recovery/provider wiring.

## Completion

Commit:

Implement phase 6A1 Windows single-instance lock

Push only origin/codex-work.
