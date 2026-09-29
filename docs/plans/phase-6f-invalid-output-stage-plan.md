# Phase 6F — plan for bounded post-SDK output-stage diagnostics

**Status:** READY FOR IMPLEMENT
**Authority:** `phase-6f-invalid-output-stage-plan-task.md` and the approved `phase-6f-invalid-output-stage-analysis.md`.
**Mode:** offline planning only. No live response, credential, operational configuration, SQLite database, provider call, smoke, or network probe is needed.

## Objective and invariant

Relabel only failures already rejected after `Responses.create()` returns. The accepted response set, validation order, and all request and provider behavior remain identical. The three fixed codes report the *application validation stage*, not provider fault, malformed field, parser position, or evidence rule. They are non-transient and never cause a retry.

## Exact boundary, mapping, and precedence

1. Keep all SDK-call-boundary classifications unchanged, notably `provider_response_json_failure` for JSON decoding inside the SDK call. The post-return JSON code must not replace it.
2. Keep the post-return deadline check before extraction; expiry is `timeout`.
3. In `_structured_text()`, replace only its existing `invalid_output` raises with `provider_output_envelope_failure`. The covered branches are non-completed global status other than `incomplete`, absent or non-list output, disallowed item type or role, non-list content, unknown part or non-string `output_text`, absent text, empty aggregate, UTF-8 aggregate encoding failure, and aggregate exceeding `MAX_RESPONSE_BYTES`. Keep all checks and traversal in place, including reasoning handling and ordered concatenation without separators. Global `incomplete` remains `provider_incomplete`; encountered refusal remains `provider_refusal`, with exactly today's encounter-order precedence. Do not add a surrounding catch to `_structured_text()`.
4. After successful extraction, isolate `parsed = json.loads(text)` in its own `try` with the **unchanged** catch tuple `(ValueError, AISchemaError, TypeError, OverflowError, UnicodeError)`. Only failures caught there become `provider_output_json_failure`.
5. After successful parse, isolate `result = decode_analysis_response(parsed, projection)` in the adjacent `try` with the **same unchanged** catch tuple `(ValueError, AISchemaError, TypeError, OverflowError, UnicodeError)`. Only failures caught there become `provider_output_semantic_failure`. Unexpected exceptions remain uncaught by these stage handlers as before.
6. Keep `completed = True` only after successful decoding. Preserve deterministic `client.close()` exactly once and the primary-failure precedence: a close failure does not mask a pre-existing failure; `provider_client_close_failure` applies only after operational success. No retry, additional provider call, or changed lock lifetime results from these new codes.

The adapter's existing `invalid_output` production paths addressed here are precisely the `_structured_text()` raises and the combined parse/decode catch. Retain `invalid_output` as an allowlisted compatibility/fallback diagnostic in the smoke CLI; do not reinterpret any other code.

## Exact implementation Scope Lock

1. `app/integrations/openai_analysis.py` — substitute the fixed extraction code at current rejection sites and split the combined parse/decode `try` into two adjacent catches with the identical tuple above. No other adapter behavior changes.
2. `test/test_openai_analysis.py` — update existing exact-code expectations and add synthetic stage, special-code, retry, close, lock-release, SDK-boundary and no-leak regressions.
3. `app/integrations/ai_smoke_cli.py` — add exactly `provider_output_envelope_failure`, `provider_output_json_failure`, and `provider_output_semantic_failure` to `_DIAGNOSTIC_CODES`; leave all existing entries, exact-string membership check, output form, and fallback untouched.
4. `test/test_ai_smoke_cli.py` — update the exact allowlist expectation and test each new `smoke_failed:<code>` plus unknown, non-string and unhashable fallback to generic `smoke_failed`.

No fifth file, dependency, migration, configuration, schema, decoder, model, endpoint, payload, timeout, retry, hook, ownership, gate, service, route, or persistence edit is authorized. If a fifth tracked file or broader behavior change proves necessary, STOP before implementation.

## Offline acceptance matrix

Use only in-memory synthetic response objects, fake client/transport, and no-network tests. Assert exact code, bounded output, one provider attempt, and one client close where applicable.

| Input or failure point | Exact expected result |
| --- | --- |
| Global status neither completed nor incomplete; missing/non-list output; wrong item type; wrong role; non-list content; unknown part; non-string fragment; no text; empty aggregate; UTF-8 encode failure; oversized aggregate | `provider_output_envelope_failure` |
| Global incomplete; encountered refusal; expired post-return deadline | `provider_incomplete`; `provider_refusal`; `timeout`, respectively |
| Malformed JSON or concatenated complete JSON documents after valid extraction | `provider_output_json_failure` |
| Parseable wrong root; evidence mismatch; invalid support/reference index; invalid date/domain invariant; other currently caught decoder rejection | `provider_output_semantic_failure` |
| Valid structured output satisfying decoder/evidence/provenance rules | Existing success result unchanged |
| Successful decode followed by client close failure | `provider_client_close_failure` |
| SDK-call-boundary response JSON failure | Existing `provider_response_json_failure` |
| Other current transport, HTTP, hook, timeout and close failures | Their existing classifications and precedence unchanged |

For each rejected post-return case, assert no retry/provider re-call, request lock release, client close exactly once, and no raw synthetic output, exception text, exception identity, parser location, field name, request details or secret in exception string, logs, stdout or stderr. Recheck split-output concatenation, reasoning handling, refusal traversal, response byte bound, and valid success without changing acceptance. CLI tests must prove the exact three-code addition while preserving `invalid_output`, `provider_response_json_failure`, every prior diagnostic, and generic fallback for unknown or malformed codes. Run the two focused test files and then the full offline suite; inspect `git diff --name-only` and `git diff --check` before a future commit. Do not execute a live smoke as part of implementation or its validation.

## Risk, rollback, and decision

The principal risks are confusing SDK-boundary JSON with post-return JSON, changing refusal/incomplete precedence, widening catches, masking a primary failure on close, or leaking decoder detail. Call-site-specific fixed codes, identical catch tuples, and the matrix above address them. If validation fails, revert only the four-file relabeling and test/allowlist changes; the previous `invalid_output` classification remains the known baseline. A later live smoke requires separate explicit authorization and cannot retroactively identify the eleventh response's rejection stage.

No unresolved design choice or fifth-file need appears in the inspected code and approved analysis. This plan authorizes no implementation by itself.

READY FOR IMPLEMENT
