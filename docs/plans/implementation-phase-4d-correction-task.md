# Phase 4D Correction Task — Metadata-only Prior Bodies

**Status:** Approved for correction implement
**Date:** 2026-09-24
**Baseline implementation:** 35463fc8478a6df3234b9456d024d783f32aea78

## Objective

Correct Phase 4D so a selected PRIOR message with stored normalized_body = NULL may participate as metadata-only context, exactly as allowed by the approved Phase 4 plan and Phase 4B selection behavior.

Target message with normalized_body = NULL remains invalid/no_analyzable_body upstream.

## Exact Scope Lock

Modify only:
1. app/persistence/repositories.py
2. test/test_persistence_repositories.py

## Required behavior

AnalysisSourceSnapshot must be able to represent the exact stored original body state for every selected message:
- target: str (Phase 4B already rejects None target body);
- prior: str or None.

During complete_run revalidation:
- selected source IDs must still match snapshot exactly;
- current stored normalized_body values must still equal snapshot values exactly, including None;
- None must NOT be coerced to empty string for stale detection;
- a metadata-only prior may remain in AnalysisInput with body_excerpt='';
- its full-body digest in the canonical AnalysisInput remains the digest produced by Phase 4B's canonical contract;
- no EvidenceCandidate may target a source whose snapshot original body is None;
- quote classification and evidence validation run only for sources with string bodies.

Do not change Phase 4B/domain code in this correction.

## Tests

Add focused tests covering:
1. target with valid body + prior normalized_body=None can complete successfully when candidates do not cite that prior;
2. metadata-only prior remains part of the selected AnalysisInput/digest;
3. snapshot preserves None rather than coercing it;
4. EvidenceCandidate against metadata-only prior is rejected boundedly;
5. changing metadata-only prior body from None to text after provider snapshot makes completion stale/input_changed;
6. changing text prior to None likewise makes completion stale/input_changed;
7. existing evidence/body validation remains unchanged for normal text messages;
8. no extra derivation or operational rows are created for metadata-only context by itself.

## Restrictions

No domain/model/migration/service changes.
No provider/network/CRM/IMAP/Calendar.
No new dependencies.

## Validation

Run:
python -m pytest test/test_persistence_repositories.py
Then:
python -m pytest

Tracked diff must remain exactly the two Phase 4D files.

## Completion

Commit:
Correct phase 4D metadata-only prior handling

Push only origin/codex-work.

If this cannot be fixed without changing Phase 4B/domain semantics, STOP.