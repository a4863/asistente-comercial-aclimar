# Phase 6F — bounded unknown non-HTTP exception families

**Status: READY FOR IMPLEMENT — plan only.** No code, test, dependency, configuration, credential, gate, or external system has been changed. No provider call or live smoke is authorized by this plan.

## Objective, authority, and evidence boundary

Refine only the existing `provider_non_http_failure` branch reached from `client.responses.create(**request_kwargs)` into six fixed, bounded family codes. Authority: `docs/plans/phase-6f-unknown-non-http-family-plan-task.md` and the approved `docs/plans/phase-6f-unknown-non-http-family-analysis.md`. Consulted the current adapter/CLI/tests, `AGENTS.md`, `docs/security.md`, and `docs/testing-strategy.md`. The sixth live smoke returned the generic code; no evidence identifies its actual exception, network stage, or origin. The installed runtime evidence is Python 3.13.7, `openai==3.17.0`, and `httpx2==2.13.1`; `httpx2` is already installed and imported by existing offline tests. No package or version change is required.

The current adapter handles timeout, connection, 429/quota, auth, 402, 5xx, selected 4xx, other 4xx, and anomalous `APIStatusError` first, then exact `APIResponseValidationError`, `JSONDecodeError`, `TypeError`, `ValueError`, and `RuntimeError`. Those branches, their order, their codes, and their retry/deadline semantics are immutable here. Local `request_schema_failure`, client-construction `provider_unavailable`, and post-return decoding are outside this classifier and remain unchanged.

## Exact ordered mapping

Insert the six branches **only after** the existing exact `RuntimeError` branch and **before** the final generic `else`, preserving every earlier line of classification. Each new branch assigns `(category, transient) = (<fixed literal>, False)`. Thus each new family exits after one adapter attempt, with no retry or sleep. Existing `OpenAIAnalysisError` and CLI bounded-output pathways remain in use.

| Precedence after existing branches | Exact condition | Fixed category | Explicit limit |
| --- | --- | --- | --- |
| 1 | `isinstance(error, openai.OpenAIError)` | `provider_openai_error_family` | Residual SDK family only; prior status/timeout/connection and exact SDK-validation cases win. Do not infer a provider response. |
| 2 | `isinstance(error, httpx2.RequestError)` | `provider_http_client_error_family` | Residual HTTP-client request family only. **Do not** check broad `httpx2.HTTPError`, which also includes `HTTPStatusError`. |
| 3 | `isinstance(error, OSError)` | `provider_os_error_family` | Includes `ssl.SSLError` and `SSLCertVerificationError`; does not identify DNS, TLS, proxy, firewall, or dispatch stage. |
| 4 | `isinstance(error, ValueError)` | `provider_value_subclass_family` | Only residual subclasses because exact `JSONDecodeError` and exact `ValueError` have already returned their dedicated codes. Includes Unicode and Pydantic validation subclasses without importing Pydantic in production. A custom `JSONDecodeError` subclass lands here, not in the exact JSON branch. |
| 5 | `isinstance(error, (TypeError, RuntimeError, AttributeError, LookupError, AssertionError))` | `provider_python_internal_family` | This tuple is exhaustive and must not be broadened. Exact `TypeError`/`RuntimeError` already have dedicated codes; `KeyError`/`IndexError` enter through `LookupError`. No generic Python-exception catch. |
| 6 | `isinstance(error, ExceptionGroup)` | `provider_exception_group_family` | Check the outer group only; never inspect its members. Do not catch `BaseExceptionGroup` or `BaseException`. |
| 7 | final `else` | existing `provider_non_http_failure` | Raw `httpcore2` exceptions, `httpx2.HTTPStatusError` not translated by the SDK, unrelated custom `Exception`, and all other residual cases remain generic. |

Precedence before the table remains, exactly: existing timeout/connection/HTTP/auth/quota branches; anomalous `APIStatusError -> provider_failure`; exact `APIResponseValidationError`; exact `JSONDecodeError`; exact `TypeError`; exact `ValueError`; exact `RuntimeError`. The JSON check must remain before ValueError. `APITimeoutError` must remain before `APIConnectionError`. The family conditions use `isinstance` only on **approved known classes**, never dynamic class-name/module/MRO reflection. Specific OpenAI and HTTP-client checks precede built-ins. Ordinary `httpx2.RequestError` inside SDK send is normally wrapped as `APIConnectionError` and retains the existing retry policy; the new HTTP-client code applies only if an unwrapped request error reaches this handler. `httpcore2` is not imported or checked in production. A `BaseExceptionGroup` containing a non-`Exception` member is not caught by the present `except Exception`; the plan does not change that boundary.

Import `httpx2` alongside the existing lazy `import openai` in the adapter's existing provider-client-construction `try`, so module import and `create_app()` stay inert and the already-installed runtime requirement remains within the existing `provider_unavailable` boundary. Do not add a top-level import or change factory arguments. No Pydantic, httpcore2, SSL, keyring, or new dependency import is needed in production. If this cannot be done without a package/behavior change, STOP.

## CLI and security contract

Add **exactly** the six table literals to the private `_DIAGNOSTIC_CODES` allowlist. For each, the CLI emits one stdout line `smoke_failed:<literal>\n`, empty stderr, and exit code 1. Keep `provider_non_http_failure`, every previously approved code, and `type(code) is str` before membership. Unknown, non-string, or unhashable codes remain `smoke_failed\n`/1. Keep `passed`, `disabled`, `lock_unavailable`, `unavailable`, help, invalid-command, and lock release unchanged. Neither adapter nor CLI may print/log/derive from exception class names or modules, MRO, `str`, `repr`, `args`, cause/context, nested group members, provider bodies/messages, request text, URL/headers, or secrets. Codes identify only families, not root causes or pre-/post-dispatch timing.

## Exact Scope Lock and implementation order

**IN SCOPE — exactly four tracked files:**

1. `app/integrations/openai_analysis.py`: lazy import of already-installed `httpx2` within the existing provider-construction try; six ordered `elif` conditions above, all `transient=False`, before the unchanged generic fallback. No other adapter changes.
2. `test/test_openai_analysis.py`: adjust the synthetic fake OpenAI exception hierarchy within this file to reflect `OpenAIError`/`APIError` inheritance needed for precedence tests; add parametrized fake-client and pinned-SDK/MockTransport family, fallback, no-retry, no-leak, and unchanged-kwargs tests. Do not weaken existing assertions.
3. `app/integrations/ai_smoke_cli.py`: add only the six literal strings to `_DIAGNOSTIC_CODES`.
4. `test/test_ai_smoke_cli.py`: add the six literals to the allowlist matrix and assert exact bounded output, generic fallback, and lock lifecycle.

**OUT OF SCOPE:** every fifth tracked file, model, endpoint, Responses API, Structured Outputs schema, request/commercial or synthetic payload, output-token limit, timeout/deadline, retry/delay policy, dependency/package versions, keyring, operational TOML/SQLite, gate, ownership, routes/UI, persistence, migration, telemetry, transport instrumentation, or live access. **RESTRICTIONS:** no real key/credential, provider call, live smoke, network probe, direct httpcore2/Pydantic production dependency, dynamic exception identity/fingerprint, nested-group inspection, `BaseException` catch, or raw diagnostic content. A requirement for any of these is STOP, not a Scope Lock expansion.

Implement/test in this order: (1) build the hierarchy-correct fake and representative family/precedence tests; (2) add adapter lazy import and family branches; (3) add CLI allowlist and CLI tests; (4) run focal offline tests, then full offline suite, then inspect `git diff --name-only` and `git diff --check`. Commit/push is a separate explicitly authorized step after the implementation tests pass; this plan itself changes no production file.

## Offline/no-network acceptance matrix

- Adapter fake-client mapping: residual `OpenAIError` and `APIError` subclass; residual `httpx2.RequestError`/`ProtocolError`/`DecodingError`; raw `OSError` and SSL certificate subclass; `UnicodeError`, `UnicodeDecodeError`, a safe synthetic `ValueError` subclass (or Pydantic validation fixture without production import); `TypeError`/`RuntimeError` subclasses; `AttributeError`; `KeyError`/`IndexError` through `LookupError`; `AssertionError`; outer exact `ExceptionGroup`. All must yield the table code after one `responses.create` call, no adapter retry/sleep, and a released request lock. Synthetic error messages include secret-like strings solely to assert no output, exception-code, or log leakage.
- Fallback: raw `httpcore2.ConnectError`, raw `httpx2.HTTPStatusError` if constructible without network, unrelated custom `Exception`, and an approved-exception-family-negative case all remain `provider_non_http_failure`; no broad `HTTPError` or `Exception` family is added. Do not inspect nested `ExceptionGroup` members. Do not test `BaseException` by changing the production catch boundary.
- Regression priority: exact `APIResponseValidationError`, `JSONDecodeError`, `TypeError`, `ValueError`, `RuntimeError` retain their existing codes. An `APIResponseValidationError` subclass is residual `OpenAIError` family when using the real hierarchy; a custom JSON subclass is residual ValueError family. Preserve all existing HTTP/auth/quota/timeout/connection classes and their retry counts, `request_schema_failure`, refusal/incomplete/invalid output, reauthorization, request kwargs, and client factory arguments.
- Pinned real SDK with synthetic key and explicit `httpx2.MockTransport` plus `trust_env=False`: demonstrate that ordinary `httpx2.DecodingError` emitted during send still follows the SDK connection path; inject residual SDK/OS/Python errors with no external dispatch and compare fixed outputs. Where a test double injects an atypical raw error, label it as an injection rather than evidence of the normal transport. A pre-send build failure must show zero mock dispatch without asserting that the live failure occurred there.
- CLI fake adapter: exactly one bounded stdout line and empty stderr for each new literal; existing `passed`/`disabled`/lock/unavailable behavior and unknown/non-string/unhashable generic fallback unchanged; no commercial gate activation or real keyring/config/database access.

Execute `python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py`, then `python -m pytest`, then `git diff --name-only` and `git diff --check`. Require all tests green and exactly the four Scope-Locked paths in the tracked diff. No live smoke is an acceptance test.

## Risks, rollback, pending approval, and verdict

The sixth live result does not establish the root cause. Family diagnostics are intentionally coarse: OS does not prove TLS; Python-internal does not prove an SDK bug; residual HTTP client does not prove provider contact; a group code reveals nothing about members. Dashboard usage can lag. Output remains restricted to fixed literals. If a later, separately authorized live smoke remains generic, STOP for a new design decision rather than introducing arbitrary identity or content disclosure.

Rollback of a future implementation is a single four-file diagnostic change restoring the preceding generic fallback and CLI allowlist; do not compensate by changing dependencies, request parameters, transport, retries, or the gate. No functional or architectural ambiguity blocks this **plan**. Implementation requires explicit approval of this exact Scope Lock and code list; a future live attempt requires separate authorization.

**READY FOR IMPLEMENT.**
