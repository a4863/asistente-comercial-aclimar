# Phase 4B Implementation Task — Canonical Analysis Input and DTOs

**Status:** Approved for Implement
**Date:** 2026-09-23
**Prerequisites:** Phase 4A1 ACCEPTED; Phase 4A2 ACCEPTED
**Approved plan:** docs/plans/implementation-phase-4-plan.md

## Objective

Implement only the pure Phase 4 analysis-domain layer for:
- canonical message selection;
- 30,000-character body budget;
- deterministic canonical serialization and input digest;
- provider-neutral immutable DTOs;
- bounded inference enums;
- source-local evidence candidate validation helpers;
- conservative quoted-history classification.

No persistence writes.
No repository changes.
No AI provider.
No orchestration service.
No CRM calls.

## Exact Scope Lock

Modify only:

1. app/domain/email_analysis.py
2. test/test_email_analysis.py

No other tracked path may change.

## Required public contracts

Implement immutable/frozen DTOs or equivalent immutable value objects for at least:

### SelectedMessage
- source_record_id: int
- role: target|prior
- body_excerpt: str
- original_body_digest: lowercase SHA-256
- sender: optional str
- recipients: immutable ordered collection
- subject: optional str
- message_date: optional datetime

### AnalysisInput
- account_scope
- target_source_record_id
- contract_version
- policy_version
- selected messages
- input_digest

No ORM objects. No credentials/logs/attachments/audit/provider fields.

### EvidenceCandidate
- source_record_id
- start_offset
- end_offset
- span_digest
- exact_text

Coordinates refer to original stored normalized_body, not excerpt coordinates.

### Candidate DTOs
Implement provider-neutral candidate DTOs consistent with the approved plan:
- FactCandidate
- InferenceCandidate
- ProposalCandidate
- QuestionCandidate
- CommitmentCandidate
- TaskCandidate
- NextStepCandidate
- ContextMention
- AnalysisCandidates

Bounded enums:
- response_needed: yes|no|uncertain
- commercial_risk: none|low|medium|high|unknown
- priority: low|normal|high|urgent
- responsible_party: self|counterparty|unknown
- date_certainty: exact|resolved_relative|uncertain|none
- context mention kind: company|contact|work|opportunity|offer
- quote_state: new|quoted|ambiguous

No candidate may contain approval/execution instructions or adapter handles.

## Input selection function

Implement a read-oriented selector contract equivalent to:

select_analysis_input(session, account_scope, target_source_record_id, *, contract_version=1, policy_version=1, max_prior=6, max_body_chars=30000) -> AnalysisInput

This function may read ORM rows but must perform no writes/commit/rollback.

Selection rules:
1. Target must be an email SourceRecord/EmailMessage, active/retained/non-redacted, have current ConversationMembership, belong to a resolved non-superseded same-account conversation, and have normalized_body.
2. Prior candidates: same current conversation, email sources only, active/retained/non-redacted, not target.
3. Reliable date = sent_at else received_at. If both target and candidate have reliable dates, candidate is prior if earlier, or equal with smaller source_record_id. If either lacks reliable date, candidate is prior only if source_record_id < target source_record_id.
4. Sort dated priors before dateless priors, newest-to-oldest, source_record_id deterministic tie-break.
5. Take at most 6 prior messages.
6. Body budget: max 30,000 Python characters total; target first; if target >30,000 keep first 30,000 and no prior body; then priors newest-to-oldest using remaining budget.
7. Metadata/separators do not consume body budget.
8. No quote/signature stripping.
9. Metadata allowlist only: source_record_id, role, sender, relevant recipients, subject, reliable message date/null, original full-body digest.

Do not include folder/UID location, attachments, credentials/tokens, logs/audit, CRM data, conversation stable key, or unrelated DB fields.

## Canonical serialization and digest

Implement deterministic canonical serialization:
- UTF-8 JSON
- sorted/stable object keys
- compact separators
- explicit nulls
- Unicode as stored
- target first then selected priors
- include account_scope, target_source_record_id, contract_version, policy_version, selected IDs, approved metadata, body excerpts, and full-body SHA-256 digests.

Digest = SHA256(b"phase4/analysis-input/v1\\0" + canonical_json_bytes), lowercase hex.

Same semantic input => same digest.
Change to selected body, selected metadata, selected membership/order, contract_version, or policy_version => changed digest.
Body change outside excerpt must also change digest via original_body_digest.

## Limit-tightening rule
Callers may tighten but not widen:
- max_prior <= 6
- max_body_chars <= 30000
Reject attempts to exceed approved maxima.

## No-analyzable-body behavior
If target normalized_body is missing/None, return/raise a bounded domain result/error suitable for later service mapping to no_analyzable_body. Do not fabricate body.

## Evidence helpers
Implement pure validation/classification helpers operating on original body text and EvidenceCandidate.
Validate source ID, 0-based half-open bounds, slice equality, SHA-256(slice), and that AI-originated evidence lies within the disclosed excerpt range.

## Conservative quote classification
At minimum:
- line beginning with > => quoted
- content below an unambiguous standard mail quote delimiter => quoted
- if quote boundary cannot be established conservatively => ambiguous where applicable
- otherwise new

Do not implement sophisticated signature/quote removal.
Only a new span in the target is eligible for later automatic current Question creation; this phase only exposes classification.

## DTO validation
Enforce:
- summary absent or length 1..4000
- value_reference <=255
- question_text nonempty and consistent with evidence exact_text where applicable
- support indexes valid shape
- commitment rules: exact requires resolved_due_at; resolved_relative requires resolved_due_at + date_expression; uncertain|none require resolved_due_at None
- enums exact
- immutable collections where practical

Invalid output raises bounded domain validation errors; never truncate silently.

## Deterministic tests
Add tests covering at least:
1 target-only selection; 2 six-prior limit; 3 deterministic ordering; 4 timestamp tie-break; 5 missing-date fallback; 6 redacted/deleted excluded; 7 different conversation excluded; 8 unresolved/superseded rejected; 9 target >30k; 10 shared budget; 11 metadata budget exclusion; 12 widening rejected; 13 digest stability; 14 selected body change; 15 body change outside excerpt; 16 metadata change; 17 contract/policy change; 18 forbidden fields absent; 19 valid evidence; 20 invalid bounds; 21 text mismatch; 22 digest mismatch; 23 evidence outside disclosed excerpt; 24 > quote; 25 delimiter quoted region; 26 ambiguous quote case; 27 new target classification; 28 enum validation; 29 commitment date semantics; 30 summary bounds; 31 value_reference bounds; 32 immutability/determinism; 33 selector performs no commit/rollback/write.

Use isolated SQLite fixtures only. No provider/network calls.

## Restrictions
- no app/persistence changes
- no migrations
- no repositories
- no services
- no provider dependency
- no CRM
- no UI/scheduler
- no new dependency
- no cache/untracked inspection

## Validation
Run:
python -m pytest test/test_email_analysis.py
Then:
python -m pytest

Tracked diff must contain exactly:
- app/domain/email_analysis.py
- test/test_email_analysis.py

## Completion
Commit:
Implement phase 4B canonical analysis input

Push only origin/codex-work.

If a persistence/repository/model change is required, STOP.