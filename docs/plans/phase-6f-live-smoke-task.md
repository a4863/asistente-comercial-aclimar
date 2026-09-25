# Phase 6F Execution Task — One-Time Live Synthetic Smoke

**Status:** APPROVED FOR ONE LIVE EXECUTION
**Date:** 2026-09-25
**Depends on:** Phase 6E3 ACCEPTED; D18 APPROVED

## Objective

Perform exactly one real OpenAI call through the already accepted synthetic smoke path.

This is an execution task, not an implementation task.

## Hard boundary

The only permitted provider payload is the fixed literal already embedded in `OpenAIAnalysis.smoke()`:

`This is a synthetic test message. Please confirm receipt of a sample catalogue request.`

No commercial data may be read or transmitted.

## Preconditions

Before running the live smoke:

1. Synchronize `codex-work`.
2. Confirm working tree has no tracked changes:
   - `git status --short --untracked-files=no`
3. Confirm current branch is `codex-work`.
4. Confirm no operational assistant instance is running and holding the single-instance lock.
5. Confirm AI technical configuration is enabled.
6. Confirm endpoint class is one of the adapter allowlisted endpoints.
7. Confirm credential status is `present` using the existing local credential CLI/status surface.
8. Confirm commercial gate remains OFF/blocked.
9. Do not modify code, tests, config, database, or credentials during this execution task.

## Execution

Run exactly once:

`asistente-aclimar-ai-smoke`

If the console script is unavailable but the package code is present, STOP rather than invent an alternate direct Python/provider call.

Do not run pytest as part of the live smoke itself.

## Expected bounded outcomes

Success:
- stdout: `passed`
- exit code: 0

Bounded failures may include:
- `disabled`
- `lock_unavailable`
- `smoke_failed`
- `unavailable`

Do not expose or paste:
- API key;
- raw provider error body;
- full HTTP request/response;
- credential metadata beyond present/missing;
- any commercial content.

## STOP rules

STOP immediately and do not retry if:
- first live invocation returns any failure;
- lock is unavailable;
- endpoint/configuration is not the intended approved configuration;
- credential is missing/unavailable;
- any unexpected commercial-data access is observed;
- command output exposes raw provider/secret data;
- execution appears to require a code/config change.

A second live invocation requires fresh explicit approval.

## Post-run evidence

Report only:
- exact command used;
- exit code;
- bounded stdout/stderr;
- whether gate remained blocked;
- whether any code/config/db files changed;
- `git status --short --untracked-files=no`

Do not include secret values or raw provider payloads.

## Completion

No commit is required for the execution itself.

If the smoke passes, Phase 6F can be formally accepted.
If it fails, Phase 6F remains unaccepted and the failure must be analyzed offline before any new live attempt.
