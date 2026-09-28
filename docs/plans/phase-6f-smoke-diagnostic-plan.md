# Phase 6F — bounded synthetic smoke diagnostic implementation plan

**Status: READY FOR IMPLEMENT — plan only.** Implementation and another live smoke require separate explicit authorization.

## Objective and authority

Make the dedicated synthetic smoke CLI report an existing, safe adapter failure category while preserving secret isolation and every other execution boundary. This plan applies `docs/plans/phase-6f-smoke-diagnostic-plan-task.md` and the accepted `docs/plans/phase-6f-smoke-diagnostic-analysis.md`. Security authority remains `docs/security.md`; offline verification follows `docs/testing-strategy.md`. The observed prior `smoke_failed` is insufficient to infer a model, endpoint, credential, retry, timeout or schema defect.

## Current state

`app/integrations/ai_smoke_cli.py` catches `OpenAIAnalysisError` but always prints `smoke_failed`. The adapter's `.code` carries fixed local categories, but its constructor accepts any value, so it is not safe to echo indiscriminately. `test/test_ai_smoke_cli.py` already fakes settings, lock, credentials and adapter, and checks bounded output, lock release, preflight and no commercial gate/database access. The CLI does not invoke commercial routes or read the gate. No code, tests, keyring, operational config, SQLite or provider were accessed during this planning task.

## Exact output contract

For an `OpenAIAnalysisError` from adapter construction or `smoke()`:

1. If and only if `type(error.code) is str` and the value is in the literal allowlist below, stdout is exactly one line `smoke_failed:<code>\n`; stderr is empty; return 1.
2. Otherwise stdout is exactly `smoke_failed\n`; stderr is empty; return 1. This includes every excluded/internal, unknown, empty, malformed, control-containing, non-string or unhashable value. The code must be type-checked **before** set membership, so an unhashable value is never hashed.
3. Do not print or log `str(error)`, `repr(error)`, its cause/traceback, provider metadata, response/request body, credential reference or value, endpoint, model or path. Do not use prefix matching or a pattern that permits future arbitrary codes.

The allowlist is exactly an immutable, module-local `frozenset[str]` of these twelve string literals, with no import from the adapter or provider SDK:

```text
credential_missing
credential_unavailable
provider_unavailable
provider_auth
provider_quota
provider_transient_exhausted
provider_failure
timeout
provider_incomplete
provider_refusal
invalid_output
invalid_configuration
```

The following known adapter codes are **not** allowlisted and therefore collapse to `smoke_failed`: `operational_ownership_required`, `commercial_activation_required`, `busy`, `smoke_already_used`, `sensitive_content`, `invalid_input`, and `disabled` when raised unexpectedly by the adapter. Any new adapter code also collapses until separately reviewed.

All other existing CLI output remains byte-for-byte unchanged: success `passed\n`/0; technical-AI preflight `disabled\n`/1; lock failure `lock_unavailable\n`/1; settings/unexpected failure `unavailable\n`/1; invalid arguments on stderr `invalid_command\n`/2; and `--help` usage on stdout/0. A non-`passed` normal return remains `smoke_failed\n`/1. Do not add a second diagnostic line or new exit code.

## Scope Lock

**IN SCOPE — exactly two files:**

1. `app/integrations/ai_smoke_cli.py`
2. `test/test_ai_smoke_cli.py`

**OUT OF SCOPE:** `app/integrations/openai_analysis.py`, schema/decoder, adapter API, model, endpoint, request payload, timeout, retries, credentials/keyring, operational configuration, single-instance lock, commercial gate, routes/UI, persistence, migrations, documentation, logging/telemetry and dependencies.

**RESTRICTIONS:** no third tracked file; no real config/keyring/SQLite; no provider/network call; no gate access or activation; no raw error data in output; no second live attempt under this plan. If any requirement needs another file, adapter change, raw provider text or a new functional decision, **STOP**.

## Per-file implementation steps

1. In `app/integrations/ai_smoke_cli.py`, declare one private module-local `frozenset` containing exactly the twelve literals above. Do not add logging, SDK inspection or provider imports.
2. Change only the `except OpenAIAnalysisError:` handler to bind `as error`, read `error.code`, apply exact-string type check followed by allowlist membership, and print either the single bounded diagnostic line or the generic fallback. Preserve exception-handler order: `SingleInstanceError` first, `OpenAIAnalysisError` second, generic `Exception` last. Preserve all other branches, existing lock context manager and return 1. A helper is unnecessary; if one is used, it must remain private, total for the tested arbitrary values, and inside the same file.
3. In `test/test_ai_smoke_cli.py`, add or adjust only fake-driven tests for the output mapping and security regressions below. Keep existing canonical-config tests isolated through their temporary fixture and fake loader; never access the real path. Do not change the adapter or its tests.

## Offline test matrix

Use `smoke_fakes`, monkeypatch and capture fixtures. Every fake adapter failure must occur while the fake lock is held, call `smoke()` once, and verify `lock_release` as the final event.

| Case | Exact assertion |
| --- | --- |
| Each of 12 allowlisted codes | Parametrize: stdout `smoke_failed:<code>\n`, empty stderr, exit 1, lock released. |
| Each excluded known code | Parametrize: stdout `smoke_failed\n`, empty stderr, exit 1, lock released. |
| Arbitrary strings | Unknown provider code, fake API key/body, path/URL, empty, newline, carriage return, tab/control and code-like prefix/suffix all collapse; no injected text in stdout/stderr/captured logs. |
| Non-string and unhashable | `None`, integer, list and dict `.code` values collapse without raising `TypeError`; do not stringify or hash them. |
| Other exceptions | Fake credential construction and adapter construction with raw secret/body text preserve `unavailable\n`/1, empty stderr, no raw text, lock released. |
| Existing success and preflight | `passed\n`/0, `disabled\n`/1, `lock_unavailable\n`/1, invalid arguments/help and normal non-`passed` return unchanged; preflight failures do not construct credentials or provider. |
| Commercial boundary | Fail the test on gate enable/disable/read and database session/engine access; the diagnostic does not add any such access. |

The existing `test/test_openai_analysis.py` fake-provider tests establish local auth, quota, transient, timeout, refusal, incomplete and invalid-output categorization; this task does not edit that file. Test fixtures must not call the real provider, keyring, operational TOML or SQLite.

Run, in order:

```text
python -m pytest test/test_ai_smoke_cli.py test/test_openai_analysis.py
python -m pytest
git diff --name-only
git diff --check
```

Before commit, verify the tracked diff contains only the two Scope-Locked files and no raw secret or response fixture data in production output. No live smoke is part of validation.

## Security invariants and acceptance

- The allowlist is the only disclosure boundary; unknown/new codes fail closed.
- No arbitrary `.code`, raw exception, SDK error, HTTP body/status detail, secret, credential reference, request/response, endpoint, model or path is echoed.
- Ownership and technical AI checks, fixed synthetic payload, one-shot adapter call and lock release remain unchanged.
- The commercial gate is never consulted or enabled; commercial analysis remains gated.
- `passed`, `disabled`, `lock_unavailable`, `unavailable`, help and invalid-command behavior is preserved.
- All focal and full offline tests pass; diff is limited to the two authorized files and passes whitespace checks.

## Rollback and release gate

If implementation or tests reveal a required third file or a leak, stop without expanding scope. The correction is an isolated two-file change and can be reverted as one commit if rejected; do not alter configuration or provider behavior to compensate. A successful offline correction does **not** authorize another live smoke: the user must separately approve a fresh one-shot execution that stops on any failure.

## Verdict

**READY FOR IMPLEMENT**, subject to explicit approval of the two-file implementation task. No new functional decision, adapter change or live access is needed for this plan.
