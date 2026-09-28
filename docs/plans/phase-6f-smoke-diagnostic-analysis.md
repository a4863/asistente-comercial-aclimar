# Phase 6F — bounded synthetic smoke diagnostics analysis

**Result: READY FOR PLAN — analysis only.** A later implementation and any further live smoke require separate approval.

## 1. Objective

Make a future, separately authorized synthetic smoke failure distinguish safe adapter categories without disclosing provider text, response bodies, credentials, configuration values, commercial content, or internal security state.

## 2. Context and interpretation

The first authorized one-shot live smoke returned only `smoke_failed`; that outcome does not identify the cause and does not justify a model, endpoint, schema, retry, timeout, credential, or gate change. This task is offline analysis only. The future correction should change only the dedicated CLI presentation of an existing `OpenAIAnalysisError.code`; it must not change adapter execution or browser/commercial error surfaces.

## 3. Documentation consulted

`AGENTS.md`; `docs/plans/phase-6f-smoke-diagnostic-analysis-task.md`; `docs/plans/phase-6f-live-smoke-task.md`; `docs/plans/phase-6d-smoke-analysis.md`; `docs/plans/implementation-phase-6d-task.md`; `docs/functional-spec.md` (credential and AI boundaries); `docs/architecture.md` (adapter/credential and logging boundaries); `docs/security.md`; `docs/testing-strategy.md`; `app/integrations/ai_smoke_cli.py`; `app/integrations/openai_analysis.py`; `test/test_ai_smoke_cli.py`; `test/test_openai_analysis.py`. No required document was missing.

## 4. Current state

`ai_smoke_cli.main()` accepts no payload arguments, loads operational settings, acquires `SingleInstanceLock`, creates the adapter and calls `smoke()` once. It prints `passed` on success; `disabled`, `lock_unavailable` or `unavailable` at preflight boundaries; and `smoke_failed` for **every** `OpenAIAnalysisError`. Its outer unexpected-exception branch prints `unavailable`. Exit codes are 0 for success/help, 2 for invalid arguments, and 1 for operational failures.

`OpenAIAnalysisError.code` is a plain string supplied by the adapter; the constructor does not enforce a vocabulary. The adapter emits fixed local categories and deliberately suppresses raw provider exception text. It maps HTTP/auth/quota/transient errors locally; response refusal/incomplete and decoder/shape failures also become fixed codes. Tests use fake credentials and clients and already assert relevant categories and non-disclosure. The smoke uses a fixed synthetic input, technical AI enablement and ownership, but does not consult or enable the commercial gate. No code, test, provider call, keyring lookup or live configuration access occurred in this analysis.

## 5. Affected elements and proposed change

**IN SCOPE for a future correction:** `app/integrations/ai_smoke_cli.py` and `test/test_ai_smoke_cli.py` only. Add a local, immutable explicit allowlist and format recognized adapter failures as exactly one stdout line `smoke_failed:<code>`, with exit code 1. Unknown, malformed or security-internal codes remain exactly `smoke_failed` and exit code 1. Never interpolate `str(error)`, `repr(error)`, an exception cause, SDK metadata or arbitrary `.code` into output. Keep stderr empty for these adapter failures. Existing `passed` remains exactly `passed\n` with exit code 0; help, invalid arguments, disabled, lock and unexpected-exception behavior retain their current bounded outputs and exit codes. No second diagnostic line is needed.

### Explicit CLI diagnostic vocabulary

| Classification | Existing adapter codes | CLI outcome |
| --- | --- | --- |
| Safe operational/provider diagnosis | `credential_missing`, `credential_unavailable`, `provider_unavailable`, `provider_auth`, `provider_quota`, `provider_transient_exhausted`, `provider_failure`, `timeout`, `provider_incomplete`, `provider_refusal`, `invalid_output`, `invalid_configuration` | `smoke_failed:<exact allowlisted code>` |
| Internal security/concurrency or synthetic-input integrity | `operational_ownership_required`, `commercial_activation_required`, `busy`, `smoke_already_used`, `sensitive_content`, `invalid_input` | `smoke_failed` |
| Already handled before adapter call | `disabled` | Preserve existing CLI `disabled`, but collapse this code if raised unexpectedly by the adapter |
| Any unknown, non-string or attacker-controlled code | Arbitrary value | `smoke_failed` |

The exposed codes reveal only a coarse category, not the account, credential reference, endpoint, model, request, response, HTTP body, retry headers or SDK message. `provider_auth` is not proof the key is wrong: the adapter also maps HTTP 403 to it. `provider_quota` is not proof of one particular billing cause. `invalid_output` combines shape, JSON and decoding failures; do not split it here. The CLI must use membership against literal approved strings, never a regex accepting new code-like strings or an imported SDK error field.

The future CLI must first require `type(error.code) is str`, then check membership in the literal allowlist; all other values use the generic fallback without formatting or hashing them. The adapter's existing tests establish the vocabulary and mapping without adapter modification. They do not make `OpenAIAnalysisError.code` intrinsically safe: the CLI allowlist is the final display boundary.

## 6. Dependencies

Only existing Python stdlib, adapter error type, current CLI boundaries and pytest fakes. No new package, provider API, persistence or schema change. No logging change is required or authorized.

## 7. Risks and security invariants

- **High — arbitrary-code reflection:** an exception constructed with raw secret/body text must not be printed. Explicit equality membership and generic fallback are mandatory, including non-string/unhashable values if tests inject them.
- **High — raw exception logging:** no traceback or `str`/`repr` of provider/credential/config errors may enter stdout, stderr or logs through this correction.
- **Medium — internal state disclosure:** ownership, gate, concurrency, one-shot and synthetic-content integrity errors remain collapsed; the dedicated CLI's existing `disabled`/`lock_unavailable` preflight statuses are unchanged.
- **Medium — misleading diagnosis:** the code is a bounded category, not a definitive root cause. A single failure does not authorize configuration changes or retrying live.
- **High — commercial boundary:** no change to `OpenAIAnalysis.analyze()`, smoke payload, gate, credential store, provider request or web routes. The commercial gate remains OFF.

## 8. Ambiguities and decisions pending

None for planning: the task explicitly prefers a fixed allowlist; the existing adapter vocabulary and security policy support the narrow contract above. Implementation approval and a separate live-attempt authorization remain pending. If a future plan seeks to expose any additional code or a second diagnostic line, it needs an explicit new decision.

## 9. Offline test matrix

Use only fake settings, lock, credentials and adapter in `test/test_ai_smoke_cli.py`; do not run the real command or provider.

1. Parameterize every allowed code: exactly `smoke_failed:<code>\n`, empty stderr, exit 1, lock released.
2. Parameterize internal/excluded and unknown codes, including raw secret, provider body, path/URL, newline/control text, empty string and non-string/unhashable values: exactly `smoke_failed\n`; injected text absent from stdout, stderr and captured logs.
3. Inject an unexpected exception with raw secret/body text: preserve exactly `unavailable\n`, exit 1, no raw output and lock released.
4. Preserve success `passed\n`/0; `disabled`, `lock_unavailable`, invalid arguments/help and their existing exit codes. Assert no adapter construction or credential access on preflight failures.
5. Assert the CLI neither reads nor changes the commercial gate; no real keyring, local operational configuration, SQLite or network access.
6. Reuse existing `test/test_openai_analysis.py` fake-provider tests as evidence for auth, quota, transient exhaustion, timeout, refusal, incomplete and invalid-output mapping; do not modify adapter tests for the CLI-only change.

For a later implementation, run `python -m pytest test/test_ai_smoke_cli.py test/test_openai_analysis.py`, then `python -m pytest`, and verify the two-file diff and `git diff --check`.

## 10. Scope Lock for future correction

**IN SCOPE:** `app/integrations/ai_smoke_cli.py`; `test/test_ai_smoke_cli.py`.

**OUT OF SCOPE:** adapter, schema/decoder, model, endpoint, timeout/retry policy, credentials/keyring, operational config, lock implementation, commercial gate, routes/UI, persistence, logging, dependencies and documentation changes beyond a separately authorized plan.

**RESTRICTIONS:** no live smoke or OpenAI call; no raw exception/provider text; no arbitrary `.code` interpolation; no new output channel/telemetry; no gate activation; no second provider attempt outside existing adapter policy.

## 11. Out-of-scope discoveries

`docs/architecture.md` retains historical wording that no AI provider/model is selected, although later approved Phase 5 selected OpenAI/`gpt-6-sol`. This documentation drift predates the present task and must not be corrected within this Scope Lock. The prior `smoke_failed` outcome itself provides no evidence that the configured model or endpoint is wrong.

## 12. Result

**READY FOR PLAN.** The two-file CLI-only correction can provide safe bounded diagnosis while preserving the existing adapter and all external-state boundaries. Another live smoke is prohibited until that correction is separately approved, implemented, validated offline and a fresh one-shot live execution is explicitly authorized.
