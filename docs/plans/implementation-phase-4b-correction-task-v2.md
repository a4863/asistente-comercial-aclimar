# Phase 4B Correction Task — Candidate Support Integrity (Resolved)

**Status:** Approved for correction implement
**Date:** 2026-09-24
**Baseline implementation:** 1fcc50b0136d101bfea90bce974fc6e77b1c4a1b
**Decision authority:** docs/plans/implementation-phase-4b-support-decision.md

## Objective

Correct the Phase 4B candidate support model using typed support references, and give the three bounded analytical signals provenance.

## Exact Scope Lock

Modify only:

1. app/domain/email_analysis.py
2. test/test_email_analysis.py

## Typed support references

Introduce an immutable DTO equivalent to:

SupportRef(
    kind: Literal["fact", "inference", "proposal"],
    index: int,
)

Rules:
- zero-based indexes;
- index >= 0;
- duplicate identical refs rejected;
- tuple/collection immutable;
- order deterministic and preserved;
- every ref must resolve against the correct AnalysisCandidates collection.

Approved support policy:
- InferenceCandidate: facts only.
- ProposalCandidate: facts and/or inferences.
- TaskCandidate: facts, inferences, proposals.
- NextStepCandidate: facts, inferences, proposals.
- FactCandidate: no SupportRef; source evidence only.
- response_needed/commercial_risk/priority signal candidates: facts and/or source evidence.

Do not silently coerce old integer support indexes.

At AnalysisCandidates aggregate validation time, validate all SupportRef targets and allowed kinds.

## Analytical signals with provenance

Replace provenance-free scalar-only response_needed/commercial_risk/priority representation with immutable candidate DTO(s) that preserve:
- bounded value;
- SupportRef tuple and/or EvidenceCandidate;
- at least one provenance path: support refs or evidence.

Approved value sets remain:
- response_needed: yes|no|uncertain
- commercial_risk: none|low|medium|high|unknown
- priority: low|normal|high|urgent

AnalysisCandidates may contain at most one of each signal.

These remain analytical inferences and do not create persistence rows in Phase 4B.

## Validation requirements

Reject:
- out-of-range SupportRef;
- invalid support kind;
- disallowed support kind for candidate type;
- duplicate identical SupportRef;
- signal with neither support nor evidence;
- invalid bounded signal value.

Preserve frozen/immutable DTO behavior.

## Tests

Add/adjust tests for:
- valid fact -> inference support;
- proposal supported by fact and inference;
- task/next step supported by proposal;
- out-of-range support;
- wrong-kind support;
- duplicate support;
- immutable support tuple;
- valid response_needed with evidence only;
- valid commercial_risk with fact support;
- valid priority with fact support;
- invalid signal enum;
- signal with no provenance;
- existing Phase 4B selection/digest/evidence behavior remains unchanged.

## Restrictions

No persistence/model/migration/repository/service/provider/CRM changes.

## Validation

Run:

python -m pytest test/test_email_analysis.py

Then:

python -m pytest

Tracked diff must remain exactly:
- app/domain/email_analysis.py
- test/test_email_analysis.py

## Completion

Commit:

Correct phase 4B typed support references

Push only origin/codex-work.

If this requires persistence/model changes, STOP.
