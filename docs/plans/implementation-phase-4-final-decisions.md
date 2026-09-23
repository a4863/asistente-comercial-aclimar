# Phase 4 Final Decisions — Closing Remaining Planning Ambiguities

**Status:** APPROVED
**Date:** 2026-09-23

**Parent decisions:** docs/plans/implementation-phase-4-decisions.md  
**Blocked plan:** docs/plans/implementation-phase-4-plan.md

This document resolves the remaining ambiguities identified in the blocked Phase 4 final planning attempt.

## P4-1 — Bounded inference values

Approved exact values:

### response_needed
- yes
- no
- uncertain

Meaning:
- absence of a response_needed inference = not evaluated;
- uncertain = evaluated but evidence is insufficient for yes/no.

### commercial_risk
- none
- low
- medium
- high
- unknown

Meaning:
- absence = not evaluated;
- unknown = evaluated but risk level cannot be determined.

### priority
- low
- normal
- high
- urgent

Meaning:
- absence = not evaluated;
- values represent analytical prioritization, not an external action authorization.

All three remain Inference-class outputs, not facts and not direct Alerts.

## P4-2 — Same-input manual reanalysis

Normal manual reanalysis:
- if canonical input digest + contract/policy version exactly match a completed run, reuse the completed result;
- do not call AI again;
- do not create duplicate derivations/operational records.

Explicit force_reanalysis:
- may call AI again even when canonical input digest is identical;
- creates a new append-only AnalysisRun version;
- previous run/results remain preserved;
- new output may supersede prior derivations but never silently overwrite or delete history.

A repeated normal manual request is therefore deduplicated.

## P4-3 — Exact-question evidence and quoted history

Authoritative evidence coordinates are anchored to the original locally stored message body, not to the remote-AI excerpt.

Persist sufficient bounded evidence to validate:
- source_record_id;
- start_offset;
- end_offset;
- digest/text-match reference.

AI may identify a candidate in disclosed text, but the application must resolve and validate it against the original stored body before persistence.

Quoted-history rule:
- no sophisticated quote/signature remover is authorized in Phase 4;
- if the application cannot conservatively determine that the question is newly asked rather than historical quoted content, it must not automatically classify it as a newly asked current Question;
- ambiguous cases remain candidate/ambiguous rather than being silently promoted.

Question closure still requires later source evidence or explicit user confirmation.

## P4-4 — 30,000-character budget and missing dates

The 30,000-character disclosure budget applies only to message text bodies, not metadata or canonical separators.

Selection:
1. current/new-or-changed target message first;
2. then prior messages from newest to oldest;
3. maximum six prior messages;
4. never exceed 30,000 body characters total.

If the target body alone exceeds 30,000 characters:
- keep the first 30,000 characters of the target body;
- include no prior-message body context.

Canonical metadata/separators are still included in the final canonical input/digest but do not consume the 30,000 body-character budget.

Relative commitment dates:
- resolve only against a reliable source-message date;
- if no reliable source date exists, do not substitute local ingestion time;
- date certainty remains uncertain;
- resolved_due_at remains null.

## P4-5 — Operational objects from superseded analysis

Question, Task, Commitment, and NextStep lifecycles are not silently changed because their originating analysis is superseded.

They remain in their current lifecycle state.

Their provenance must explicitly expose that the originating analysis run/derivation is superseded so a later UI can distinguish:
- supported by current analysis;
- originating from superseded analysis and requiring review.

Supersession alone does not imply:
- answered;
- completed;
- fulfilled;
- cancelled;
- dismissed.

## P4-6 — Derived summary storage

Do not store long summaries in 255-character value_reference fields.

Add a dedicated analysis-derived textual artifact linked to AnalysisRun for summary-like content.

MVP summary constraints:
- maximum 4,000 characters;
- derived content only;
- must not duplicate the raw email body;
- append-only/versioned with its AnalysisRun;
- no execution authority.

Existing ExtractedFact / Inference / Proposal value_reference fields remain for brief structured values/references.

## Consolidated authority

Phase 4 planning is now governed by:
- D1-B, D2-B, D3-A, D4-A, D5-A, D6-A, bounded D7-B, D8-A, D9-B;
- P4-1 through P4-6 in this document.

These decisions authorize final planning only, not implementation.
