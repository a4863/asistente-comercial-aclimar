# Phase 6D — Synthetic smoke boundary analysis

**Result: READY FOR PLAN — analysis only.** No provider call, credential lookup, migration, test execution, or implementation is authorized by this document. A revised 6D implementation task must explicitly approve the Scope Lock below before code changes.

## 1. Objective and context

Provide one explicit local CLI invocation that can exercise the configured OpenAI Responses adapter with fixed, non-commercial synthetic text while the commercial gate remains OFF. Phase 6B1 correctly requires both live operational ownership and commercial authorization for `OpenAIAnalysis.analyze(AnalysisInput)`; 6D must not weaken that public commercial entry point. D5 authorizes the design of a synthetic smoke, not a live execution. D8 separates synthetic capability from commercial authorization; D11 keeps any smoke outcome transient.

## 2. Interpretation and current state

The current `OpenAIAnalysis` owns projection, request limits, strict schema, response decoding, deadline, bounded provider errors, and one retry. `_require_authorization()` checks ownership and the commercial gate before credential lookup and before every attempt, including retry after sleep. There is no smoke method. `SingleInstanceLock` derives an exclusive Windows sidecar handle from the configured SQLite file identity. `AISettings.enabled` defaults false; the credential remains in keyring. The credential CLI is separate from analysis. The process-local commercial gate defaults OFF. No 6D smoke CLI or result state exists yet.

The smoke must exercise the same adapter mechanics, but may not call `analyze()` with a temporarily enabled gate, a fake ownership object, or a caller-supplied `AnalysisInput`. It must not connect to SQLite or read IMAP, CRM, Calendar, notes, or commercial messages.

## 3. Documentation consulted

- `AGENTS.md`; `docs/plans/implementation-phase-6d-analysis-task.md`; `docs/plans/implementation-phase-6-plan.md`; `docs/plans/phase-6-activation-decisions.md` (D2, D5, D6, D8, D11–D13).
- `docs/security.md`, `docs/testing-strategy.md`; relevant `docs/architecture.md` AI/credential boundaries.
- `app/integrations/openai_analysis.py`, `app/integrations/ai_schema.py`, `app/domain/email_analysis.py`, `app/security/activation.py`, `app/security/single_instance.py`, `app/security/credential_cli.py`, `app/config.py`, `pyproject.toml`, and existing adapter tests.

## 4. Candidate designs and decision

| Candidate | Assessment |
| --- | --- |
| Temporarily enable `CommercialActivationGate` and call `analyze()` | Rejected: a smoke would become commercial authorization; failure or concurrency could leave an unsafe window. |
| Boolean `synthetic=True` or caller-provided synthetic text/`AnalysisInput` | Rejected: a general-purpose bypass can carry commercial content. |
| Public token/capability or wrapper that accepts arbitrary `AnalysisInput` | Rejected: the token can be constructed/reused or the wrapper can forward commercial data. A Python token is not a security boundary against code already executing in this process. |
| Separate provider implementation in the CLI | Rejected: duplicates schema, timeout, retry, error and disclosure rules, creating divergent security behavior. |
| **No-argument `OpenAIAnalysis.smoke()` using an adapter-owned fixed literal and one shared private execution path** | **Recommended:** the only public synthetic entry accepts no content or source identifier; the commercial entry remains gated. |

### Exact proposed API and flow

1. Add `OpenAIAnalysis.smoke() -> str` with **no payload, `AnalysisInput`, mode, gate, token, or settings argument**. Return only the bounded outcome `passed`; failures retain fixed local error codes. One invocation may include the adapter's already-configured bounded retry. The method is one-shot per adapter instance: a second invocation fails with a fixed code. The CLI makes one call and exits; another deliberate CLI run creates a fresh instance. This is an operational one-shot, not an unforgeable capability against malicious local Python code.
2. The adapter itself constructs one immutable synthetic `AnalysisInput` from fixed source literals: scope `synthetic:smoke`, target ID `1`, contract/policy version `1`, one target message, body `This is a synthetic test message. Please confirm receipt of a sample catalogue request.`, no sender, recipients, subject, date, prior messages, attachment, CRM/Calendar context, or externally supplied fields. Compute the body digest locally; the synthetic input digest is local-only and never disclosed or persisted. The exact literal and projection must be snapshot-tested. The `smoke()` caller cannot substitute an input. The existing projection and strict decoder validate the request/response; successful decoding, not a particular factual answer, is the smoke success criterion.
3. Refactor the adapter's existing call body into one private provider-execution path used by `analyze()` and `smoke()`. Keep commercial `analyze()` unchanged at the public boundary and always requiring ownership plus gate. The smoke path requires `AISettings.enabled=True` and live ownership before credential lookup/client creation and immediately before the first attempt and each retry after any delay, but **never reads or enables the commercial gate**. It uses the same endpoint allowlist, configured model, credential reference, request size, timeout, SDK retries disabled, `store=false`, strict Structured Outputs, no tools/functions, decoder and bounded errors. No duplicate provider implementation or public mode flag is permitted.
4. Add console command `asistente-aclimar-ai-smoke` with no data arguments. It reads normal settings, requires technical AI enabled and a configured allowed endpoint, acquires the actual `SingleInstanceLock(settings.database_url)` before constructing/calling the adapter, invokes `smoke()` exactly once, prints only a bounded status, and releases the lock on all exits. A running operational app holding the same lock makes the CLI fail closed; it must not use a different lock identity or override ownership. `SingleInstanceLock` may stat the SQLite path and create its sidecar; the CLI must not open/query SQLite or read commercial rows. The command must not import domain source selectors, IMAP/CRM/Calendar clients, or the web route. It never changes the commercial gate.
5. A live invocation is **not** part of 6D implementation or pytest. It remains a separately approved 6F operation with an exact command, account/endpoint/credential, budget, and bounded outcome reporting. A successful smoke is not EU residency, ZDR, retention compliance, or consent to commercial-data processing.

The fixed payload is non-commercial. Python code with arbitrary execution rights can still monkeypatch private methods or construct clients directly; this design prevents accidental/general-purpose *public API* bypass, not malicious code already running in the trusted local process. Do not describe a token or underscore-prefixed method as cryptographically sealed.

## 5. Proposed implementation Scope Lock (revised from the earlier plan)

**IN SCOPE — create:** `app/integrations/ai_smoke_cli.py`, `test/test_ai_smoke_cli.py`.

**IN SCOPE — modify:** `app/integrations/openai_analysis.py`, `test/test_openai_analysis.py`, `pyproject.toml`.

The earlier Phase 6 plan listed only the CLI, its test, adapter tests, and `pyproject.toml`. That four-file lock is insufficient: the existing adapter has no safe synthetic entry, and a CLI-only workaround would either duplicate provider behavior or bypass the commercial gate. The subsequent 6D plan/task must explicitly authorize the fifth file, `app/integrations/openai_analysis.py`; analysis does not itself grant that permission.

**OUT OF SCOPE:** `app/security/activation.py`, `app/main.py`, routes/UI, domain selection, persistence/models/migrations, IMAP/CRM/Calendar, credential implementation, config schema, commercial enablement, and a live smoke run.

**RESTRICTIONS:** no caller-supplied request text or `AnalysisInput` on the smoke API/CLI; no gate mutation; no provider request in pytest; no new dependency or persistence; no environment/argv data bypass; no secret/request/response body in output/logs. The explicit 6F live approval remains separate.

## 6. Dependencies, risks and test matrix

Dependencies: approved D5/D8/D11/D12/D13 semantics, existing `AnalysisInput`/projection/decoder, `AISettings`, keyring credential reference, `SingleInstanceLock`, and the current OpenAI SDK already pinned in `pyproject.toml`. No model, migration, or dependency change is needed. CLI registration is the only proposed `pyproject.toml` edit.

| Offline test | Expected evidence |
| --- | --- |
| `analyze()` without ownership/gate and with gate OFF | Zero credential/client/provider calls, even when technical AI is enabled or a fake client is supplied. |
| `smoke()` with real/fake ownership false, closed, or revoked before attempt/retry | Zero subsequent provider calls; bounded error. |
| `smoke()` with technical AI disabled or invalid endpoint | Zero credential/client/provider calls. |
| Fixed input snapshot and adversarial arbitrary text/IDs passed to method/CLI | Public smoke signature refuses arguments; provider request contains exactly the fixed synthetic projection and never caller material. |
| Fake Responses success | Same strict schema, decoder, `store=false`, disabled SDK retries, allowed endpoint/model, timeout and size bounds; no tools/functions. |
| Fake transient error and retry | Only configured bounded retry; ownership is revalidated after delay; second smoke invocation on the same adapter is refused. |
| CLI fake settings/keyring/lock/client and failure injection | Actual lock lifecycle and configured credential reference are used; all failures release the lock; output contains only bounded codes, no path, handle, key, request or raw provider error. |
| Gate remains OFF before/during/after smoke | No call to `enable()` and no effect on a distinct commercial `analyze()` call. |
| No commercial-source imports/reads, no durable smoke state | Tests fail on SQLite connection, IMAP/CRM/Calendar access, file-based result write, or provider network; status is process-local only. |

Run `python -m pytest test/test_ai_smoke_cli.py test/test_openai_analysis.py`, then `python -m pytest`, in the later implementation task with all provider calls faked. No tests or provider calls were run for this analysis.

## 7. Ambiguities, out-of-scope discoveries and verdict

**Ambiguities/decisions required before planning:** none for the recommended public boundary. The exact synthetic literal and revised five-file Scope Lock must be ratified by a subsequent explicit 6D plan/task; they are proposals here, not implementation authority. If that Scope Lock cannot include the adapter, **STOP**: no safe CLI-only implementation is identified.

**OUT-OF-SCOPE DISCOVERY:** `docs/architecture.md` still contains historical wording that no AI provider/model is selected, while Phase 5 selected OpenAI/`gpt-6-sol`. This is already identified for a separate documentation correction; 6D must not edit it.

**READY FOR PLAN.** The narrow no-argument method can share the existing provider machinery without weakening commercial `analyze()`, provided the future approved implementation Scope Lock includes the adapter. There is no authorization here to build or run a live smoke.
