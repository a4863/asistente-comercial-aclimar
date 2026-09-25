# Runtime Configuration Loading Analysis Task — Precondition for Phase 6F

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-25
**Trigger:** Phase 6F preflight STOP
**Mode:** READ-ONLY

## Objective

Define the smallest safe runtime configuration-loading contract so command-line entry points and the operational application can consume approved non-secret TOML settings consistently, while preserving current fail-closed defaults and secret isolation.

Do not implement anything in this task.

## Confirmed current behavior

- `load_settings(path=None)` uses defaults and does not discover/read a TOML file.
- `asistente-aclimar-ai-smoke` calls `load_settings()`, therefore AI is always disabled unless code passes a Settings object through some other path.
- `asistente-aclimar-credential` also calls `load_settings()`.
- `app.main.run()` calls `load_settings()` when no Settings object is supplied.
- Architecture states non-secret local settings use TOML and secrets stay in keyring/Windows Credential Manager.

## Questions to resolve

1. What is the canonical local TOML path on Windows for this project?
2. Should all operational CLI/app entry points use one central discovery function?
3. Should explicit config-path CLI arguments be supported, or should one fixed local path be used?
4. How do we prevent arbitrary/untrusted path loading from weakening local-only assumptions?
5. How should missing config behave:
   - defaults,
   - bounded failure,
   - or different behavior for dev/tests vs operational commands?
6. Which settings must be explicitly present for operational AI use?
7. Confirm that API keys/tokens remain forbidden in TOML.
8. How do tests inject Settings without touching real local config?
9. Which entry points must be updated together to avoid divergent behavior:
   - `app.main.run`;
   - credential CLI;
   - smoke CLI;
   - any other console script?
10. Does the current project already document/name a config file anywhere else?
11. Can the change remain dependency-free and migration-free?
12. What exact files/tests need modification?
13. How do we prove import/create_app remains inert and does not perform filesystem/network/keyring reads unexpectedly?
14. How do we preserve fail-closed AI activation: missing/invalid config must never imply `enabled=True`.
15. How should endpoint selection be configured for the future smoke while keeping the existing endpoint allowlist authoritative?

## Preferred properties

Prefer:
- one canonical local non-secret TOML configuration file;
- one central loader/discovery helper;
- no environment-variable secret/config bypass;
- no automatic search across arbitrary directories;
- deterministic Windows/local behavior;
- explicit bounded errors;
- tests using temporary files/Settings objects;
- no provider call;
- no commercial-gate effect.

## STOP conditions

STOP if:
- implementing safe config discovery requires a new dependency;
- a secure canonical path cannot be chosen from existing project conventions;
- the change would need secret material in TOML;
- multiple incompatible runtime modes require another product decision.

## Deliverable

Create only:

`docs/plans/runtime-config-loading-analysis.md`

Include:
- current-state findings;
- candidate approaches;
- rejected approaches;
- recommended exact configuration-loading contract;
- canonical path proposal;
- entry points affected;
- exact proposed Scope Lock;
- security invariants;
- offline test matrix;
- migration/dependency impact;
- verdict: READY FOR PLAN or STOP.

No code changes.
No tests.
No OpenAI call.

Commit:

Analyze runtime configuration loading contract

Push only origin/codex-work.
