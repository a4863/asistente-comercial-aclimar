# Phase 4D Implementation Task — Persist Analysis Derivations and Operational Links

**Status:** Approved for Implement
**Date:** 2026-09-24
**Prerequisites:** Phase 4A1 ACCEPTED; Phase 4A2 ACCEPTED; Phase 4B ACCEPTED; Phase 4C ACCEPTED
**Approved plan:** docs/plans/implementation-phase-4-plan.md
**Support decision:** docs/plans/implementation-phase-4b-support-decision.md

## Objective

Implement only the repository persistence needed to atomically persist a validated Phase 4 analysis result for an already-reserved AnalysisRun.

This phase covers:
- AnalysisSourceEvidence persistence;
- ExtractedFact / Inference / Proposal persistence;
- AnalysisDerivationLink;
- AnalysisSummary;
- creation of Question / Commitment / Task / NextStep according to approved rules;
- AnalysisOperationalLink;
- existing FactSourceEvidence / InferenceSupport / ProposalSupport / OperationalEvidenceLink;
- final completion of the AnalysisRun in the same caller-owned transaction.

No AIService.
No provider call.
No orchestration service.
No live CRM.
No scheduler/UI.

## Exact Scope Lock

Modify only:
1. app/persistence/repositories.py
2. test/test_persistence_repositories.py

No other tracked path may change.

## Core repository contract

Extend AnalysisRepository with a primitive equivalent to:

complete_run(run_id, expected_input_digest, validated_candidates, source_snapshot)

where:
- run already exists in status reserved;
- validated_candidates is the Phase 4B immutable AnalysisCandidates aggregate;
- source_snapshot contains only the exact original stored bodies / source metadata needed to validate evidence for selected sources;
- caller owns the surrounding transaction.

Do not make external calls.

## Required preconditions

Before inserting any derived row:
- run exists and status is reserved;
- run.input_digest == expected_input_digest;
- run target/account/conversation still pass current target validation;
- validated_candidates is an AnalysisCandidates instance;
- every EvidenceCandidate resolves to a source selected by the run input snapshot supplied by caller;
- evidence original-body digest, offsets, exact_text, span digest, and disclosed-prefix eligibility have already been validated by Phase 4B helper or are revalidated here using the same pure contract;
- no cross-account/cross-run support reference;
- no stale source snapshot.

If any check fails: bounded AnalysisRepositoryError, zero derived rows, run not completed.

## Persistence order and atomicity

Persist in deterministic order:
1. AnalysisSourceEvidence rows;
2. ExtractedFact rows + FactSourceEvidence;
3. Inference rows + InferenceSupport;
4. Proposal rows + ProposalSupport;
5. AnalysisDerivationLink rows;
6. AnalysisSummary if present;
7. Question / Commitment / Task / NextStep operational rows;
8. OperationalEvidenceLink;
9. AnalysisOperationalLink;
10. finalize AnalysisRun status/supersession.

All of the above must succeed or roll back together under caller transaction.

Repository must not commit/rollback.

## Evidence persistence

For each unique evidence span used by candidates:
- persist one AnalysisSourceEvidence per unique run+source+span identity;
- reuse it within the same completion call;
- quote_state comes from validated source-local classification;
- do not duplicate raw body/text beyond existing candidate value fields;
- do not persist attachment content.

Question evidence:
- QuestionCandidate.question_text must remain exact evidence text;
- only quote_state=new on target source may create a current Question row;
- quoted or ambiguous questions remain represented only as derivation/candidate provenance; do NOT create Question operational row.

## Typed derivations

### Facts
- each FactCandidate -> ExtractedFact;
- provenance identifies Phase 4 analysis/run without raw source content;
- FactSourceEvidence links source_record_id;
- AnalysisDerivationLink links run + fact + optional AnalysisSourceEvidence;
- no source-free fact allowed.

### Inferences
- each InferenceCandidate -> Inference;
- each SupportRef must resolve to already-created fact derivation according to Phase 4B policy;
- create InferenceSupport using existing schema semantics;
- optional direct evidence may also create/run-link AnalysisSourceEvidence;
- AnalysisDerivationLink links run + inference.

Also persist the three bounded analytical signals as distinct Inference rows when present:
- response_needed
- commercial_risk
- priority
with value_reference equal to approved bounded value and provenance/support/evidence preserved.
They must NOT create Alerts.

### Proposals
- each ProposalCandidate -> Proposal;
- support refs may resolve to fact or inference derivations;
- create ProposalSupport accordingly;
- optional evidence allowed;
- AnalysisDerivationLink links run + proposal.

## Operational objects

### Question
Create only when:
- candidate quote_state == new;
- evidence source is target_source_record_id;
- exact source-local evidence validated.
Initial state: detected.
No automatic answered/open transition.

### Commitment
Create one Commitment per CommitmentCandidate.
Initial state:
- confirmed only if explicit_promise=True AND evidence is unambiguous source evidence;
- otherwise detected.

Persist approved Phase 4 fields:
- responsible_party;
- date_certainty;
- date_expression;
- due_at = resolved_due_at.

Do not use ingestion time to resolve relative dates.
No fulfilled/overdue transition here.

### Task
Create one Task per TaskCandidate.
Initial state: proposed.
Support may point to fact/inference/proposal according to typed SupportRef rules.

### NextStep
Create one NextStep per NextStepCandidate.
Initial state: proposed.
Support may point to fact/inference/proposal.

## Operational provenance

Every AI-created Question/Commitment/Task/NextStep must have:
- AnalysisOperationalLink;
- a valid AnalysisDerivationLink origin;
- existing OperationalEvidenceLink using source/fact/inference/proposal support as appropriate.

The analytical-origin status current_analysis vs superseded_analysis_needs_review remains computed from run chain. Do not mutate lifecycle because later analysis supersedes origin.

## Mapping rule for operational origins

Use deterministic derivation origins:
- Question -> its exact fact derivation;
- Commitment -> fact derivation when explicit source promise supports it; otherwise inference derivation;
- Task -> proposal derivation;
- NextStep -> proposal derivation.

If a needed origin derivation does not already exist from the candidate graph, create the minimum corresponding typed derivation from the candidate itself without fabricating a fact.

Do not create arbitrary hidden facts merely to satisfy links.

## Summary

If summary is present:
- 1..4000 already validated;
- create exactly one AnalysisSummary for run;
- summary_digest = SHA-256(summary_text);
- reject exact equality with any selected original message body/excerpt supplied in source_snapshot;
- no raw-body duplication.

## Replay/idempotency

complete_run may be called only for reserved run.
Calling it on completed/stale/failed run must fail boundedly and create nothing.

Within one run, candidate order is deterministic and persistence order must be deterministic.

Do not deduplicate operational objects across different forced AnalysisRun versions in 4D; append-only forced reanalysis is allowed to create new derived objects. Normal replay should never reach complete_run because 4C reuses completed run.

## Failure handling

- IntegrityError or persistence invariant violation -> bounded AnalysisRepositoryError;
- do not leak SQL/raw exception/provider text;
- caller rollback removes all partial rows;
- finalize run only after all rows flush successfully;
- no AuditEvent in Phase 4D unless already explicitly required by existing repository contract; do not invent new generic audit events.

## Tests

Add focused tests covering at least:
1. fact + evidence persisted and linked;
2. no source-free fact;
3. inference supported by fact;
4. analytical signal becomes Inference with provenance;
5. proposal supported by fact/inference;
6. summary persisted once with correct digest;
7. summary exact body copy rejected;
8. new target question creates Question detected;
9. quoted question creates no Question operational row;
10. ambiguous question creates no Question row;
11. non-target new question creates no current Question row;
12. explicit promise -> Commitment confirmed;
13. ambiguous/non-explicit promise -> detected;
14. commitment D4 fields persisted exactly;
15. task -> proposed;
16. next step -> proposed;
17. every operational row has AnalysisOperationalLink;
18. operational evidence links resolve;
19. typed SupportRef wrong kind/out-of-range rejected even if malformed aggregate is injected;
20. source evidence cross-run/cross-account rejected;
21. duplicate evidence span reused within run;
22. deterministic insertion/order expectations;
23. run finalized only after successful flush;
24. completed run supersedes prior completed run via 4C helper;
25. failure before finalization leaves run reserved until caller rollback;
26. caller rollback removes all derived rows;
27. repository performs no commit/rollback;
28. completed run cannot be completed twice;
29. no Alert/ActionProposal/ApprovalDecision/ExecutionResult created;
30. no AuditEvent created by this phase unless pre-existing contract forces one.

Use isolated SQLite fixtures only.

## Restrictions
- no app/domain changes;
- no models/migrations;
- no services/AIService;
- no provider/network;
- no CRM/IMAP/Calendar;
- no scheduler/UI;
- no new dependencies;
- no cache/untracked inspection.

## Validation
Run:
python -m pytest test/test_persistence_repositories.py
Then:
python -m pytest

Tracked diff must contain exactly:
- app/persistence/repositories.py
- test/test_persistence_repositories.py

## Completion
Commit:
Implement phase 4D analysis result persistence

Push only origin/codex-work.

If implementing this requires model/migration/domain/service changes, STOP.