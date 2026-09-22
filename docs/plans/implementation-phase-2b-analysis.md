# Phase 2B Analysis — Operational Entities

**Status:** STOPPED FOR DECISION

## Context

Phase 2A supplies assistant-owned source, derivation, identity, audit, checkpoint, and idempotency persistence. Phase 2B would add operational current-state records without implementing any IMAP, Calendar, CRM, AI, UI, or external execution.

## Entity matrix

| Entity | Minimum persistence role | 2A links |
| --- | --- | --- |
| Task | internal action and current lifecycle | source/fact/inference/proposal/audit |
| Commitment | promise, participant context, due date, lifecycle | evidence and CRM context |
| Question | exact unresolved item and lifecycle | source/fact/evidence |
| NextStep | agreed/proposed action and target date | proposal/evidence |
| Alert | derived signal, priority, current state | supporting record and preference |
| FollowUpPreference + history | scoped threshold/override and immutable change history | CRM references/context |
| ActionProposal | one concrete external mutation and idempotency identity | proposal/source/target reference |
| ApprovalDecision | immutable explicit decision for one proposal | action proposal/audit |
| ExecutionResult | append-only execution attempt and revalidation evidence | action proposal/approval/audit |

## State-transition matrix

| Entity | Valid transitions | Automatic transition | Confirmation/evidence required |
| --- | --- | --- | --- |
| Task | proposed → pending → completed/cancelled | none | completed requires explicit source evidence or user confirmation |
| Commitment | detected → confirmed → fulfilled/overdue/cancelled | confirmed due date passing may create overdue | fulfilled requires evidence or confirmation |
| Question | detected → open → answered/dismissed | none | answered requires evidence or confirmation |
| NextStep | proposed → planned → completed/cancelled | none | completed requires evidence or confirmation |
| ActionProposal | pending_approval → approved/rejected → executed/error | none | approval explicit; execution requires revalidation |

## Repository proposal

- `OperationalRepository`: explicit creation and valid-only lifecycle transitions for Task, Commitment, Question, NextStep, Alert, and follow-up preference/history.
- `ActionRepository`: create one concrete ActionProposal, append immutable ApprovalDecision, append ExecutionResult attempt after recorded revalidation, and reserve idempotency identities.
- `AuditRepository`: append lifecycle, approval, revalidation, execution, correction, and failure events; no update/delete API.

No repository performs external execution in 2B.

## Migration 0003 proposal

Create only operational tables, their evidence/relationship tables, constrained state columns, unique action idempotency identity, immutable approval/execution history, and preference-history tables. Current-state records may be mutable only through explicit repository transitions; history/approval/execution/audit rows are append-only.

## Test matrix

- valid and invalid transitions for every lifecycle;
- completion/fulfilment/answer rejection without evidence or confirmation;
- overdue temporal transition using a controlled clock;
- one ActionProposal per concrete target/idempotency identity;
- immutable single decision records and multiple execution attempts;
- revalidation evidence before execution-result creation;
- follow-up precedence and explicit future-date precedence;
- alert derivation does not alter fact/inference/task state;
- isolated SQLite migration 0002 → 0003 and downgrade/re-upgrade;
- no external client, credential, user database, or network access.

## Required decision

The documentation does not define enough information to choose safely between the following reasonable interpretations:

1. **Follow-up scope mapping:** whether the defaults apply based on a CRM opportunity/offer/work status, a manually assigned assistant classification, or a combination; the source of the applicable status is not defined for a persistence-only phase.
2. **Automatic overdue timing:** whether overdue is materialized only when a scheduled evaluator runs, calculated on read, or created during any relevant transaction; architecture defers scheduler implementation.
3. **Alert lifecycle:** no permitted alert states, deduplication rule, or resolution rule is specified.

These choices affect table constraints, current-state/history design, repository methods, idempotency, and tests. Under the Ambiguity Rule, implementation planning must not select one.

## Scope Lock pending decision

After those decisions, an implementation may be limited to `app/persistence/models.py`, `app/persistence/repositories.py`, `alembic/versions/0003_phase_2b_operational_entities.py`, and dedicated 2B migration/model/repository tests. No adapter, route, service, dependency, credential, or `main` change is in scope.

## Risks

- silently treating inferences as completion evidence;
- automatic external execution before approval/revalidation;
- duplicated alerts/actions without scoped idempotency;
- overriding explicit future dates with inactivity rules;
- loss of approval/execution history through mutable records.
