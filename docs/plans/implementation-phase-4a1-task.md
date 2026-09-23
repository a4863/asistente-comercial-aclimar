# Phase 4A1 Implementation Task — Analysis Foundation ORM Model

**Status:** Approved for Implement
**Date:** 2026-09-23
**Approved plan:** docs/plans/implementation-phase-4-plan.md
**Plan commit:** 6d44fa6a430bfab405852dd9a751fdd7549f0afd

## Objective

Implement only the Phase 4 ORM/data-model foundation defined in §3 of the approved Phase 4 plan.

This subphase adds the logical documentation and SQLAlchemy model definitions/constraints.

Do NOT create Alembic revision 0007 yet.
Do NOT add repositories, domain selection, AIService, orchestration, provider code, CRM calls, scheduler, UI, or external actions.

## Exact Scope Lock

Modify only:

1. docs/data-model.md
2. app/persistence/models.py
3. test/test_persistence_models.py

No other tracked path may change.

## Required model additions

Implement the approved ORM representation for:

### AnalysisRun
Exact approved fields/semantics from Phase 4 plan:
- account_scope
- target_source_record_id
- conversation_id
- run_version
- input_digest
- contract_version
- policy_version
- request_mode: automatic|manual|force
- status: reserved|completed|stale_retryable|failed_retryable
- failure_code: input_changed|provider_failure|invalid_output|persistence_failure|interrupted or NULL
- supersedes_run_id
- completed_at
- created_at
- updated_at

Required CHECK/unique/index semantics must match the approved plan.

### AnalysisSourceEvidence
- analysis_run_id
- source_record_id
- start_offset
- end_offset
- body_digest
- span_digest
- quote_state: new|quoted|ambiguous
- required uniqueness/indexes from plan.

Offsets are original normalized_body coordinates; no body copy.

### AnalysisDerivationLink
- run association
- exactly one of extracted_fact_id/inference_id/proposal_id
- optional evidence_id
- required uniqueness/index semantics.

### AnalysisSummary
- one per run
- summary_text length 1..4000
- summary_digest
- no raw email body field.

### AnalysisOperationalLink
- run association
- derivation_link_id
- operational_type question|commitment|task|next_step
- exactly one matching operational FK
- uniqueness/index semantics.

### Commitment extension
Add nullable legacy-compatible fields:
- responsible_party: self|counterparty|unknown
- date_certainty: exact|resolved_relative|uncertain|none
- date_expression <=255

Physical/model constraints must enforce the combinations approved in the plan where SQL CHECKs are appropriate:
- resolved_relative -> due_at non-null + date_expression non-null
- uncertain|none -> due_at null
- exact -> due_at non-null
- legacy rows with all new fields NULL remain valid.

Do not fabricate backfill values.

## Relationship/deletion rules

Use the exact FK directions and RESTRICT semantics from the approved plan.

Do not add cascade deletion that would erase append-only Phase 4 history.

Do not alter existing Phase 3D semantics.

## Documentation

Update docs/data-model.md narrowly to document:
- AnalysisRun lifecycle and replay/version identity;
- evidence spans;
- summary artifact;
- derivation and operational links;
- commitment D4 fields;
- operational analytical provenance current vs superseded is derived from run chain, not lifecycle mutation.

Do not document unimplemented provider/CRM/UI behavior as implemented.

## Tests

Add focused ORM/model tests covering at least:

1. valid AnalysisRun states;
2. invalid request_mode;
3. invalid status;
4. completed requires completed_at and no failure_code;
5. reserved requires no completed_at/failure_code;
6. retryable states require bounded failure_code and no completed_at;
7. invalid SHA-256 shape rejected;
8. run_version/contract_version/policy_version >0;
9. unique run version per account+target;
10. supersedes self/reference constraints where ORM/schema can enforce them;
11. valid evidence span;
12. invalid offsets;
13. invalid quote_state;
14. derivation link exactly-one constraint;
15. summary 1..4000;
16. operational link type/FK match;
17. commitment valid self/counterparty/unknown;
18. commitment exact date rules;
19. resolved_relative rules;
20. uncertain/none rules;
21. legacy commitment with new fields NULL remains valid;
22. no cascade behavior that contradicts RESTRICT/history.

Use isolated SQLite fixtures only.

## Restrictions

- no migration file;
- no repository changes;
- no service/domain changes;
- no new dependencies;
- no provider;
- no live CRM;
- no test execution against user DB;
- no cache/untracked inspection.

## Validation

Run:

python -m pytest test/test_persistence_models.py

Then:

python -m pytest

Inspect tracked diff using only:
- git status --short --untracked-files=no
- git diff --name-only

Exact tracked diff must contain only the three authorized paths.

## Completion

Commit:

Implement phase 4A1 analysis foundation models

Push only origin/codex-work.

If a migration or fourth tracked file is required, STOP.
