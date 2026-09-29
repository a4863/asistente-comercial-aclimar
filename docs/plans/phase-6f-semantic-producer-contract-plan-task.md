# Phase 6F Semantic Producer Contract Planning Task

**Status:** READY FOR PLAN
**Date:** 2026-09-29
**Depends on:** docs/plans/phase-6f-semantic-output-analysis.md — READY FOR PLAN

## Objective

Produce an implementation-ready plan to align the producer contract with the existing decoder, without weakening any decoder/domain/evidence rule.

The correction may use:

1. tighter static JSON Schema constraints, but only where provider compatibility is demonstrated offline from installed/local evidence; and
2. clearer producer instructions for dynamic/input-dependent invariants that JSON Schema cannot encode.

Do not implement code.
Do not call OpenAI.

## Fixed security and semantic boundary

The existing decoder remains the final authority.

Do NOT relax or change:

- disclosed-alias membership checks;
- evidence start/end bounds;
- exact_text == source slice;
- question_text == cited exact_text;
- evidence/provenance requirements;
- support kind graph;
- support index bounds;
- duplicate-support rejection;
- signal/domain enums;
- commitment/date-certainty consistency;
- timezone-aware date requirements;
- domain DTO invariants;
- source minimization/untrusted-content boundary.

The plan must not special-case the twelfth live response.

## Required planning work

### A. Static schema alignment

Inspect the current response schema and determine which already-existing decoder constraints can be mirrored safely in JSON Schema without changing semantics.

At minimum evaluate:

- nonempty strings via minLength where decoder already requires nonempty;
- domain-specific enum restrictions for signal fields;
- minItems for support collections where decoder already requires at least one support;
- uniqueness constraints only if provider dialect compatibility is demonstrated and they match decoder semantics;
- any other static constraint already enforced locally.

For every proposed schema keyword:

1. show the current decoder rule it mirrors;
2. show the exact schema location;
3. establish provider/SDK Structured Outputs compatibility using installed/local evidence only;
4. if compatibility is not established, do not plan that keyword.

Do not invent unsupported JSON Schema constructs.

### B. Dynamic producer instructions

Plan the smallest precise update to _INSTRUCTIONS that makes existing dynamic decoder rules explicit.

Instructions should cover, without changing business semantics:

- use only aliases disclosed in the input;
- evidence must cite exact nonempty source substrings;
- offsets are zero-based Python character indices into the disclosed excerpt;
- exact_text must exactly equal excerpt[start:end];
- question_text must exactly equal the cited question text;
- support references must point only to already existing candidates of allowed kinds;
- support indexes are zero-based;
- no duplicate support references;
- inference requires fact support;
- proposal requires fact/inference support;
- task/next-step require allowed support;
- signals need valid direct evidence and/or allowed fact support as currently required;
- dates must be timezone-aware;
- commitment certainty/date-expression/resolved-date combinations must match current decoder rules;
- when evidence/support is not justified, leave the candidate collection empty or signal null rather than inventing data.

Do not instruct the model to fabricate facts merely to satisfy schema.

### C. Fixed-smoke contract

The plan must verify that the fixed synthetic smoke has at least one simple decoder-valid output path after the producer-contract update.

Do not make smoke-specific production branches.

Do not force the smoke to always return an empty object if that would reduce coverage of normal structured output behavior.

## Exact candidate Scope Lock

Planning must determine whether implementation can remain within exactly these four files:

1. app/integrations/ai_schema.py
2. test/test_ai_schema.py
3. app/integrations/openai_analysis.py
4. test/test_openai_analysis.py

No other tracked file is authorized.

If a fifth tracked file is required, verdict must be STOP.

## Decoder immutability

Although app/integrations/ai_schema.py contains both schema and decoder code:

- response_schema() may be changed if justified;
- decode_analysis_response() and its helper semantics must remain unchanged.

The plan must explicitly identify which lines/functions are allowed to change and which are frozen.

## Required offline/no-network test matrix

### Schema producer tests

For every added static constraint:
- valid value accepted by schema shape;
- invalid value rejected by schema shape or schema-structure assertion;
- decoder behavior unchanged.

Include candidate cases for:
- empty vs nonempty required strings;
- allowed/disallowed signal enum values;
- mandatory support cardinality where applicable;
- any other accepted static tightening.

### Dynamic instruction contract tests

Assert the exact instruction text contains all approved invariants and does not:
- disclose internal source IDs/digests;
- authorize tool/action execution;
- tell the model to follow embedded email instructions;
- weaken evidence requirements;
- require unsupported data to be invented.

### Decoder regression

Re-run existing semantic negatives unchanged:
- wrong alias;
- bad offsets;
- wrong exact_text;
- question paraphrase;
- invalid support graph/index/duplicates;
- invalid date/timezone;
- inconsistent commitment certainty;
- invalid signal values;
- unsupported candidates.

All must continue to fail exactly as before.

### Success

At minimum:
- minimal empty candidate object remains decoder-valid;
- one valid evidence-backed fact remains decoder-valid;
- one valid supported chain where current tests permit remains decoder-valid;
- adapter still accepts a fully valid synthetic structured response through the unchanged decoder.

### Request contract

Using fake/no-network client inspection:
- request still uses strict json_schema Structured Outputs;
- only intended schema/instruction changes occur;
- model/endpoint/payload mechanics/max tokens/store/timeout remain unchanged;
- no real credential/provider/network.

## Provider compatibility gate

The plan must explicitly document how compatibility of any new JSON Schema keyword is established offline.

If compatibility cannot be established for a keyword:
- omit that keyword;
- retain the decoder rule locally;
- rely on instruction clarification where appropriate;
- do not STOP merely because one optional schema tightening is unavailable, unless the remaining correction would be semantically unsafe or ineffective.

If no safe producer-contract correction remains after this gate, verdict must be STOP.

## Out of scope

Do not change:
- domain DTOs;
- services/routes;
- persistence;
- CLI;
- configuration;
- credential handling;
- activation gate;
- lock;
- retries;
- hooks;
- model;
- endpoint;
- transport;
- diagnostics;
- error taxonomy.

No live smoke is part of implementation acceptance.

## Deliverable

Create only:

docs/plans/phase-6f-semantic-producer-contract-plan.md

Include:

- exact schema constraints to add, with decoder-rule mapping;
- exact schema constraints considered but rejected due to provider compatibility uncertainty;
- exact _INSTRUCTIONS wording/contract changes;
- frozen decoder behavior;
- exact four-file Scope Lock or STOP;
- per-file changes;
- offline/no-network acceptance matrix;
- rollback;
- whether a future thirteenth live synthetic smoke would be justified after accepted implementation;
- verdict: READY FOR IMPLEMENT or STOP.

Commit:

Plan phase 6F semantic producer contract

Push only origin/codex-work.
