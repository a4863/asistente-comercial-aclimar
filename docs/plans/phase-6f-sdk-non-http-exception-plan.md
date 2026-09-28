# Phase 6F — SDK non-HTTP exception classification plan

**Status: READY FOR IMPLEMENT — planning only.** This document does not authorize a live smoke, provider call, or commercial AI activation.

## Objective, authority, and current boundary

Refine only the adapter's remaining `provider_non_http_failure` fallback into five fixed exception-class diagnostics, without claiming a pre-dispatch or post-dispatch location. Authority: `docs/plans/phase-6f-sdk-non-http-exception-plan-task.md`, the accepted `docs/plans/phase-6f-sdk-non-http-exception-analysis.md`, dashboard evidence in `docs/plans/phase-6f-api-dashboard-evidence.md`, and the current adapter/CLI and offline tests. This plan uses the reproducible local SDK evidence, not public-web documentation or a sixth live attempt.

The production adapter already separates local schema/kwargs construction (`request_schema_failure`) from the SDK `client.responses.create(**request_kwargs)` call. Its handler classifies timeout, connection, quota/rate, auth, verified HTTP statuses, and anomalous `APIStatusError`; only the final `else` maps to `provider_non_http_failure`. That call boundary and every existing branch remain intact. The installed operational stack is Python 3.13.7, `openai==3.17.0`, `httpx2==2.13.1`; the analysis found no broken dependency requirement. Dashboard `Last used: Never` after five attempts favors a local/intermediary investigation but does not prove where the exception arose or justify changing request parameters.

## Exact mapping and precedence

Inside the existing `except Exception as error` for **only** `client.responses.create(**request_kwargs)`, preserve the current status derivation (`status_code` is trusted only for `openai.APIStatusError` with exact integer type) and every existing classifier in its current order. In particular, `APITimeoutError` remains before `APIConnectionError`, followed by existing 429/quota, auth, 402, 5xx, 400/404/409/422, other 4xx, and anomalous `APIStatusError` paths. Do not move, rewrite, or change their transient flags, retry counts, delay, deadline, or `_provider_code` use. Insert the following **after** the existing anomalous-`APIStatusError` branch and **before** the current final fallback:

| First matching exact class | Fixed category | Transient / attempts | Meaning limit |
| --- | --- | --- | --- |
| `type(error) is openai.APIResponseValidationError` | `provider_response_validation_failure` | `False`; one adapter attempt | SDK response-model validation class only; not proof of provider versus intermediary content. |
| `type(error) is json.JSONDecodeError` | `provider_response_json_failure` | `False`; one attempt | SDK-call JSON-decode class only; do not disclose the malformed content or claim origin. |
| `type(error) is TypeError` | `provider_sdk_type_failure` | `False`; one attempt | Exact plain type failure somewhere in the SDK call; no dispatch-stage claim. |
| `type(error) is ValueError` | `provider_sdk_value_failure` | `False`; one attempt | Exact plain value failure somewhere in the SDK call; no dispatch-stage claim. |
| `type(error) is RuntimeError` | `provider_sdk_runtime_failure` | `False`; one attempt | Exact plain runtime failure somewhere in the SDK call; no dispatch-stage claim. |
| Everything else not caught above | existing `provider_non_http_failure` | `False`; one attempt | Generic bounded non-HTTP fallback, including custom subclasses and other SDK/transport exceptions. |

**The JSON check must precede the ValueError check.** `json.JSONDecodeError` subclasses `ValueError`; this ordering is an explicit contract even though exact-type checks also prevent accidental capture in the current design. Use exact `type(error) is ...` for **all five** new categories. This implements the task's requirement that unapproved subclasses/custom exceptions remain in the generic fallback. No `isinstance(error, ValueError)`/`TypeError`/`RuntimeError`, class-name reflection, `str`/`repr`, attribute probing, provider code/body inspection, or status inference is permitted for these categories. The installed SDK exposes `openai.APIResponseValidationError`; `json` is already imported in the adapter, so no dependency or extra file is needed.

The existing fixed `request_schema_failure` is unchanged and remains outside this SDK-call handler. Likewise, a successful SDK return followed by `_structured_text`/response decoding still uses the existing incomplete/refusal/`invalid_output` handling; do not reclassify it as an SDK exception. Ordinary DNS/TLS/proxy/timeout exceptions already translated to `APIConnectionError` or `APITimeoutError` keep their existing categories and retry behavior.

## CLI output contract

Add exactly these five literals to the CLI's existing private `_DIAGNOSTIC_CODES` allowlist: `provider_response_validation_failure`, `provider_response_json_failure`, `provider_sdk_type_failure`, `provider_sdk_value_failure`, and `provider_sdk_runtime_failure`. Each produces exactly one stdout line `smoke_failed:<literal>\n`, empty stderr, and exit code 1. Keep `provider_non_http_failure` and `request_schema_failure` allowlisted. Keep `type(code) is str` before membership; unknown, internal, non-string, and unhashable codes remain exactly `smoke_failed\n`/1. Preserve `passed`, `disabled`, `lock_unavailable`, `unavailable`, help, invalid-command, and lock-release behavior. The CLI must not interpolate arbitrary error codes or expose Python class names from exception objects.

## Exact Scope Lock and implementation order

**IN SCOPE — exactly four tracked files:**

1. `test/test_openai_analysis.py`: extend the fake `openai` namespace with a synthetic `APIResponseValidationError` class; add fixed-code, exact-type/subclass-fallback, one-attempt/no-retry, no-leak, and pinned-SDK no-send tests below. Adjust the existing exact plain `TypeError`/`ValueError` expectations; do not weaken existing coverage.
2. `app/integrations/openai_analysis.py`: insert only the ordered fixed-class branches before the final non-HTTP fallback, with `transient=False`. Preserve all earlier branches and SDK-call arguments verbatim; use the existing `_raise(category)` pathway.
3. `app/integrations/ai_smoke_cli.py`: add only the five fixed literal codes to `_DIAGNOSTIC_CODES`; no flow or formatting changes.
4. `test/test_ai_smoke_cli.py`: add the five codes to the allowed matrix, assert bounded exact outputs, and retain unknown/non-string/unhashable fallback and preflight/security regressions.

**OUT OF SCOPE:** every other tracked file, model, endpoint, Responses API usage, Structured Outputs schema, synthetic/commercial payload, max output tokens, timeout, retry policy, SDK/dependencies, keyring, operational config/SQLite, gate, routes/UI, persistence, migration, logs/telemetry, or transport instrumentation. **RESTRICTIONS:** no fifth file, real key, provider call, smoke live, network dispatch, raw error text/body/request/URL/header/secret, or pre-/post-dispatch claim. If any becomes necessary, **STOP** instead of expanding this plan.

## Offline/no-network test matrix

1. Fake-client adapter cases for each of the five **exact** classes, injecting synthetic secret/body/path/control-text in the exception message. Expect the matching fixed `OpenAIAnalysisError.code`, exactly one `responses.create` call, zero retry/sleep, released request lock, no raw value in exception string/representation, captured stdout/stderr, or logs. `json.JSONDecodeError` must yield the JSON code rather than the ValueError code. Construct it with synthetic `msg`, `doc`, and `pos`; never print the document.
2. Custom subclasses of `TypeError`, `ValueError`, `RuntimeError`, `json.JSONDecodeError`, and the fake SDK validation class, plus unrelated exceptions and forged `status_code` on non-`APIStatusError`: all remain `provider_non_http_failure`, one attempt, no leak. Keep the existing malformed typed-status fallback at `provider_failure`.
3. Pinned real SDK with synthetic API key and explicit `httpx2.MockTransport`/no-send transport: malformed in-process JSON 200 must reach the JSON class; a deliberately strict **test-only** client with malformed in-process response must reach the validation class; an injected pre-send `build_request` exact `TypeError` must produce the type category with zero mock dispatch; in-process exact `ValueError` and `RuntimeError` transport doubles must yield their fixed classes. No default network transport, real keyring, operational TOML/SQLite, or provider endpoint call. Strict mode is solely a test construction and must not alter production client configuration.
4. Preserve SDK connection/timeout/proxy mock behavior (`httpx2.RequestError`/`TimeoutException` subclasses → existing connection/timeout categories), HTTP/auth/quota mappings, existing retry counts and reauthorization, `request_schema_failure`, refusal/incomplete/invalid-output handling, and identical request kwargs. A type subclass must not bypass the generic fallback by virtue of `isinstance`.
5. CLI fake-adapter matrix for all five new codes: exact `smoke_failed:<code>\n`, empty stderr, exit 1, lock released. Keep generic fallback for unknown/non-string/unhashable values and all success/help/disabled/lock/unavailable paths; no gate activation or commercial data.

Run `python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py`, then `python -m pytest`, then `git diff --name-only` and `git diff --check`. The tracked diff must contain **only** the four Scope-Locked files. All tests are offline. No live smoke is part of implementation acceptance.

## Security, risks, rollback, and verdict

Output codes are fixed local literals identifying an exception **class**, not root cause, provider response origin, or network stage. In particular, a JSON decode failure does not prove provider JSON was malformed; an intermediary might have supplied it. The dashboard may lag. Raw exception text, causes, traceback details, request data, SDK/provider bodies, headers, and secrets remain untrusted and must never enter the adapter error or CLI output. Existing ownership, one-shot smoke, and commercial gate boundaries remain unchanged; Global/Standard Retention does not authorize commercial AI use.

If the later four-file implementation fails validation, revert that diagnostic change as one unit and retain the previous generic `provider_non_http_failure` behavior. Do not repair a failure by changing dependencies, request parameters, retries, transport, or gate within this Scope Lock. A sixth live attempt needs a separate explicit authorization after offline acceptance.

**Verdict: READY FOR IMPLEMENT**, subject to explicit approval of this exact four-file plan. No unresolved design choice is required for this class-only refinement. **STOP** if implementation requires a fifth file, raw content, live access, dependency changes, or a pre-/post-dispatch distinction.
