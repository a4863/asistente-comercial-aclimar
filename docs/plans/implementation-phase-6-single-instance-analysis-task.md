# Phase 6 Single-Instance Ownership Analysis Task

**Status:** APPROVED FOR ANALYSIS ONLY
**Date:** 2026-09-24
**Decision:** D12 in docs/plans/phase-6-activation-decisions.md

## Objective

Determine whether a single-instance operational lock can safely establish exclusive ownership of the assistant's analysis capability on Windows under the project's actual Uvicorn startup patterns, including development reload mode.

This is analysis only.

## Questions to answer

1. How is the app currently started in development and intended to be started in normal local operation?
2. Under Uvicorn without reload:
   - which process imports the module;
   - which process should own the lock;
   - when can the lock be acquired and released safely?
3. Under Uvicorn with `--reload` on Windows:
   - parent/reloader process vs child worker process;
   - which process imports `app.main`;
   - whether workers are restarted while the parent remains alive;
   - whether a process lifetime lock can remain unambiguously owned across reloads.
4. Which locking primitive is smallest and safest for this repository on Windows?
   Consider only mechanisms that do not require a new third-party dependency unless absolutely necessary.
5. Can the design guarantee:
   - exactly one operational owner;
   - second instance fails closed;
   - no provider call without lock ownership;
   - lock release on clean shutdown;
   - lock release after abnormal process exit;
   - safe reacquisition after restart;
   - startup recovery of inherited `reserved` runs only after ownership acquisition?
6. Can this be tested offline/reliably in pytest on Windows?
7. Does reload mode need to be explicitly unsupported for operational AI mode while remaining acceptable for development?
8. What is the exact smallest future Scope Lock if viable?
9. If not viable, STOP and recommend the minimum persistent ownership alternative.

## Candidate approaches to evaluate

At minimum evaluate:
- Windows named mutex;
- exclusive lock file / file handle semantics available in stdlib/Windows;
- any existing project/process mechanism already present.

Do not add a dependency merely for convenience.

## Required deliverable

Create only:

`docs/plans/phase-6-single-instance-analysis.md`

The document must include:
- repository startup findings;
- Windows/Uvicorn process model findings;
- evaluated lock options;
- recommended mechanism;
- reload-mode policy;
- lifecycle/acquisition/release sequence;
- startup recovery ordering;
- tests required;
- exact candidate implementation files;
- decision: READY FOR PLAN or STOP.

## Restrictions

READ-ONLY analysis.

Do not:
- modify production code;
- modify tests;
- add dependencies;
- create lock files;
- launch real Uvicorn processes if not required by repository inspection;
- call OpenAI;
- inspect credentials;
- modify the database;
- change docs/architecture.md.

If factual behavior of current Uvicorn/Windows reload internals is material and cannot be established from installed/source documentation available locally, document the uncertainty and STOP rather than guessing.

## Completion

Create only:
`docs/plans/phase-6-single-instance-analysis.md`

Commit:
`Analyze phase 6 single-instance ownership`

Push only to `origin/codex-work`.
