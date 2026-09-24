# Phase 4B Correction Task — Candidate Support Integrity

**Status:** Approved for correction implement
**Date:** 2026-09-24
**Baseline implementation:** 1fcc50b0136d101bfea90bce974fc6e77b1c4a1b

## Objective
Correct two Phase 4B contract gaps without expanding scope.

## Exact Scope Lock
Modify only:
1. app/domain/email_analysis.py
2. test/test_email_analysis.py

## Correction 1 — Support indexes must resolve
`support_indexes` must not merely be non-negative integers.

At AnalysisCandidates aggregate validation time, every support index must resolve against the approved support collection used by the DTO contract. Use one deterministic convention and document it in code/tests. Prefer indexes into `facts` for inference/proposal support unless the approved Phase 4 plan requires a broader typed support space.

Requirements:
- out-of-range support index rejected;
- duplicate indexes rejected unless there is an explicit approved reason;
- deterministic tuple ordering;
- no silent dropping/remapping;
- empty support tuple allowed only where the approved candidate type semantically permits source evidence alone.

If the existing plan makes the support target ambiguous between facts/inferences/other candidate sets, STOP rather than inventing a new semantic.

## Correction 2 — Bounded analytical signals need provenance
`response_needed`, `commercial_risk`, and `priority` must remain bounded Phase 4 inferences with evidence/support sufficient for later persistence as Inference records.

Do not leave them as provenance-free scalar strings.

Implement a provider-neutral immutable DTO shape that preserves:
- bounded value;
- support indexes and/or validated EvidenceCandidate;
- exact enum set already approved.

The aggregate AnalysisCandidates contract should expose at most one candidate for each of the three analytical signals.

Do not create persistence rows in Phase 4B.
Do not add repository/service logic.

## Tests
Add/adjust tests covering at least:
- valid support index resolves;
- out-of-range support rejected;
- duplicate support indexes rejected;
- deterministic support ordering/shape;
- response_needed valid bounded value with evidence/support;
- commercial_risk valid bounded value with evidence/support;
- priority valid bounded value with evidence/support;
- invalid enum rejected;
- signal with neither evidence nor support rejected;
- frozen/immutable behavior preserved.

Run:
python -m pytest test/test_email_analysis.py
then:
python -m pytest

Tracked diff must remain exactly the two Phase 4B files.

Commit:
Correct phase 4B candidate support integrity

Push only origin/codex-work.

If correcting this requires persistence/model/service changes, STOP.