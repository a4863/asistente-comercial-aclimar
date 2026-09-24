# Phase 4B Support Reference Decision

**Status:** APPROVED
**Date:** 2026-09-24

## Decision

Use **typed support references** in Phase 4B.

A support reference must identify both:
- support kind;
- zero-based index within that candidate collection.

Approved support kinds:
- fact
- inference
- proposal

## Semantics

A support reference is conceptually:

SupportRef(kind, index)

where:
- kind='fact' points into AnalysisCandidates.facts
- kind='inference' points into AnalysisCandidates.inferences
- kind='proposal' points into AnalysisCandidates.proposals

Indexes are zero-based and validated against the referenced collection.

## Rules

- Every support reference must resolve.
- Negative or out-of-range indexes are invalid.
- Duplicate identical references are invalid.
- Ordering must be deterministic and preserved.
- No silent remapping or dropping.
- Candidate types may restrict which support kinds they accept according to Phase 4 semantics.

Minimum approved support policy:
- InferenceCandidate may be supported by facts.
- ProposalCandidate may be supported by facts and/or inferences.
- TaskCandidate may be supported by facts, inferences, and/or proposals.
- NextStepCandidate may be supported by facts, inferences, and/or proposals.
- response_needed/commercial_risk/priority inference signals may be supported by facts and/or source evidence.
- A FactCandidate is source-evidence-backed and does not use candidate support references.

This preserves source -> extraction -> inference -> proposal without fabricating facts.

No persistence schema change is authorized by this decision. This is a Phase 4B DTO/domain decision only.
