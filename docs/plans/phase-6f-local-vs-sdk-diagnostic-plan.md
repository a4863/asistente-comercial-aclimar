# Phase 6F — local construction vs SDK-call diagnostics plan

**Status: READY FOR IMPLEMENT — plan only.** Implementation, a live smoke, and any operational credential/configuration access require separate authorization.

## Objective and local authority

Separate one currently conflated outcome in the synthetic OpenAI smoke: failure while building the local response schema/request arguments versus a non-HTTP exception raised by `client.responses.create()`. The third authorized live smoke yielded `smoke_failed:provider_non_http_failure`; that result alone identifies neither an SDK phase nor a root cause.

The only design evidence is `docs/plans/phase-6f-local-vs-sdk-diagnostic-plan-task.md`, the accepted `docs/plans/phase-6f-non-http-failure-analysis.md`, current adapter/CLI/tests, and local repository policy in `AGENTS.md` and `docs/security.md`. The prior offline check used operational `C:\Python313\python.exe`, installed `openai==3.17.0`, a deterministic/JSON-serializable `response_schema()`, successful transformation/serialization of the exact fixed synthetic kwargs, and one SDK call intercepted by an explicit in-process `httpx2.MockTransport`. No public-web documentation or live provider result is needed to decide this plan. This evidence proves local compatibility for the synthetic values tested, not server acceptance or the cause of the live failure.

## Exact phase boundary and error contract

Keep the existing input projection, `request_text` JSON/UTF-8 validation, request-size check, exclusive request lock, credential lookup, SDK client construction, retry loop, deadline check, and `authorize()` order unchanged. In each retry-loop iteration, **after** computing positive `remaining` and rechecking `authorize()`, but **before** invoking `client.responses.create()`, use a dedicated bounded `try` to evaluate `response_schema()` and construct the local argument mapping for this one call. The mapping must contain exactly the current values and keys: `model=settings.model`, `instructions=_INSTRUCTIONS`, `input=request_input`, `text={"format":{"type":"json_schema","name":"commercial_analysis_v1","strict":True,"schema":response_schema()}}`, `max_output_tokens=settings.max_output_tokens`, `store=False`, `timeout=remaining`. Do not move `response_schema()` out of the loop, cache it, validate/change it, or alter any data or timing value. Existing `request_input` and `request_text` construction remain in their present earlier `invalid_input` boundary; the new category does not reclassify those existing validation outcomes.

Catch only `Exception` from that local schema/argument-construction block and raise a fixed `OpenAIAnalysisError("request_schema_failure")` through the existing `_raise` helper, which suppresses the exception cause. Do not inspect, print, log, format, or retain the caught exception. Do not enter `client.responses.create()` on such a failure, and do not retry it. The new code means **unexpected local schema/argument-construction failure before SDK invocation**, not provider schema rejection or proof that the schema is unsupported.

Put only `response = client.responses.create(**request_kwargs)` in the existing SDK-call `try`. Keep its complete current exception classifier and retry/deadline behavior unchanged: timeout, connection, 429 quota/rate, auth, other mapped HTTP statuses, and `provider_failure` retain their current meaning. A remaining non-HTTP exception **from the SDK call expression** still maps to `provider_non_http_failure` and is non-transient as today. This category must not claim whether request dispatch did or did not occur; SDK response parsing can also fail after a response. No transport marker, hook, additional instrumentation, or pre-/post-dispatch distinction is authorized.

The CLI adds exactly the literal `request_schema_failure` to its private `_DIAGNOSTIC_CODES` set. It emits `smoke_failed:request_schema_failure\n` to stdout, empty stderr, exit 1 for this code. Keep the `type(code) is str` check, exact allowlist membership, `smoke_failed` fallback for unknown/non-string/unhashable/internal codes, and all existing `passed`, `disabled`, `lock_unavailable`, `unavailable`, help, and argument-error behavior. `provider_non_http_failure` stays allowlisted and unchanged. No raw exception string, SDK class, provider body, schema, payload, credential, or request metadata may become CLI output.

## Exact Scope Lock and per-file work

**Only these four tracked files may change in a future implementation:**

1. `app/integrations/openai_analysis.py` — isolate per-attempt local schema/argument assembly in its own bounded `try`; invoke SDK with those unchanged kwargs; preserve classifier/retry and all other branches.
2. `test/test_openai_analysis.py` — update the existing local-schema failure expectation to `request_schema_failure` with zero SDK calls; add no-leak/no-retry checks, one-call non-HTTP SDK failure checks, exact-kwargs regression, and an installed-SDK synthetic-key/no-send transport test. Keep fake credentials and ownership/gate fixtures; no real provider, keyring, config, or SQLite.
3. `app/integrations/ai_smoke_cli.py` — add only the new fixed diagnostic literal to `_DIAGNOSTIC_CODES`; no CLI flow or output-format changes.
4. `test/test_ai_smoke_cli.py` — add the new literal to the allowed-code matrix and verify exact output/exit/stderr, generic fallback, lock release, and non-disclosure.

All other files are **out of scope**, including `app/integrations/ai_schema.py`, domain/service/persistence, routes, templates, gate, credentials, config, `pyproject.toml`, migrations, and documentation. Do not change model, endpoint, Responses API method, Structured Outputs schema semantics, payload, output-token limit, timeout, retry count/delay, SDK version/dependencies, or commercial activation. No new logging or telemetry. A fifth tracked file is a STOP condition, not a Scope Lock expansion.

## Offline/no-network tests and acceptance

1. Adapter fake: monkeypatch `response_schema()` to raise a synthetic exception containing secret-like text, URL, newline, and provider-body-like text. Expect only `request_schema_failure`, exactly zero `FakeResponses.create` calls, no retry/sleep, and none of the injected strings in exception representation, captured stdout/stderr, or logs. The request lock must still release.
2. Adapter fake: make `FakeResponses.create` raise `TypeError`/`ValueError` or another non-HTTP exception. Expect `provider_non_http_failure`, one SDK call, no retry, and no raw text. Keep existing forged-status and typed HTTP tests; the local category must not swallow SDK exceptions.
3. Exact-kwargs regression: successful fake call captures every current kwarg/value, including identical `input` projection, `text.format` name/type/strict/schema, `store=False`, configured model/max-output-tokens, and a positive per-call `timeout` bounded by the existing deadline. For an existing transient error, confirm reauthorization and the same local build pattern on the allowed second attempt without changing retry counts or delay.
4. Installed-SDK contract: in `test/test_openai_analysis.py` only, use a synthetic key and `httpx2.MockTransport` (or an equivalent explicit transport whose handler fails if any real dispatch is attempted) to execute the fixed synthetic request against the installed SDK. Assert a single in-process `POST /v1/responses`, expected request-structure keys and accepted JSON serialization; return only a synthetic response. Never use a default HTTP transport, real keyring, operational TOML/SQLite, or provider endpoint traffic. Do not print request body or authorization header. The test must be fully offline under the pinned dependency.
5. CLI fake: `request_schema_failure` yields exactly `smoke_failed:request_schema_failure\n`, stderr empty, exit 1, lock released; `provider_non_http_failure` remains identical to today. Unknown, non-string and unhashable codes collapse to `smoke_failed\n`; existing preflight/success cases remain green.

After implementation run `python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py`, then `python -m pytest`, followed by `git diff --name-only` and `git diff --check`. Confirm the tracked diff contains only the four files above. Green tests are necessary but do not authorize a live smoke. No migration or external-state operation is part of validation.

## Security, risk, rollback, and STOP

The exception boundary must never expose local/schema/SDK/provider exception text or a traceback through the adapter or CLI. The smoke remains fixed synthetic, one-shot, ownership-protected, and independent of the commercial gate. The gate remains OFF; no call to OpenAI is authorized. The new code is a diagnostic bucket, not permission to modify the request contract. The chief residual risk is overinterpreting `provider_non_http_failure`: it can originate before or after SDK dispatch, and this plan deliberately does not distinguish those phases.

Rollback, if a later implementation fails acceptance, is to revert **only** the four-file diagnostic change as one unit and retain the existing `provider_non_http_failure` behavior. Do not compensate by changing model, endpoint, schema, timeout, retries, credentials, or gate. Keep any rollback commit separate from this planning commit.

**STOP** if implementation needs a fifth file, a new dependency, live access, raw provider/exception content, a pre-dispatch/post-dispatch SDK distinction, or any request/retry semantic change. The existing local evidence does not justify such an expansion. There is no unresolved functional choice for the narrower two-phase diagnostic specified here.

**Verdict: READY FOR IMPLEMENT**, subject to explicit approval of this four-file Scope Lock. This document is a plan, not implementation or authorization for a further live attempt.
