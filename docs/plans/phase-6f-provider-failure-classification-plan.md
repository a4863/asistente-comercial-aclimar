# Phase 6F — bounded provider-failure classification plan

**Status: READY FOR IMPLEMENT — plan only.** No code or test implementation and no live smoke are authorized by this document.

## Objective, context and authority

Refine only the OpenAI adapter's generic `provider_failure` fallthrough into fixed, coarse HTTP and non-HTTP codes, and add those fixed codes to the dedicated synthetic smoke CLI allowlist. The second live smoke yielded `smoke_failed:provider_failure`; it did not disclose a status or establish a root cause. The approved basis is `docs/plans/phase-6f-provider-failure-classification-analysis.md` and `docs/plans/phase-6f-provider-failure-classification-plan-task.md`, within `docs/security.md` and `docs/testing-strategy.md`. Official OpenAI documentation distinguishes SDK HTTP errors such as `BadRequestError`, `NotFoundError`, `ConflictError` and `UnprocessableEntityError`; it does not identify this account's observed failure ([Error codes](https://developers.openai.com/api/docs/guides/error-codes)). Responses Structured Outputs currently uses `text.format` with `json_schema`/`strict`, but this task leaves the request untouched ([Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)).

## Exact classification contract

Within the existing `except Exception as error` around the `responses.create(...)` expression, derive a **verified status** only when `isinstance(error, openai.APIStatusError)` and `type(error.status_code) is int`. A non-`APIStatusError` with a `status_code` attribute, a bool, string or other malformed status is not a verified HTTP status. Use this verified status for every status-driven branch. Existing typed SDK exception classes retain their priority. Do not read message/body/param/request/URL/headers or provider `error.code` for any **new** classification. Preserve the existing bounded `_provider_code` use solely for the current 429 quota/rate distinction; do not change that distinction or retry policy.

Apply branches in this exact order:

1. `openai.APITimeoutError` → `timeout`, transient under existing retry/deadline rules.
2. `openai.APIConnectionError` → `provider_transient_exhausted`, transient under existing rules.
3. `openai.RateLimitError` **or verified** HTTP 429 → existing `provider_quota` (recognized current quota code, non-transient) or `provider_transient_exhausted` (otherwise transient), with the existing `_provider_code` and retry-delay behavior unchanged.
4. `openai.AuthenticationError` **or verified** HTTP 401/403 → `provider_auth`, non-transient.
5. Verified HTTP 402 → `provider_quota`, non-transient.
6. Verified HTTP 500–599 → `provider_transient_exhausted`, transient under existing rules.
7. Verified HTTP 400 → `provider_bad_request`, non-transient.
8. Verified HTTP 404 → `provider_not_found`, non-transient.
9. Verified HTTP 409 → `provider_conflict`, non-transient.
10. Verified HTTP 422 → `provider_unprocessable`, non-transient.
11. Any other verified HTTP 400–499 not caught above → `provider_client_error`, non-transient. This includes 408; do not reinterpret it as an SDK timeout or add a retry.
12. A remaining `openai.APIStatusError` with missing/malformed/unclassifiable status → existing `provider_failure`, non-transient.
13. Any other remaining non-`APIStatusError` exception from the create expression/call → `provider_non_http_failure`, non-transient. This can include local schema construction, SDK-local validation, `TypeError`, `ValueError` or response validation; the name does not assert a specific root cause.

The new codes are fixed program literals, not provider-supplied strings. Status-specific names mean only that the pinned SDK supplied that HTTP status. A 400 does not prove a schema problem, and a 404 does not prove model unavailability. An `AuthenticationError` keeps its typed-class mapping even if a synthetic fake has malformed status; other status-only mappings require verified status. Retain `provider_failure` for typed HTTP anomalies. Reclassification of forged-status non-HTTP exceptions into `provider_non_http_failure` is intentional fail-closed behavior; real typed SDK HTTP mapping and retry semantics remain unchanged.

## Smoke CLI contract

Add **exactly** these six literals to the existing private immutable `_DIAGNOSTIC_CODES` allowlist in `app/integrations/ai_smoke_cli.py`:

```text
provider_bad_request
provider_not_found
provider_conflict
provider_unprocessable
provider_client_error
provider_non_http_failure
```

Each yields exactly `smoke_failed:<code>\n` on stdout, empty stderr and exit 1. Keep all existing allowlisted codes and `type(code) is str` before membership. Unknown, excluded, non-string and unhashable codes remain exactly `smoke_failed\n`/1. Preserve `passed`, `disabled`, `lock_unavailable`, `unavailable`, help, invalid-command and normal non-`passed` output and exit codes. No raw HTTP number, message, body, provider code or SDK class name is emitted.

## Exact Scope Lock

**IN SCOPE — exactly four files:**

1. `app/integrations/openai_analysis.py`
2. `test/test_openai_analysis.py`
3. `app/integrations/ai_smoke_cli.py`
4. `test/test_ai_smoke_cli.py`

**OUT OF SCOPE:** all other tracked files, model, endpoint, Responses API method, Structured Outputs schema/decoder, request payload, output-token ceiling, timeout, retry count/delay, SDK version/dependencies, keyring/credential handling, operational configuration, commercial gate, lock ownership, routes/UI, persistence, logging/telemetry and another live smoke.

**RESTRICTIONS:** no fifth file; no provider message/body/param/request/URL/header inspection for new branches; no raw data in exception text, CLI or logs; no account credential or operational config access; no OpenAI call; no change to existing 429 code interpretation despite the separate out-of-scope quota-code observation in the analysis. If a fifth file, raw provider content, new retry decision or live call is needed, **STOP**.

## Per-file implementation order

1. `test/test_openai_analysis.py`: extend the fake `openai` namespace with `APIStatusError` and fake status subclasses (or generic typed status instances), preserving the current fake isolation. Add expected-code, attempt-count and no-leak cases below. Do not import/use the real provider client.
2. `app/integrations/openai_analysis.py`: add only verified-status derivation and the ordered classification branches inside the existing create-expression exception handler. Reuse existing retry loop and `_raise`; no request argument, schema, credential, gate or deadline edit.
3. `app/integrations/ai_smoke_cli.py`: append exactly six fixed literals to `_DIAGNOSTIC_CODES`; do not change its handler, output formatting, lock lifecycle or other CLI branch.
4. `test/test_ai_smoke_cli.py`: extend the fake-adapter matrix for the six new codes and keep generic unknown/non-string/unhashable fallback and lock-release tests.

## Offline test matrix

All provider behavior is faked. Use synthetic error text/body containing an artificial secret, URL/path and newline/control characters, but never log or print these values.

| Case | Required result |
| --- | --- |
| Typed 400/404/409/422 | Exact respective fixed code; one `responses.create` attempt; no retry; no raw text in `str(OpenAIAnalysisError)` or captured logs. |
| Typed other 4xx (for example 405, 408, 410, 413) | `provider_client_error`; one attempt; 408 does not change timeout/retry behavior. |
| Typed 401/402/403/429 and 5xx | Existing auth/quota/transient categories and attempt counts unchanged, including current 429 quota-vs-rate and retry-delay cases. |
| Typed `APITimeoutError`/`APIConnectionError` | Existing timeout/transient behavior and retry count unchanged. |
| Non-HTTP `TypeError`, `ValueError`, schema-construction error and arbitrary exception with forged `status_code=400`/429/503 | `provider_non_http_failure`; one attempt; forged status cannot invoke HTTP, quota or retry branch. |
| Typed `APIStatusError` with bool/string/None/out-of-range status | `provider_failure`; one attempt; no exception from classification. |
| CLI fake adapter returns each new code as `OpenAIAnalysisError` | Exact `smoke_failed:<code>\n`, stderr empty, exit 1 and lock released. |
| CLI unknown/raw/control/non-string/unhashable code | Generic `smoke_failed\n`, empty stderr, no injection in stdout/stderr/logs. |
| Existing CLI success/preflight and gate isolation | `passed`, `disabled`, `lock_unavailable`, `unavailable`, help/invalid-command and non-`passed` unchanged; no commercial gate read/change. |

Also assert request method/arguments and fixed smoke payload are unchanged via existing adapter tests; no fake may reach network/keyring/real SQLite. Run in this order for the later implementation:

```text
python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py
python -m pytest
git diff --name-only
git diff --check
```

Before commit, confirm the tracked diff is exactly the four files above and review it fully. Passing offline tests does not authorize a live smoke.

## Security invariants, acceptance and rollback

- New output is bounded to literal categories; raw SDK text/body/code/param/request/URL/headers, secrets and commercial content never enter `OpenAIAnalysisError`, CLI stdout/stderr or logs.
- No status-only branch trusts a non-`APIStatusError` object or bool/string status; malformed typed status fails closed to the old generic code.
- Existing typed auth/quota/timeout/connection/5xx outcomes, authorization checks, retries, deadline, fixed smoke payload and commercial gate behavior remain intact.
- The CLI's generic fallback still protects unknown or attacker-controlled codes.
- All focal and full offline tests pass, exact four-file diff, clean `git diff --check`.

If implementation violates any invariant or needs a fifth file, stop and report the blocker; do not broaden the change. The eventual correction should be one isolated four-file commit, reversible as a unit if rejected. No automatic config/model/schema adjustment or additional live attempt follows this plan.

## Verdict

**READY FOR IMPLEMENT**, pending explicit approval of an implementation task with this exact four-file Scope Lock. No raw provider inspection, new dependency, or external call is required for this bounded classification.
