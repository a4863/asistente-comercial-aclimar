# Phase 6F — invalid output after Responses return

**Mode:** offline analysis only. **Trigger:** the tenth separately authorized live smoke returned `smoke_failed:invalid_output`; the SDK call returned to the adapter. This result alone does not identify which post-return check failed. No live response, real credential, keyring, operational configuration/database, provider, or network was accessed here.

## 1. Objective, interpretation, and evidence

Enumerate every current post-return `invalid_output` route, compare the parser with the installed `openai==3.17.0` Responses model and the local strict schema/decoder, and determine whether a narrow correction can be justified offline. This is not authorization to change code or run another smoke.

Consulted `AGENTS.md`, `docs/plans/phase-6f-invalid-output-analysis-task.md`, relevant remote-AI and testing provisions of `docs/functional-spec.md`, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, the Phase 5 provider task/plan, `app/integrations/openai_analysis.py`, `app/integrations/ai_schema.py`, `app/domain/email_analysis.py`, `test/test_openai_analysis.py`, `test/test_ai_schema.py`, and the installed SDK response model sources. No required source was missing.

## 2. Current post-return decision tree

After `client.responses.create(**request_kwargs)` returns, the adapter checks its soft deadline first. Deadline expiry yields `timeout`, **not** `invalid_output`. The remaining `invalid_output` branches are:

1. `_structured_text`: global `status` is not `completed` (except `incomplete`, which yields `provider_incomplete`); `output` is not a list; an output item is neither `reasoning` nor an assistant `message`; a message `content` is not a list; a content part is neither a string-valued `output_text` nor a `refusal` (the latter yields `provider_refusal`); the total number of `output_text` parts is not **exactly one**; that sole text is empty; UTF-8 encoding of it fails; or its bytes exceed `MAX_RESPONSE_BYTES` (160,000). Reasoning items are skipped. This function does not inspect message-level status, text annotations, response metadata, or the SDK `output_text` helper.
2. `json.loads(text)`: malformed JSON or a supported parse exception within the adapter catch becomes `invalid_output`.
3. `decode_analysis_response(parsed, projection)`: the bounded JSON check, exact top-level/nested object shape, version, types, length/depth/item/byte bounds, dates, aliases, evidence spans, support kinds/indexes/duplicates/cycles, domain DTO invariants and related checks may fail. `AISchemaError` and the other caught decoder exceptions become `invalid_output`. `json.loads` can produce valid JSON that the local decoder must reject. An unexpected exception outside the specified catch is not safely attributable to this bounded code.

Refusal and incomplete status have separate codes. A `failed`, `queued`, `in_progress`, `cancelled`, or absent status maps to `invalid_output`; the installed response model permits these status values. The adapter also deliberately rejects tool/non-message output rather than treating it as structured analysis.

## 3. Installed SDK envelope versus parser assumptions

Installed `openai/types/responses/response.py` defines `Response.output` as a list of `ResponseOutputItem` whose length/order depends on the response. Its documented `output_text` property concatenates text from **all** `output_text` parts in message items; it does not itself enforce the adapter's refusal/non-message guards. `ResponseOutputMessage.content` is a list of `ResponseOutputText | ResponseOutputRefusal`; the text part has an `annotations` list. A separate `ResponseReasoningItem` is a valid output item. Therefore the SDK object shape (`status`, `output`, `message.role`, `content`, `part.type`, `part.text`) matches the adapter's attribute access, but the model type does **not** guarantee exactly one message or one text part. Global response metadata and text annotations are supported and ignored safely by the current parser.

The local request uses `text.format` with `type=json_schema`, `strict=True`, and `response_schema()`. This constrains the intended JSON payload, not, from installed model definitions or existing local evidence, the count of SDK output items or text parts. No offline evidence proves that this particular model/service actually split the tenth output. Nor does a successful SDK return prove a valid schema-conformant payload: refusal, incomplete generation, non-JSON text, or a locally invalid semantic candidate remain possible. The SDK helper cannot simply replace `_structured_text`, because it silently skips non-text items/refusals and would weaken fail-closed checks if used alone.

## 4. Schema and decoder compatibility

`response_schema()` and `decode_analysis_response()` agree on the twelve candidate fields plus `schema_version=1`, exact object keys, array element shapes, nullability, major enums and declared string/item limits. A minimal all-empty candidate object with null summary/signals is both schema-shaped and accepted by the decoder for the fixed synthetic smoke projection; this was reproduced with a validated SDK `Response` object.

The schema intentionally cannot prove all local business/evidence invariants. It permits, for example, an alias not present in the disclosed request, offsets/text not matching the source excerpt, a reference index beyond an existing collection, empty support arrays where a domain candidate requires provenance, inconsistent due-date certainty, a question whose text differs from its evidence, or a date string with no timezone. Such JSON may satisfy the structural schema yet must fail the local decoder. This is the approved fact/evidence/security boundary, **not** justification to relax the decoder to make a smoke pass. A tenth-smoke semantic failure is plausible but unproven without prohibited live-content inspection.

## 5. Offline reproduction matrix

No-network checks used synthetic fixed data, `Response.model_validate` from the installed SDK, and the actual `_structured_text` → `json.loads` → `decode_analysis_response` path. Only fixed labels and bounded results were recorded. `helper_text_nonempty` was checked separately, never printed as content.

| SDK-valid synthetic case | Current bounded outcome | Finding |
| --- | --- | --- |
| Completed, one assistant message, one schema-shaped JSON text | accepted | Normal SDK object shape works. |
| Reasoning item followed by that message | accepted | Reasoning is skipped correctly. |
| One message with two `output_text` parts splitting a single valid JSON object | `invalid_output` | Demonstrated count mismatch; SDK aggregate text is nonempty. |
| Two assistant messages splitting a single valid JSON object | `invalid_output` | Same mismatch across output items. |
| Text with a valid synthetic annotation and response metadata | accepted | These fields do not cause rejection. |
| Refusal content | `provider_refusal` | Separate fail-closed path. |
| Globally incomplete response | `provider_incomplete` | Separate fail-closed path. |
| Malformed JSON text | `invalid_output` | Correctly rejected after extraction. |
| Structurally schema-shaped JSON with wrong source evidence | `invalid_output` | Correct local semantic rejection. |

The two split-text cases demonstrate an SDK-model-permitted envelope containing one concatenated schema-shaped payload that the current parser rejects. They do **not** establish that strict Structured Outputs produced that envelope in the tenth live call. Existing tests largely use `SimpleNamespace` with one message/one part; they cover refusal/incomplete and many decoder failures but do not cover SDK-validated split-text envelopes. Prior pinned SDK tests exercise transport/request/response parsing, not this successful multi-part `Response` extraction.

## 6. Proposed minimal correction for a separate plan

The offline mismatch justifies planning a narrow extraction-only correction in `app/integrations/openai_analysis.py` plus focused tests in `test/test_openai_analysis.py`. Traverse the existing allowlisted envelope in order; keep the global completed check, reasoning skip, assistant-role requirement, refusal and unknown/tool-item rejection, and bounded errors. Collect only string `output_text` parts from allowed message items. Require at least one nonempty aggregate, join in output/content order, apply the existing UTF-8/160,000-byte bound to the aggregate, and run the **unchanged** `json.loads` and `decode_analysis_response` checks. Do not use `response.output_text` as the sole validator. Concatenated separate JSON documents must still fail parsing; there must be no selection of a “best” message, JSON repair, schema relaxation, or coercion.

This is a candidate for a separately approved exact plan, not an implementation decision made here. It is supported by the installed SDK's aggregation semantics and the synthetic mismatch, while preserving the current security boundary. It may not resolve the tenth smoke if the actual cause was malformed JSON or semantic candidate evidence.

## 7. Scope Lock, dependencies, risks, and tests

**IN SCOPE now:** creation of this report only. **OUT OF SCOPE now:** production code, tests, other documentation, dependencies, provider calls, live response/credential/config/database, and another smoke. **RESTRICTIONS:** no model/endpoint/schema/payload/timeout/retry/gate/ownership changes; no raw provider text in logs or error codes; no weakening of evidence/provenance validation.

**Candidate future Scope Lock for an approved correction:** `app/integrations/openai_analysis.py` and `test/test_openai_analysis.py` only. If a later plan needs another file, that requires a new decision. No new dependency is needed.

Offline tests for that plan: validated SDK `Response` with one text, reasoning plus text, split text within one message and across messages, annotations/metadata, empty/no text, two complete JSON documents, refusal (including alongside text), incomplete/failed status, non-message/tool output, invalid role/part types, aggregate byte/Unicode bounds, malformed JSON, locally invalid semantic candidates, no retry, bounded/no-leak errors, and deterministic client close/lock release. Run focused provider tests and then the full offline suite only in an authorized implementation task. No real integration is required.

Risks: accepting mixed or tool output by blindly using SDK `output_text`; accidentally accepting multiple independent JSON results; losing refusal precedence; exceeding bounds after joining; masking semantic violations as an envelope problem; and assuming this demonstrated mismatch explains the unseen tenth response. Keep every existing downstream local check.

**OUT-OF-SCOPE DISCOVERY:** a response-level `completed` status does not by itself verify each message-level status; the current parser ignores message status. No evidence here shows it caused this smoke. A later plan should explicitly decide whether to retain or add that check rather than silently changing it.

## 8. Ambiguities, decisions, and verdict

The exact tenth-smoke failure branch cannot be identified without inspecting the live response, which this task forbids. That uncertainty does not block a plan for the independently reproduced split-text incompatibility, but it blocks any claim that the correction will make a subsequent smoke pass. No functional or security decision is needed to preserve the existing fail-closed semantics; the exact extraction contract and tests still require plan approval. Another live synthetic smoke is **not authorized now**; it could be considered only after a separately approved, implemented, offline-verified correction and fresh explicit live authorization.

READY FOR PLAN
