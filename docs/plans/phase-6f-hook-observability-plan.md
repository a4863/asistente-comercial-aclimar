# Phase 6F — hook-level Unicode observability and deterministic client closure

**Status: READY FOR IMPLEMENT — plan only.** No implementation, provider call, ninth live smoke, credential access, dependency change, or commercial-gate activation is authorized by this document.

## Objective, authority, and bounded interpretation

Add public HTTPX2 request/response hooks to the existing synchronous OpenAI adapter, record only a short-lived phase for each adapter attempt, use that phase to refine **residual Unicode** failures into fixed diagnostics, and close the one SDK client deterministically after the entire `_execute()` operation. Authority: `docs/plans/phase-6f-hook-observability-plan-task.md`, the approved `docs/plans/phase-6f-deterministic-client-close-approval.md`, and the earlier hook and Unicode-path analyses. Checked against `AGENTS.md`, `docs/security.md`, `docs/testing-strategy.md`, current adapter/CLI/tests, and locally installed `openai==3.17.0` and `httpx2==2.13.1` source. No required document is missing.

The observations mean exactly:

1. `before_request_hook`: no request hook reached in this adapter attempt;
2. `request_hook_reached`: at least one request hook ran but no response hook ran;
3. `response_hook_reached`: at least one response hook ran.

These names do **not** assert transport dispatch, provider contact, provider response origin, final-response identity, body read, JSON decode, or cause of the Unicode exception. Redirect/auth flows can run hooks multiple times within an attempt; `response_hook_reached` means **at least one** response hook ran, possibly for an intermediate exchange. The prior no-network tests reproduced all three hook states using only synthetic inputs. The installed HTTPX2 request hook precedes `_send_single_request`; the response hook follows it and precedes some body/read/SDK parsing. No transport wrapper or hook-level data inspection is permitted.

## Exact client-construction and lifetime contract

After all existing disabled, ownership/gate, configuration, data projection, request-size, and request-lock checks pass, and after credential retrieval succeeds, create one `openai.DefaultHttpxClient` with:

- the **same** approved `base_url` passed to the SDK;
- the **same initial remaining-deadline timeout value** that the adapter already passes as `timeout` to `openai.OpenAI` (calculate it once, not independently twice);
- only public synchronous `event_hooks={"request": [request_hook], "response": [response_hook]}` as additional configuration.

Pass that exact HTTP client through `http_client=` to the existing `factory = self._client_factory or openai.OpenAI`, while preserving the current `api_key`, `base_url`, `max_retries=0`, and `timeout` arguments. Do not use a plain `httpx2.Client`, specify `transport=`, change `trust_env`, `verify`, proxies, mounts, limits, follow-redirects, auth, or any SDK defaults. Source inspection showed `DefaultHttpxClient` uses the same HTTPX2 constructor/defaults as the SDK's internal sync wrapper; with `transport=None`, environment-proxy discovery and the normal transport/pool/TLS path remain selected. Supplying `base_url` and the single calculated timeout reproduces the wrapper's construction inputs. Per-request `Responses.create(timeout=remaining)` remains unchanged. No production code may access SDK/HTTPX2 private attributes.

Create **exactly one SDK client per `_execute()`**, reuse it across all adapter attempts, and invoke its public `close()` **exactly once** after the operation completes or fails, never between retries. The SDK's public `close()` closes the supplied HTTP client. The adapter must not separately close that supplied HTTP client after a successfully constructed SDK client, avoiding double close. If the HTTP client was constructed but the SDK factory raises before returning a client, close that HTTP client once and preserve the existing bounded `provider_unavailable` result; if that cleanup close also raises an ordinary `Exception`, suppress it in favor of `provider_unavailable`. If construction fails before an HTTP client exists, there is nothing to close. On any path after SDK construction—success, provider failure, exhausted retry, timeout, gate/ownership revocation during retry, invalid output, or another failure—run SDK `close()` in a `finally` that surrounds the entire remaining operation and releases the request lock independently.

**Chosen close-failure policy:** if the operation already has a primary failure, preserve it and suppress only the ordinary `Exception` thrown by `close()`; do not log or expose that exception. If the operation otherwise produced a successful result but `close()` raises an ordinary `Exception`, replace that success with `OpenAIAnalysisError("provider_client_close_failure")`. This is non-transient, generates no retry or second provider call, and must be included in the CLI's fixed allowlist for smoke. An explicit success flag initialized false and set true only after a valid result is computed can implement the policy without reflecting on exception types or contents. Do not catch control-flow `BaseException` merely to make it look like an ordinary close failure. Preserve the existing primary failure classification, lock release, and gate/ownership checks; never allow a close failure to mask a bounded primary error. The close must be attempted exactly once even if the last attempt exits by return or raise.

The current `client_factory` injection remains available but its **public contract expands uniformly**: every fake client returned by it must accept the new `http_client` keyword through its factory, expose `.responses.create()` and a `.close()` method, and close/own the supplied HTTP client as the real SDK does. No production-only or test-only bypass of closure is allowed. The fake OpenAI modules used by offline tests must expose a fake `DefaultHttpxClient` with the same relevant constructor/hook/close shape, so tests cannot accidentally instantiate a real client, inspect environment proxies, or contact a provider. Factory-failure tests must verify cleanup of the separately constructed HTTP client.

## Attempt-local hooks, reset, and diagnostic mapping

A tiny non-persisted phase holder is created for the one `_execute()` and used only while its client exists; reset it to `before_request_hook` **immediately before each adapter-level `Responses.create()` attempt**. A synchronous request callback ignores its argument and changes `before_request_hook` to `request_hook_reached` only; it must never demote `response_hook_reached`. A synchronous response callback ignores its argument and sets `response_hook_reached`. Both are constant-time, non-blocking, non-raising and do not log, read attributes, retain references, or inspect request/response contents. The one-request lock and SDK `max_retries=0` constrain the active operation, but the holder must still be local rather than an adapter-wide global or class field. A later adapter retry starts from `before_request_hook` even if the preceding attempt reached a response hook.

Preserve the full existing SDK-call exception branch ordering and all transient/retry decisions. Change **only** the existing residual `elif isinstance(error, UnicodeError)` branch to choose the following non-transient fixed code from that attempt's phase:

| Attempt phase at residual Unicode catch | Fixed code |
| --- | --- |
| `before_request_hook` | `provider_unicode_before_request_hook` |
| `request_hook_reached` | `provider_unicode_request_hook_reached` |
| `response_hook_reached` | `provider_unicode_response_hook_reached` |
| No trustworthy phase state (defensive fallback only) | existing `provider_unicode_error_family` |

The exact `JSONDecodeError`, exact `ValueError`, SDK validation, OpenAI/HTTP/OS families, auth, quota, timeout, connection, client-error, and retry branches retain their existing precedence. These new Unicode codes are non-transient: one SDK call for that attempt, no sleep, and no retry because of Unicode. Other errors must **not** acquire phase suffixes. The CLI adds only the three phase codes and `provider_client_close_failure` to its literal diagnostic allowlist and retains `provider_unicode_error_family` plus every prior code. Exact CLI form is `smoke_failed:<code>\n`, empty stderr, exit 1; unknown, internal, non-string and unhashable codes still yield generic `smoke_failed\n`.

## Exact six-file Scope Lock and per-file sequence

**IN SCOPE — exactly these six tracked files, no seventh:**

1. `app/integrations/openai_analysis.py`: create the public `DefaultHttpxClient` with only hooks and parity arguments, inject via `http_client=`, add the attempt-local monotonic phase/reset, replace only the residual Unicode mapping, implement one-client-one-close lifetime and bounded close-failure policy including factory-failure HTTP-client cleanup. Preserve all existing request, authorization, provider, retry, and response-decoder behavior.
2. `test/test_openai_analysis.py`: update fake module/client factory to the same `http_client`/`close` contract; add offline pinned-SDK + MockTransport phase tests, lifetime/constructor parity, one-close/factory-cleanup, retry/reset, success/failure/close-failure precedence, leak and request-contract regressions. MockTransport is **test-only**.
3. `app/integrations/ai_smoke_cli.py`: add only the four fixed new codes to `_DIAGNOSTIC_CODES`; no CLI flow change.
4. `test/test_ai_smoke_cli.py`: extend the exact allowlist/output matrix for those four codes; retain fallback, lock-release, success, disabled, help, and unavailable cases.
5. `test/test_email_analysis_service.py`: update its fake OpenAI module and factory-returned client to accept `http_client` and close it exactly once; prove service-level outcomes and retries remain unchanged. No production service change.
6. `test/test_security.py`: likewise update its fake OpenAI module/client to the close-capable contract; prove no secret/content leak or new AI authority from hooks/close failures. No production security change.

**OUT OF SCOPE:** every other file, including `app/services`, `app/security`, routes, config, models, migrations, docs other than this plan, and dependencies. **RESTRICTIONS:** no transport wrapper, global monkeypatch, private SDK/HTTPX2 API in production, actual proxy/DNS/TLS/socket probe, keyring, operational config/SQLite, real provider call, live smoke, schema/model/endpoint/payload/output-token change, or timeout/retry/gate alteration. If implementation needs a seventh file or new dependency, STOP.

## Offline/no-network acceptance matrix

- **Constructor parity:** compare SDK internal default and hook-enabled `DefaultHttpxClient` construction using only synthetic key and public/default/source evidence: same base URL, initial timeout, SDK limits/pooling, `trust_env`, default transport/proxy path, TLS verify, follow-redirects and SDK retry count; only hooks differ. Do not print proxy/environment values. A production `transport=` must be absent.
- **Lifecycle:** one SDK client/factory call per `_execute()`, same client on adapter retry, one `close()` after final success or every post-construction failure; none between attempts, none before successful construction, and exactly one supplied-HTTP-client close on SDK-factory failure. Verify close on non-transient failure, transient exhaustion, deadline timeout, gate/ownership revocation during retry, invalid output, and unexpected post-construction failure. Assert request lock release and no double close. All fake factories must implement the same contract.
- **Close errors:** success plus failing close -> `provider_client_close_failure`, zero retry, no raw text; primary bounded failure plus failing close -> original failure and code, zero extra call; factory failure plus failing HTTP cleanup -> `provider_unavailable`; no stderr/log leakage. The close error must not turn an operation into success.
- **Phases:** synthetic pre-hook Unicode failure -> `provider_unicode_before_request_hook`; request hook but no response hook -> `provider_unicode_request_hook_reached` (without claiming dispatch); response hook then invalid UTF-8/UTF-16/UTF-32 JSON or post-response Unicode injection -> `provider_unicode_response_hook_reached` (without claiming provider/body cause). Redirect/auth repeated callbacks must be monotonic, and a second adapter attempt must reset phase. Hook functions must not touch their arguments; tests can use objects that fail on attribute access to enforce this. Tests use synthetic credentials and explicit MockTransport/no-send only.
- **Regression:** exact `JSONDecodeError`/`ValueError`, residual non-Unicode `ValueError`, SDK validation, OpenAI/HTTP/OS, auth/quota/rate/timeout/connection and `request_schema_failure` retain existing codes and attempts. Request kwargs, client factory arguments apart from `http_client`, fixed synthetic smoke payload, gate/ownership, deadline/retry/sleep, and one-shot smoke remain unchanged. CLI diagnostics and generic fallback remain bounded. No network, real keyring, operational database, or commercial activation.

For a future implementation task, run the focal adapter/CLI/service/security tests, then `python -m pytest`, then `git diff --name-only` and `git diff --check`; verify exactly the six Scope-Locked files and no untracked artifacts staged. A live ninth smoke requires separate explicit authorization **after** implementation and review, and is not an acceptance test for this plan.

## Risks, rollback, decisions, and verdict

The main risks are falsely reading hook labels as dispatch/provider proof, changing proxy/TLS/pooling by supplying a transport or plain client, leaking a client when a fake or factory construction does not honor closure, masking a primary bounded error with a close failure, and failing to reset phase across retries. The plan addresses these through public SDK/HTTPX2 seams, deterministic close, exact labels, six-file fake updates, and offline no-leak tests. External source content remains untrusted data; no hook receives authority to act on it.

Rollback of a future implementation must revert the adapter's hook/client-lifetime/diagnostic change, the CLI literals, and all four test-file updates together; it must not compensate by changing dependencies, endpoint, model, schema, timeout, retries, proxy settings, or gate. **OUT-OF-SCOPE DISCOVERY:** the SDK's internal sync wrapper has a finalizer, whereas the public injected client does not; the separately approved deterministic close contract intentionally replaces reliance on that finalizer. No other functional/security decision is needed for this bounded change.

**READY FOR IMPLEMENT.** This verdict is a plan review result only; implementation and any live smoke still need separate explicit approval.
