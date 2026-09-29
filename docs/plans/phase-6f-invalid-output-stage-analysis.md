# Phase 6F — bounded `invalid_output` stage analysis

**Mode:** offline, read-only diagnosis. **Trigger:** the eleventh authorized synthetic smoke returned `smoke_failed:invalid_output` after the split-text correction. This does not reveal which post-return stage failed. No live response, credential, keyring, operational config/database, provider or network was accessed.

## 1. Objective, context, interpretation, and sources

Determine whether existing post-`Responses.create()` `invalid_output` results can be partitioned by **application validation stage**, without changing the accepted response set or revealing text, exception details or schema/evidence failures. This is diagnostic planning, not authorization to implement or run another smoke.

Consulted `AGENTS.md`, `docs/plans/phase-6f-invalid-output-stage-analysis-task.md`, `docs/plans/phase-6f-eleventh-live-smoke-failure.md`, the approved prior invalid-output analysis and split-output plan, relevant AI/security/testing provisions of `docs/functional-spec.md`, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, and the current adapter, schema decoder, smoke CLI and their focused tests. No required source was missing.

## 2. Current decision tree and safe boundaries

After `client.responses.create(**request_kwargs)` returns:

1. The adapter checks the soft deadline. Expiry raises `timeout` **before** extraction. It must remain `timeout`.
2. `_structured_text(response)` checks global status and the output/message/content envelope; skips `reasoning`; rejects tool/unknown items and parts; detects `refusal`; concatenates allowed `output_text` parts; requires a nonempty aggregate; checks UTF-8 encoding and `MAX_RESPONSE_BYTES`. Its current `invalid_output` branches are non-`completed` status other than `incomplete`, non-list/missing `output`, wrong item/role, non-list content, unknown/non-string part, no text or empty aggregate, aggregate encoding failure and aggregate over the byte bound. `incomplete` and `refusal` already have their own codes.
3. `json.loads(text)` parses the extracted string. Malformed JSON and concatenated independent JSON documents currently enter the shared `invalid_output` catch.
4. `decode_analysis_response(parsed, projection)` enforces the local structural/schema bounds and semantic/domain/evidence rules. Its currently caught failures also enter that same `invalid_output` catch.
5. A successful decode marks the operation complete. SDK client close is in a surrounding `finally`: a close failure produces `provider_client_close_failure` **only if decode had succeeded**; an earlier primary failure remains primary. This precedence must not change.

These boundaries are disjoint by call site. A fixed code can identify the function/stage that rejected the output without inspecting the rejected value or any exception's message/class. It cannot identify the exact rule, prove that the provider was at fault, or recover what the eleventh response contained. An unexpected exception outside the existing catch set must **not** be newly swallowed merely to force a stage code; that would change failure semantics.

## 3. Exact candidate bounded codes

| Code | Only emitted for | Meaning and limits |
| --- | --- | --- |
| `provider_output_envelope_failure` | Existing `_structured_text` branches that now raise `invalid_output` | Application extraction-stage rejection, including aggregate UTF-8/size guards; not a claim that only the SDK envelope shape was wrong. |
| `provider_output_json_failure` | Existing caught `json.loads(text)` failure **after** successful extraction | Application JSON parse stage; no parser position, token or text is exposed. Distinct from `provider_response_json_failure`, which arises inside the SDK-call boundary before an SDK response returns. |
| `provider_output_semantic_failure` | Existing caught `decode_analysis_response(parsed, projection)` failure **after** successful JSON parse | Local schema/evidence/domain stage; no indication which field, rule or source span failed. |

The `provider_output_` prefix identifies the validated data source, **not** fault attribution to OpenAI. The names identify stage only. Treat all three as fixed, non-transient, no-retry values. Preserve the existing `invalid_output` CLI allowlist entry for compatibility/fallback, but new deterministic branches should use the stage-specific code. No raw value, exception text, exception type/module, parser offset, field name or validation reason may be emitted.

## 4. Special-code precedence and minimal future change

Preserve the current ordered behavior:

- Before post-return validation, SDK-call failures retain all existing HTTP/transport/hook classifications, including `provider_response_json_failure`; they are **not** post-return JSON failures.
- Post-return deadline expiry remains `timeout`, even if a response object exists.
- Global `incomplete` remains `provider_incomplete`; encountered refusal remains `provider_refusal`. A preceding disallowed item still fails at its existing encounter point; do not reorder validation or pre-scan refusals.
- Existing `_structured_text` `invalid_output` sites alone may emit the envelope-stage code. Its acceptance checks, traversal order, aggregate and bounds must not change.
- Split the present shared `try` into adjacent `json.loads` and `decode_analysis_response` `try` blocks, retaining the **same exception tuple at each call site** and changing only the fixed output code. Keep `completed=True` and client close timing unchanged.
- On a preceding stage failure, a simultaneous ordinary `close()` failure remains suppressed in favor of the primary code. Only a previously successful decode may yield `provider_client_close_failure`.

No schema, decoder, request, retry, deadline, hook, ownership, gate or log change is needed. Replacing the existing `invalid_output` literals in `_structured_text` (rather than catching every exception around it) avoids accidentally remapping `provider_incomplete`, `provider_refusal` or unforeseen exceptions.

## 5. Offline evidence and required future tests

A no-file-write, `python -B` synthetic check used the current `_structured_text`, stdlib `json.loads`, the current decoder and a fixed in-memory smoke projection. It reported only case labels and bounded stage labels:

| Synthetic cases | Observed stage |
| --- | --- |
| Non-completed status other than incomplete; missing/non-list output; wrong item or role; non-list content; unknown part; non-string text; no text; empty aggregate; aggregate Unicode encode failure; aggregate over byte bound | Extraction/envelope |
| Global incomplete; refusal | Existing `provider_incomplete`; existing `provider_refusal` |
| Malformed JSON; two complete JSON objects concatenated | JSON parse |
| Parseable but wrong top-level shape; evidence mismatch; invalid support index; invalid date; empty required domain support | Semantic decoder |
| Structurally and semantically valid empty candidate object | Accepted |

The stage result was determined by which function rejected the synthetic case; no live-output inference follows. Future offline tests should assert exact fixed codes for every row, no retry/provider re-call, one SDK client close, lock release, no raw synthetic text in exception/log/stdout/stderr, and unchanged provider/transport/hook codes. CLI tests must verify only the three new exact strings are added to its bounded allowlist, `smoke_failed:<code>` output is exact, and unknown values still collapse to `smoke_failed`. Preserve the existing `provider_incomplete`, `provider_refusal`, `timeout`, `provider_client_close_failure` and `provider_response_json_failure` regressions. No live test belongs to normal pytest.

## 6. Scope Lock, dependencies, risks, and out-of-scope discovery

**IN SCOPE now:** create only `docs/plans/phase-6f-invalid-output-stage-analysis.md`.

**Candidate future Scope Lock, subject to a separate plan and approval:**

1. `app/integrations/openai_analysis.py` — fixed code substitution at existing extraction failures and separation of the two post-extraction catches, without acceptance changes.
2. `test/test_openai_analysis.py` — stage/special-code, no-retry, close, lock and no-leak cases.
3. `app/integrations/ai_smoke_cli.py` — three-code allowlist addition only.
4. `test/test_ai_smoke_cli.py` — exact allowlist/output/fallback regressions.

**OUT OF SCOPE:** all other files and integrations, model/schema/decoder/persistence, operational config/database, actual credentials or response, live smoke and external systems. **RESTRICTIONS:** no new dependency; no raw diagnostics; no broad exception catch; no change to acceptance, refusal order, deadlines, retries, client lifetime, hooks, gate or ownership. A fifth file or need to inspect live content is STOP.

Dependencies are the existing stdlib JSON parser, Phase 5A decoder and bounded smoke CLI. Main risks are mislabeling an SDK-internal `provider_response_json_failure` as the new post-return JSON stage, leaking decoder details, altering special-code precedence, or broadening catches and thus changing acceptance/error handling. Call-site-specific fixed codes and adversarial offline tests mitigate them.

**OUT-OF-SCOPE DISCOVERY:** this partition does not tell whether the eleventh live output failed the envelope, JSON or semantic stage; that historical result cannot be reclassified without forbidden response inspection. It also does not prove another live attempt will pass.

## 7. Ambiguities, decisions, and verdict

No new functional or security decision is required for a pure relabeling of existing caught failures. The exact names above are suitable for a separate implementation-ready plan; their stage definitions must accompany them. A future twelfth live synthetic smoke could be considered **only after** that plan is approved, implemented, and offline-tested, and only with fresh explicit authorization. This analysis authorizes none.

READY FOR PLAN
