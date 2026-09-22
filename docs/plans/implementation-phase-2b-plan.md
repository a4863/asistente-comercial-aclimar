# Plan: Implementation Phase 2B Operational Entities

**Status:** READY FOR APPROVAL

## Scope

Implement assistant-owned operational persistence only. CRM context is preferred for follow-up scope; manual classification is fallback. Overdue is evaluated by an explicit clock-injected operation, not a scheduler. No external execution occurs.

## Tables and invariants

| Table | Current state / history | Core constraints |
| --- | --- | --- |
| `task` | current state | `proposed -> pending -> completed/cancelled`; completion requires evidence/confirmation reference |
| `commitment` | current state | `detected -> confirmed -> fulfilled/overdue/cancelled`; fulfilment requires evidence/confirmation |
| `question` | current state | `detected -> open -> answered/dismissed`; answer requires evidence/confirmation |
| `next_step` | current state | `proposed -> planned -> completed/cancelled`; completion requires evidence/confirmation |
| `alert` | current state | `active -> resolved/dismissed`; unique active condition key; recurrence after resolution creates a new row |
| `follow_up_preference` | current state | scope type/reference, threshold days, explicit future date; one current preference per scope |
| `follow_up_preference_history` | append-only | preference change, actor/provenance/timestamp |
| `action_proposal` | current state | one concrete action/target, state `pending_approval -> approved/rejected -> executed/error`, idempotency identity |
| `approval_decision` | append-only | one explicit immutable decision event for one proposal |
| `execution_result` | append-only | attempt, revalidation evidence, outcome, external result reference/failure code |
| `operational_evidence_link` | append-only | links operational objects to source/fact/inference/proposal or user confirmation |

All records use integer PKs and UTC timestamps. 2A foreign keys reference source, fact/inference/proposal, CRM references/context, idempotency identities, and audit events as applicable. No CRM master data is copied.

## Follow-up and alerts

- Defaults: new/qualified opportunity 7 days; sent offer 5; homologation/docs 7; negotiation/review 5.
- Precedence: opportunity/offer/work, then company/contact, then global; CRM context determines scope first, manual classification only when CRM context is unavailable.
- An explicit future date suppresses inactivity alerting until that date.
- `evaluate_overdue(now)` receives a controlled clock value and may transition only confirmed due commitments to overdue; it performs no scheduling or external action.
- Alert condition keys deduplicate active alerts. Resolution/dismissal closes the key; later recurrence creates a distinct alert.

## Repository boundaries

- `OperationalRepository`: explicit create/transition methods, evidence validation, `evaluate_overdue(now)`, preference lookup by precedence, alert create/resolve/dismiss.
- `ActionRepository`: create proposal, append decision, append revalidated execution attempt, and idempotency lookup/reservation. It never invokes an adapter.
- Existing `AuditRepository`: append-only lifecycle/approval/execution audit events.

No generic CRUD, delete, or unrestricted state update methods.

## Migration 0003

Create an explicit Alembic revision with only the listed 2B tables, FKs, state checks, unique active-alert/idempotency constraints, and indexes needed for precedence/due-date queries. Downgrade drops only 0003 objects in reverse dependency order. It must not import application metadata.

## Files / Scope Lock

### Authorized

- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/versions/0003_phase_2b_operational_entities.py`
- `test/test_migrations.py`
- `test/test_persistence_models.py`
- `test/test_persistence_repositories.py`

### Outside scope

Adapters, scheduler, routes/UI, external calls, credentials, dependencies, Phase 2A changes, CRM master copies, and `main`.

## Test plan

- SQLite 0002 → 0003 → 0002 → 0003 migration tests.
- Valid/invalid lifecycle transition tests and evidence/confirmation guards.
- Controlled-clock overdue evaluation tests.
- Follow-up precedence/future-date tests.
- Alert active deduplication and recurrence tests.
- Proposal/decision/execution linkage, immutable history, revalidation, and idempotency tests.
- No network, external system, credential, or user-database tests.

## Implementation order

1. Add models/checks/explicit migration.
2. Add repository guards and clock-injected evaluation.
3. Add isolated migration/model tests.
4. Add repository/lifecycle/idempotency tests.
5. Run full pytest and review the Scope Lock diff.

## STOP conditions

Stop if an adapter, scheduler, external mutation, new dependency, new operational entity, unapproved CRM field, or change outside the listed files is required.

## Definition of Done

- Only Scope Lock files change.
- 0003 is explicit and reversible on isolated SQLite.
- All lifecycle, evidence, preference, alert, approval/revalidation, and idempotency tests pass.
- No external effect or `main` modification occurs.
