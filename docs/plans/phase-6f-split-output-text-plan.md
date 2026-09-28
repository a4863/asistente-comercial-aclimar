# Phase 6F — split `output_text` handling plan

**Status:** READY FOR IMPLEMENT

**Mode now:** planning only; no production or test change, no provider call.
**Authority:** `phase-6f-split-output-text-plan-task.md` and the approved `phase-6f-invalid-output-analysis.md`.

## Objective and context

Allow one logical, schema-shaped JSON text to be split across multiple permitted Responses `output_text` parts, while preserving every existing fail-closed envelope check and the unchanged `json.loads` → `decode_analysis_response` boundary. This addresses an offline-demonstrated SDK-envelope mismatch; it does **not** assert that the unseen tenth live response had this shape.

Consulted `AGENTS.md`, the two authority documents above, relevant AI/security/testing rules in `docs/functional-spec.md`, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, `app/integrations/openai_analysis.py`, and `test/test_openai_analysis.py`. The current `_structured_text` already traverses SDK items in order, skips `reasoning`, checks assistant role/content/part types, and returns a single text. Its sole extraction incompatibility for this task is `len(texts) != 1`. Existing single-part and refusal/incomplete tests use synthetic fakes; the approved analysis also validated split variants with installed SDK `Response` models.

## Exact implementation algorithm

Change only `_structured_text(response)`:

1. Keep the current global status checks in the same order: `incomplete` → `provider_incomplete`; anything other than `completed` → `invalid_output`. Keep `output` required to be a list.
2. Iterate `output` in its original order. Skip only `type == "reasoning"`. Every remaining item must be `type == "message"` with `role == "assistant"`; otherwise raise `invalid_output`. Require each accepted message's `content` to be a list.
3. Iterate each content list in order. A `refusal` immediately raises `provider_refusal` at the point encountered, including after earlier text. A part not typed `output_text`, or an `output_text` whose `.text` is not `str`, immediately raises `invalid_output`. Otherwise append its string as a fragment, including an empty string. Do not read annotations or metadata.
4. Require at least one collected fragment. Join fragments with `""` exactly in traversal order—no separator, trimming, coercion, JSON repair, or selection of one message. Reject an empty aggregate with `invalid_output`.
5. Run the existing UTF-8 encoding guard and `MAX_RESPONSE_BYTES` comparison on the **aggregate**, then return that aggregate. Keep its existing bounded `invalid_output` behavior for Unicode encoding or excess bytes.

Make no other production change. The adapter's existing `json.loads(text)` and `decode_analysis_response(parsed, projection)` remain untouched. Adjacent complete JSON documents concatenate into invalid JSON and remain rejected. No SDK `response.output_text` shortcut is permitted: it can omit refusal or other disallowed items from consideration.

**Explicit no-change decision:** do not read, require, or validate `message.status`. Preserve its current behavior exactly. Do not add response-level checks beyond those listed above.

## Preserved semantics and security boundaries

Refusal, global incomplete/non-completed status, malformed/oversize/Unicode-invalid text, unknown content, tool/non-message output, wrong role, and absent text retain their existing bounded codes and no-retry behavior. Reasoning remains ignored; annotations/response metadata remain inert. All exact schema, evidence-span, support/provenance, fact-vs-inference, and domain checks remain in the existing decoder. The provider remains untrusted; the change grants no tool/action authority and adds no logging or raw-output diagnostics. SDK client closure, request lock, hook phase state, retry/deadline, ownership and commercial gate remain untouched.

## Exact two-file Scope Lock

**IN SCOPE for later approved implementation:**

1. `app/integrations/openai_analysis.py` — only `_structured_text`'s fragment-count/aggregate extraction and bound application.
2. `test/test_openai_analysis.py` — focused synthetic envelope and adapter regressions, including installed SDK model objects where practical.

**OUT OF SCOPE:** every other tracked file, especially `app/integrations/ai_schema.py`, CLI, service, configuration, persistence, docs, dependencies, and migrations. No actual credential, keyring, operational config/database, provider call, live response inspection, or live smoke.

**RESTRICTIONS:** no third file; no change to model, endpoint, schema, payload, timeout, retries, hook instrumentation, deterministic close, gate, ownership, or `message.status`; no separators, JSON repair, best-message selection, raw content in logs/errors, or weakening of semantic decoding. A third-file need or a new design choice means STOP.

## Ordered work for a separately authorized Implement Task

1. In the production function, replace the exactly-one-fragment check with at-least-one check, ordered join, nonempty aggregate check, and existing byte check applied to the aggregate. Leave all loop guards and refusal branch in place.
2. Add focused tests in the one authorized test file. Prefer `Response.model_validate` with synthetic installed-SDK envelopes for multi-part and multi-message cases; keep fake-client tests to verify the full adapter behavior and resource lifecycle. Never use a real key, actual response, keyring, or sending transport.
3. Run `python -m pytest test/test_openai_analysis.py`, then `python -m pytest` using the repository's offline fixtures. Review `git diff --name-only`, `git diff --check`, and the full two-file diff before a separately authorized commit/push.

## Required offline test matrix and acceptance

| Case | Required outcome |
| --- | --- |
| Completed; one assistant message, one schema-valid `output_text` | Accepted `AnalysisCandidates`. |
| Reasoning item followed by valid message | Accepted; reasoning ignored. |
| One message with two ordered fragments making one JSON object | Accepted; no separator inserted. |
| Two assistant messages with ordered fragments making one JSON object | Accepted. |
| Annotation/metadata alongside otherwise valid text | Accepted without interpreting them. |
| Refusal alone or after/beside text | `provider_refusal`; never decode collected text. |
| Global `incomplete` / any other non-`completed` status | `provider_incomplete` / `invalid_output`, respectively. |
| Empty output/content, no text parts, or only empty fragments | `invalid_output`. |
| Non-string text, unknown content part, non-message/tool item, wrong role | `invalid_output`. |
| Malformed aggregate JSON or two complete JSON documents joined | `invalid_output` downstream; no repair or selection. |
| Aggregate over `MAX_RESPONSE_BYTES` or Unicode-encoding failure | `invalid_output`, bounded and no raw text. |
| JSON with valid structural shape but invalid evidence/provenance | `invalid_output` from unchanged decoder. |
| Synthetic no-retry failure and success paths | One provider invocation, no retry for output errors, client close exactly once, request lock released. |
| No-leak checks | No raw output or synthetic secret in exception text, logs, stdout or stderr. |

Tests must include the exact unchanged handling of `message.status` as a regression, not introduce a new message-status policy. The change is accepted only if the two split-valid cases pass and every fail-closed control above still passes. The full suite must remain green; no live test is part of acceptance.

## Dependencies, risks, rollback, and decision gate

No new dependency is needed. Risks are silently skipping a refusal or tool item, accepting multiple unrelated JSON documents, violating aggregate byte bounds, and mistaking this demonstrated compatibility fix for proof of the tenth-smoke cause. The ordered guards, unchanged parser/decoder and adversarial tests contain those risks.

Rollback, if later implementation fails verification: revert only that implementation commit in a controlled Git operation or restore the prior `_structured_text` logic and focused tests; do not change `main`, credentials or operational data. The prior behavior is fail-closed but rejects split-valid envelopes.

**Ambiguities/decisions pending:** none for this exact extraction contract. Implementation, commit/push and any future live smoke require separate explicit authorization. **Out-of-scope discovery:** the prior analysis noted unexamined message-level status; the task explicitly freezes that behavior here.

READY FOR IMPLEMENT
