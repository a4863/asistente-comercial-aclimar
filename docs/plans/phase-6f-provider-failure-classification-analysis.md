# Phase 6F — provider-failure classification analysis

**Result: READY FOR PLAN — analysis only.** No provider call, keyring/config/database access, test execution or code change occurred. A later plan and explicit approval are required before implementation; another live smoke requires separate authorization.

## 1. Objective

Determine the smallest safe, offline-verifiable refinement of the OpenAI adapter's `provider_failure` category so a future synthetic smoke can distinguish coarse HTTP client failures from failures without an HTTP status, without exposing provider messages, bodies or other sensitive values.

## 2. Context and interpretation

The second authorized live synthetic smoke returned `smoke_failed:provider_failure`. That is evidence only that the current catch-all branch was reached. It does **not** identify a request parameter, model entitlement, schema, endpoint, credential or account problem. This analysis classifies paths visible in source and official documentation; it does not troubleshoot the live account or authorize a config/request change.

## 3. Documentation and evidence consulted

- `AGENTS.md`; `docs/plans/phase-6f-provider-failure-classification-analysis-task.md`; `docs/plans/phase-6f-smoke-diagnostic-analysis.md`; `docs/plans/phase-6f-smoke-diagnostic-plan.md`; `docs/security.md`; `docs/testing-strategy.md`; relevant credential/AI clauses of `docs/functional-spec.md` and adapter boundaries of `docs/architecture.md`.
- `app/integrations/openai_analysis.py`, `app/integrations/ai_smoke_cli.py`, `test/test_openai_analysis.py`, `test/test_ai_smoke_cli.py`, `pyproject.toml` (`openai==3.17.0`). The locally installed SDK's `_exceptions.py` and `_client.py` were read as source files only; no SDK client was instantiated.
- Official OpenAI documentation: [Error codes and Python library error types](https://developers.openai.com/api/docs/guides/error-codes), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), and [`gpt-6-sol` model](https://developers.openai.com/api/docs/models/gpt-6-sol). These pages document the broad SDK classes, `text.format` strict JSON schema for Responses, and model support for Responses/Structured Outputs. They do not establish this account's access or the cause of the observed failure.

No relevant required document was missing. The live provider error body/message and HTTP status were intentionally not collected or inspected.

## 4. Exact current fallthrough

Inside `OpenAIAnalysis._execute`, the `try` around `client.responses.create(...)` also evaluates `response_schema()`. Its `except Exception as error` checks, in order: `APITimeoutError` → `timeout`; `APIConnectionError` → `provider_transient_exhausted`; `RateLimitError` or status 429 → quota or transient; status 401/403 or `AuthenticationError` → `provider_auth`; status 402 → `provider_quota`; integer status 500–599 → transient; **anything else** → `provider_failure`, with no retry. Client construction/import errors are outside this catch and already become `provider_unavailable`; response `incomplete`, refusal, invalid shape/JSON and decoder errors occur after a successful call and already have separate categories.

| Error raised during create expression | Current category | Basis |
| --- | --- | --- |
| SDK `BadRequestError`, HTTP 400 | `provider_failure` | Not covered by earlier conditions. A 400 may reflect different request/entitlement/policy issues; status alone cannot identify the precise field. |
| SDK `NotFoundError`, HTTP 404 | `provider_failure` | No 404 branch. It does not by itself prove the model ID or endpoint is wrong. |
| SDK `ConflictError`, HTTP 409 | `provider_failure` | No 409 branch. |
| SDK `UnprocessableEntityError`, HTTP 422 | `provider_failure` | No 422 branch. |
| Other `APIStatusError` with 4xx except 401/402/403/429 (for example 405, 408, 410, 413) | `provider_failure` | Generic fallthrough; current code does not treat 408 as `timeout`. |
| SDK-local `TypeError`/`ValueError` or another non-HTTP exception during `responses.create(...)` argument evaluation/client call; failure in `response_schema()` | `provider_failure` | Same broad `except`; there may be no `status_code`. Cannot attribute all such errors specifically to SDK request construction. |
| `APIResponseValidationError` or another SDK exception not covered above | Usually `provider_failure` unless its `status_code` matches an existing branch | The typed HTTP-status condition is not currently required; classification depends on attributes. |
| Unknown/malformed status, or unusual status outside mapped ranges | `provider_failure` | Safe generic fallback. |

The pinned SDK source defines `BadRequestError`, `NotFoundError`, `ConflictError` and `UnprocessableEntityError` as `APIStatusError` subclasses with 400/404/409/422 respectively, and maps those response statuses to the classes. The official error guide describes these classes, including that 400 is a broad malformed/invalid-request category. The current adapter test explicitly expects `APIStatusError(400)` to yield `provider_failure`, confirming the branch. Existing fake SDK tests model timeout, connection, auth, quota and 429/5xx, but do not yet cover 404/409/422 or non-HTTP local failures.

## 5. Recommended bounded classification

Preserve all existing branches and retry/transient decisions. Add **status-only** classification for verified `openai.APIStatusError` instances after the existing 5xx branch, before the catch-all; do not inspect `error.message`, `str(error)`, body, `param`, request, URL, headers or provider `error.code` for this refinement. Require a real integer status (`type(status) is int`), not bool or a string.

| Verified HTTP status | Proposed fixed code | Meaning and limit |
| --- | --- | --- |
| 400 | `provider_bad_request` | HTTP request rejected; not a diagnosis of model/schema/parameter. |
| 404 | `provider_not_found` | Requested API resource not found; not proof that `gpt-6-sol` is unavailable. |
| 409 | `provider_conflict` | HTTP conflict, without claiming the conflicting resource. |
| 422 | `provider_unprocessable` | HTTP unprocessable request, without exposing validation details. |
| Other unmapped 4xx (400–499 excluding already-handled 401/402/403/429) | `provider_client_error` | Generic client-side HTTP status; includes 408 without changing retry policy. |

For a non-`APIStatusError` exception remaining after the existing typed timeout/connection branches, propose `provider_non_http_failure`, meaning only “no verified HTTP status classification in this call path.” It can include SDK-local validation, `TypeError`, local schema construction, or response validation; it must **not** be presented as proof of a specific SDK bug or parameter defect. Retain `provider_failure` for unexpected/malformed typed HTTP statuses that cannot be safely bucketed. This separates HTTP from non-HTTP without consulting raw content. Do not use SDK class names or provider-supplied strings as output codes.

An untyped exception with a forged `status_code=400` must **not** become `provider_bad_request`; it belongs in the non-HTTP bucket. Existing special branches remain as they are for this scope. All new categories remain non-transient with the existing one-call behavior; this task must not add retries or alter the 60-second deadline.

## 6. CLI consequence and proposed Scope Lock

The CLI currently prints `smoke_failed:<code>` only for its literal twelve-code allowlist. If only the adapter changes, all new codes collapse to `smoke_failed`, defeating the stated diagnostic purpose. A future correction therefore needs **four files, no fewer**:

**IN SCOPE (proposed future implementation):**

1. `app/integrations/openai_analysis.py` — classification only inside the existing exception handler.
2. `test/test_openai_analysis.py` — fake SDK status and non-HTTP tests, plus no-leak/retry assertions.
3. `app/integrations/ai_smoke_cli.py` — add exactly the six fixed codes above to its existing immutable allowlist; preserve unknown-code fallback.
4. `test/test_ai_smoke_cli.py` — verify each new bounded stdout value and generic fallback.

**OUT OF SCOPE:** model, endpoint, schema/decoder, Structured Outputs contract, input/payload, timeout, retries, SDK version/dependencies, credentials/keyring, config, gate, routes/UI, persistence, logging/telemetry and any live smoke.

**RESTRICTIONS:** do not widen the CLI to raw HTTP status, `error.code`, body/message or SDK metadata; no global error-handling refactor; no data-model or commercial contract change. If a future task approves fewer than four files, the adapter could be improved internally, but the live smoke would not gain the promised categories and must not be represented as diagnostically complete.

## 7. Offline test matrix and acceptance

All tests use fake SDK classes/statuses, fake credentials, fake ownership/gate and fake provider responses; no real provider, keyring, operational config or SQLite. Extend the current fake SDK namespace with the `APIStatusError` class so typed-status checks can be tested without importing the real client.

1. HTTP 400, 404, 409 and 422 → exact proposed code, one attempt, no retry; test both generic `APIStatusError` with a status and the corresponding fake subclasses when useful.
2. Other verified 4xx (for example 405, 408, 410, 413) → `provider_client_error`, one attempt; 401/402/403/429 retain current categories and retry counts; 5xx, timeout and connection remain unchanged.
3. `TypeError`, `ValueError`, synthetic schema-construction error, and non-status exception with forged `status_code=400` → `provider_non_http_failure`, one attempt. Malformed typed status retains `provider_failure`.
4. Inject raw synthetic secret, provider body, URL/path, newline/control text into exception message/body/code/headers. Assert only fixed `OpenAIAnalysisError.code` is surfaced; no raw value in exception string, CLI stdout/stderr or captured logs. Do not log or print the SDK exception.
5. CLI fake adapter for each six new codes → exact `smoke_failed:<code>\n`, exit 1, empty stderr and released lock. Unknown/non-string/unhashable codes still → `smoke_failed\n`. Existing `passed`, `disabled`, `lock_unavailable`, `unavailable`, help and invalid-command outputs remain unchanged; gate is never read or enabled by the smoke CLI.
6. Run `python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py`, then `python -m pytest`; verify `git diff --name-only` contains only the four approved files and `git diff --check` is clean.

Acceptance is classification based solely on trusted SDK exception type plus numeric status, no raw leakage, no request/config/gate/retry change, all offline tests green, and exact Scope Lock. No test needs a live call.

## 8. Dependencies, risks, ambiguities and STOP conditions

Dependencies are the already pinned OpenAI Python SDK, existing adapter/CLI and pytest fakes; no new package or migration is required. The chief risk is falsely treating a status as a precise cause: a 400 or 404 alone does not prove which field, model, policy or account permission failed. Another risk is reflecting provider-controlled error data through a new code; fixed literals and the CLI's allowlist prevent that. Keep provider output as untrusted data, never as instructions.

**Ambiguities requiring a decision:** None for an implementation plan that adopts the bounded vocabulary above. The result is a recommendation for approval, not a unilateral implementation decision. If stakeholders need finer root-cause distinctions such as “unsupported schema” versus “model access,” status-only classification cannot safely provide them; **STOP** and request a separate policy/diagnostic decision rather than exposing raw bodies/messages.

**Other STOP conditions:** no trustworthy typed HTTP status; SDK behavior differs from the pinned version in a way that invalidates the mapping; a third-party exception would be misrepresented as an HTTP status; a fifth file or dependency would be required; tests need real credentials/network; or any raw provider content would be required for the requested diagnostic.

**Out-of-scope discovery:** Current official OpenAI documentation lists several current 429 credit/spend/usage-limit codes beyond `_QUOTA_CODES`; the adapter may classify those as retryable transient. That is a separate quota/retry-policy issue and **must not** be changed under this task's no-retry-change restriction. The historical `docs/architecture.md` wording about provider selection also remains outside scope.

## 9. Verdict

**READY FOR PLAN.** A four-file, status-only and non-HTTP bounded refinement is feasible offline. The observed `provider_failure` remains unexplained until a separately approved future live attempt yields one of the new categories; no model, endpoint, Structured Outputs, timeout, retry, payload or gate change is justified by current evidence.
