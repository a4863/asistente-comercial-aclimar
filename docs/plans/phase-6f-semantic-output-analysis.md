# Phase 6F — semantic output failure analysis

**Mode:** offline Analyze Task; no live provider, credential, keyring, operational configuration/database, network, or twelfth-response inspection. **Trigger:** the bounded twelfth result `smoke_failed:provider_output_semantic_failure`.

## 1. Objective, context, and interpretation

Determine whether the fixed synthetic smoke's producer contract (`response_schema()` plus `_INSTRUCTIONS`) can admit JSON that the existing decoder/domain rejects, and whether a producer-side correction is justified without weakening provenance. The bounded result establishes only that the SDK returned, extraction and `json.loads` succeeded, and `decode_analysis_response(parsed, projection)` failed. It does not identify the rejected field or rule, or prove provider fault.

## 2. Sources and current state

Consulted `AGENTS.md`, `skills/analyze-task/SKILL.md`, `docs/plans/phase-6f-semantic-output-analysis-task.md`, `docs/plans/phase-6f-twelfth-live-smoke-failure.md`, the Phase 5A task and provider decisions, relevant requirements in `docs/functional-spec.md`, `docs/security.md`, and `docs/testing-strategy.md`, and the current `app/integrations/ai_schema.py`, `app/domain/email_analysis.py`, `app/integrations/openai_analysis.py`, `test/test_ai_schema.py`, and `test/test_openai_analysis.py`. No required source was missing. This is an implemented decoder and schema, not `NO IMPLEMENTATION YET`.

The provider request supplies the general instruction to distinguish facts/inferences/proposals and cite exact spans. It sends the fixed smoke through `project_analysis_input(_fixed_smoke_input())` with the strict schema. The smoke projection has one target alias `m0`, no prior aliases, one fixed synthetic body excerpt, and no sender, recipients, subject, or message date. Internal source IDs and digests are not disclosed. `_INSTRUCTIONS` does not currently spell out the decoder's alias set, zero-based character-offset convention, exact question/evidence equality, allowed support graph and indices, date-certainty relationships, or the option to leave unsupported collections empty.

## 3. Decoder invariant map and schema gap

The schema and decoder agree on exact object keys and required/null fields, candidate collection shapes, `schema_version=1`, maximum string lengths and array item counts, top-level fact/inference/proposal/question/commitment/task/next-step/mention shapes, declared kind enums, nonnegative numeric indices, and major commitment/mention enums. Structural conformity does **not** imply a valid `AnalysisCandidates` graph.

| Invariant checked after JSON parse | Schema representation | Gap relevant to fixed smoke |
| --- | --- | --- |
| Bounded nested JSON, total response bytes, exact Python container/scalar types | Field shapes and per-field length/item caps | Global byte/depth bounds are local only; booleans used as integer indices are rejected locally. |
| Required nonempty strings | `type: string` plus `maxLength`; no minimum length | Empty non-null candidate text can satisfy the schema but not `_text`/domain. |
| Evidence alias must be one disclosed alias | String with `maxLength: 2` | `m1` or another short undisclosed alias is schema-shaped but impossible for this one-message projection. Alias→source ID remains local. |
| Evidence has `0 <= start < end <= len(body_excerpt)` and `exact_text == body_excerpt[start:end]` | Nonnegative integer offsets; bounded string | Relational bounds and exact slice equality are not encoded. Digest is computed locally; no provider digest is accepted. |
| Question text equals its evidence's exact text | Both are strings with evidence object | Paraphrased question text is schema-shaped but rejected. `classify_quote` derives `new/quoted/ambiguous` locally; a correctly evidenced quoted question is classified, not automatically rejected by this decoder. |
| Support references are unique, in range, and type-restricted by consumer | `kind` enum and nonnegative index; arrays can be empty | Inference requires at least one fact support; proposal requires fact/inference support; task/next step require fact/inference/proposal support; signals allow fact support and/or direct evidence. Duplicate, missing, forward/out-of-range, or disallowed-kind refs are schema-shaped. Facts rely on direct evidence, not support refs. |
| Signal values use domain-specific enums | Bounded arbitrary string | For example, `priority=medium` is schema-shaped but not a permitted priority value; response-needed/risk/priority have distinct allowed sets. |
| Dates parse as timezone-aware ISO datetimes; commitment certainty and date fields are consistent | Nullable bounded date string; certainty enum | Naive or malformed date strings and `exact`/`resolved_relative` without a resolved due date are schema-shaped but rejected. `resolved_relative` also requires a date expression; `uncertain`/`none` require null resolved date. Valid offsets are normalized to UTC locally; a non-UTC offset alone is not rejected. |
| Candidate-specific domain requirements | Mostly type/shape constraints | Nonempty support for inference/proposal/task/next step, nonempty signal evidence-or-support, enum restrictions and cross-field constraints arise in immutable domain constructors. |

The fixed schema cannot express input-dependent excerpt slices, alias membership, support-index bounds, cross-collection rules, or truth of a commercial interpretation as static JSON Schema alone. The decoder must remain the final authority. The fact that `strict=True` was requested does not prove semantic validity.

## 4. Fixed-smoke-valid output space

The minimal object with `schema_version=1`, null `summary` and signals, and empty candidate arrays is accepted for the fixed projection. A nonempty fact with direct evidence whose alias is `m0` and whose offsets/text exactly match a nonempty span of the fixed excerpt is also accepted locally. Dependent inference/proposal/task/next-step candidates can be accepted only with the allowed in-range support chain; signals need valid fact support or direct evidence. Question text must be identical to its cited excerpt, not a paraphrase. Dates must be null absent a safely representable timezone-aware value; certainty rules still apply. The synthetic message itself does not justify assuming a source commitment or a literal question merely because its imperative asks for confirmation. The decoder does not itself prove commercial truth of a well-shaped candidate, so acceptance is not factual endorsement.

## 5. Offline reproduction matrix

Used `python -B` with in-memory copies of the fixed smoke projection and candidate object. No test runner, file output, network transport, keyring, provider client, operational setting, or live response was used. Only fixed case labels and `accepted`/`rejected` were printed. `jsonschema` is not installed, so “schema-shaped” below is based on direct inspection of `response_schema()` rather than an independent validator; no package was installed.

| Synthetic case | Decoder result | Why the schema shape permits it |
| --- | --- | --- |
| Minimal empty candidate object; fact with valid `m0` full-body evidence | accepted; accepted | Both satisfy existing shape and local checks. |
| Start offset shifted while exact text stays the full excerpt; wrong exact text; undisclosed `m1` alias | rejected; rejected; rejected | No slice equality or request-specific alias enum. |
| Question paraphrase with valid evidence | rejected | No `question_text == exact_text` relation. |
| Inference with empty support; task with missing fact index; inference referring to an existing proposal instead of a fact | rejected; rejected; rejected | No nonempty/collection-specific/in-range reference rule. |
| Commitment `exact` with null due date; task with naive datetime | rejected; rejected | No certainty/date dependency or timezone-aware parse rule. |
| Task with empty support; priority value outside its domain enum; duplicated task support | rejected; rejected; rejected | No minimum support, signal-specific enum, or uniqueness rule. |

The earlier `test/test_ai_schema.py` suite also covers invalid evidence, quoted question classification, missing/out-of-range supports, invalid dates and other semantic failures with synthetic data. These reproductions establish a real producer/consumer contract gap, **not** which gap caused the twelfth result. The live response is deliberately unavailable and must not be inferred from the matrix.

## 6. Proposed minimal correction for a separate plan

**READY FOR PLAN**, not approval to implement. Plan a producer-boundary alignment in two complementary, non-relaxing parts:

1. Mirror only static, existing decoder constraints in `response_schema()` where the pinned provider's strict Structured Outputs subset can be verified offline: domain-specific signal enums, nonempty strings and mandatory support cardinality are candidates. Do not add unsupported JSON Schema constructs blindly or change domain semantics. Preserve required fields, nullability, bounds, no tools/actions, and the versioned contract.
2. Make the currently implicit *dynamic* rules explicit in `_INSTRUCTIONS`: use only disclosed aliases; cite exact, nonempty source substrings with zero-based Python-character offsets and matching `exact_text`; make `question_text` exactly its cited text; reference only existing zero-based candidates with the approved kind graph and no duplicate refs; use timezone-aware datetimes with the current commitment certainty rules; leave unsupported candidates and signals empty/null rather than inventing evidence. These instructions convey existing decoder requirements, not authority from email content.

Plan verification must decide exact provider-supported schema keywords using already installed/local evidence and prepare offline schema-shaped/decoder-valid and negative test cases. If provider compatibility cannot be established, retain the decoder and document an instructions-only alternative for explicit approval; do not silently weaken validation. Neither part guarantees the twelfth live rejection's cause or that a thirteenth attempt would pass. The producer-contract mismatch independently justifies a plan, while implementation and another live attempt require separate approvals.

## 7. Candidate Scope Lock, dependencies, risks, tests, and exclusions

**IN SCOPE for a future plan only:** `app/integrations/ai_schema.py` and `test/test_ai_schema.py` for schema/decoder compatibility tests; `app/integrations/openai_analysis.py` and `test/test_openai_analysis.py` for instruction/request-contract tests. The decoder's behavior must not change even though its file is in that candidate scope. No other file is presently justified.

**OUT OF SCOPE:** the current analysis may create only this report. Future correction must not touch domain DTOs, services, persistence, config, credentials, gate, CLI, retries, hooks, model, endpoint, transport, or external systems. No semantic exception categories or raw failure details are authorized.

**RESTRICTIONS:** no relaxation of evidence/provenance, offsets, alias validation, quoted-text classification, support indices/kinds, date certainty, domain invariants, or untrusted-data boundary. No live/provider call, operational data, new dependency, response inspection, or thirteenth smoke under this analysis.

**Dependencies and risks:** the local projection, immutable domain DTOs, strict schema dialect accepted by the configured provider, and pinned SDK request shape. A too-specific instruction could suppress valid commercial candidates; a schema keyword unsupported by the provider could convert a semantic failure into a request failure; advice about offsets may be misread as byte indexing; a “smoke-only always-empty” output would weaken the smoke's coverage. Future tests should assert schema structure/provider-compatibility offline, minimal valid and full candidate graph, all matrix rejections, unchanged decoder acceptance/security, exact sent instructions, no source/secret leakage, and no network via fake transport. Do not use a live smoke in normal tests.

**OUT-OF-SCOPE DISCOVERY:** the bounded twelfth code is insufficient to identify the actual failing invariant. A separate semantic-family diagnostic could be considered later, but it would require its own security review and approval; it is not part of this producer-contract proposal.

**Ambiguities and pending decisions:** no business/domain decision is needed to plan making the producer describe the already-approved decoder rules. Provider support for any newly proposed schema keyword is a required technical validation gate during planning, not an assumption. If it fails or the proposed instructions would alter commercial semantics, STOP and request a new decision.

## 8. Live-test gate and verdict

Another synthetic live smoke would be justified only after an exact plan is separately approved, a bounded correction is implemented, its offline/no-network tests pass, and the operator grants a new one-shot authorization. It is not authorized here. Phase 6F remains unaccepted and commercial activation unauthorized.

READY FOR PLAN
