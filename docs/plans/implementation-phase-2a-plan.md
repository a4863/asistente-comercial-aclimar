# Plan: Implementation Phase 2A Persistent Foundation

**Estado:** Ready for approval

**Fecha:** 2026-09-21

**Baseline:** `a672035eb0996a6fa25124a320fb4e1184bbc6ce` on `codex-work`

## 1. Objective

Add the assistant-owned persistent backbone for source provenance, derived information, CRM references, identity history, audit, checkpoints, and idempotency. This is persistence-only work: it introduces no external adapter, credential access, business UI, or action execution.

## 2. Context

Phase 1 has an empty Alembic baseline and only SQLAlchemy `Base` plus a session factory. The approved Phase 2 analysis split the proposed domain into 2A and 2B so provenance/synchronization records can be validated before lifecycle, approval, and execution records are introduced.

## 3. Scope

### Includes

- The exact Phase 2A entities in section 8.
- One isolated SQLite/Alembic migration after revision `0001`.
- Narrow repositories for persistence invariants.
- Synthetic, isolated persistence and migration tests.

### Does not include

- Phase 2B: task, commitment, question, next step, alert, follow-up preference, action proposal, approval decision, and execution result.
- Email/MIME ingestion, IMAP/SMTP, Calendar API, CRM API, AI, keyring, APScheduler, Task Scheduler, UI, routes, application services, or external mutations.
- CRM master-data copies, credentials, attachments, production data, or user-database access.

## 4. Documentation relevant to the implementation

- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/plans/implementation-phase-2-analysis.md`

## 5. Current state

- `app/persistence/models.py` defines only SQLAlchemy `Base`.
- `app/persistence/repositories.py` is a placeholder.
- Alembic revision `0001` is empty.
- Tests already provide project-controlled temporary SQLite paths and a migration smoke test.

## 6. Physical conventions

- Every table uses an integer surrogate primary key named `id`; logical/external identities remain explicit business columns and are never inferred from the physical key.
- Timestamps are timezone-aware UTC `DateTime` fields and are non-null unless the table explicitly describes an optional source timestamp.
- Controlled values use SQLAlchemy enums persisted as constrained strings; free source/provenance text remains data and is never executed.
- Source/original content is only held by the source-specific tables allowed below. Audit payloads are limited to event/outcome metadata and never credentials or full source bodies.
- Repository methods accept a caller-owned SQLAlchemy session. They do not create engines, open external clients, or perform network access.

## 7. Files planned

### Create

- `alembic/versions/0002_phase_2a_persistent_foundation.py`
- `test/test_persistence_models.py`
- `test/test_persistence_repositories.py`

### Modify

- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/env.py` only to set `target_metadata = Base.metadata` when the current environment requires it for the approved metadata path
- `test/conftest.py`
- `test/test_migrations.py`

### Do not create, modify, or delete

Every other file, including all application, route, startup, configuration, security, documentation, adapter, and Phase 2B files.

## 8. Exact SQLAlchemy model and table set

### Configuration, sources, and synchronization

| Model / table | Required fields and constraints |
| --- | --- |
| `ConfigurationReference` / `configuration_reference` | `scope` (unique, non-null), `reference_kind` (non-null), `reference_value` (non-secret, non-null), `created_at`. Stores mailbox/Calendar/source scopes only; never credentials. |
| `SourceRecord` / `source_record` | `source_type`, `source_system_scope`, nullable `stable_external_id`, nullable `source_timestamp`, `ingested_at`, `retention_state`, nullable `deleted_or_redacted_at`, nullable `redaction_reason`, `manual_entry` flag, and provenance fields. Unique `(source_system_scope, stable_external_id)` only when `stable_external_id` is non-null. |
| `SourceObservation` / `source_observation` | FK `source_record_id`, `observed_at`, nullable `source_version_marker`, `observed_state`, `outcome`, provenance. It is insert-only. A unique `(source_record_id, source_version_marker)` applies when a version marker exists. |
| `SynchronizationCheckpoint` / `synchronization_checkpoint` | `source_system_scope` (unique), nullable non-secret `checkpoint_marker`, nullable `last_success_at`, `last_outcome`, `updated_at`. |
| `IdempotencyIdentity` / `idempotency_identity` | `operation_kind`, `scope`, `identity_key`, nullable `source_record_id`, nullable `target_reference`, `created_at`, nullable `resolved_at`. Unique `(operation_kind, scope, identity_key)`. |

`retention_state` explicitly distinguishes active, deleted-at-source, redacted, and explicitly-deleted retention states. Deletion/redaction changes current state but does not delete the source row, observations, or required audit metadata.

### Source-specific and activity records

| Model / table | Required fields and constraints |
| --- | --- |
| `Conversation` / `conversation` | `created_at`, provenance, nullable `superseded_at`. It has no subject/participant rule that can itself establish membership. |
| `ConversationMembership` / `conversation_membership` | FK `conversation_id`, FK `source_record_id` (unique), `evidence_type`, `evidence_reference`, `created_at`. The unique source FK prevents a source belonging to more than one conversation. |
| `ManualNote` / `manual_note` | FK `source_record_id` (unique), `original_text` (non-null), `entered_at`, manual provenance. Original text is never updated by repository methods. |
| `WhatsAppImport` / `whatsapp_import` | FK `source_record_id` (unique), `original_text` (non-null), `pasted_at`, manual provenance. Text only; no attachment fields. |
| `CalendarEventRepresentation` / `calendar_event_representation` | FK `source_record_id` (unique), `calendar_event_id` (non-null), nullable start/end timestamps and minimal relevant metadata, `current_state`, `updated_at`. It represents data only and invokes no Calendar client. |
| `Activity` / `activity` | `activity_type`, nullable `occurred_at`, nullable description/reference, `created_at`, provenance. |
| `ActivitySourceLink` / `activity_source_link` | FK `activity_id`, FK `source_record_id`, `link_purpose`, `created_at`; unique `(activity_id, source_record_id, link_purpose)`. |

### CRM references and identity history

| Model / table | Required fields and constraints |
| --- | --- |
| `CRMReference` / `crm_reference` | `entity_type`, `external_id`, nullable `display_reference`, `created_at`, provenance; unique `(entity_type, external_id)`. Prohibited fields: copied company/contact/project/opportunity/offer business attributes. |
| `CRMContextLink` / `crm_context_link` | FK `crm_reference_id`, `assistant_record_type`, `assistant_record_id`, `relationship_purpose`, `confirmation_state`, `created_at`, nullable `confirmed_at`, provenance. `confirmation_state` is `ambiguous`, `proposed`, or `confirmed`; only confirmed rows may have `confirmed_at`. The polymorphic assistant reference is restricted in repository validation to 2A record types. |
| `IdentityLink` / `identity_link` | `identity_type`, `identity_value`, FK `crm_reference_id`, `status`, `confirmed_at`, provenance, nullable `superseded_at`; one active confirmed mapping per `(identity_type, identity_value)` is enforced through repository validation plus a partial unique index where SQLite supports it. |
| `IdentityLinkCorrection` / `identity_link_correction` | FK `prior_identity_link_id`, FK `replacement_identity_link_id`, `corrected_at`, provenance; each prior link is corrected at most once. It is insert-only and prior links are marked superseded, never deleted. |

### Derived information, evidence, and audit

| Model / table | Required fields and constraints |
| --- | --- |
| `ExtractedFact` / `extracted_fact` | `fact_type`, `value_reference`, `created_at`, extraction provenance, nullable `superseded_at`. |
| `Inference` / `inference` | `inference_type`, `value_reference`, `created_at`, inference provenance, nullable `confirmed_at`. It cannot be converted into a fact. |
| `Proposal` / `proposal` | `proposal_type`, `value_reference`, `created_at`, proposal provenance, `status`. It is not an approval or execution record. |
| `FactSourceEvidence` / `fact_source_evidence` | FK `extracted_fact_id`, FK `source_record_id`, `evidence_reference`, `created_at`; unique `(extracted_fact_id, source_record_id, evidence_reference)`. |
| `InferenceSupport` / `inference_support` | FK `inference_id`, `support_type`, `support_id`, `created_at`; unique `(inference_id, support_type, support_id)`. Repository validation permits only source/fact/inference support kinds defined by the model. |
| `ProposalSupport` / `proposal_support` | FK `proposal_id`, `support_type`, `support_id`, `created_at`; unique `(proposal_id, support_type, support_id)`. Repository validation permits only source/fact/inference/proposal support kinds defined by the model. |
| `AuditEvent` / `audit_event` | `event_type`, `affected_record_type`, `affected_record_id`, `actor_or_source`, `occurred_at`, `provenance`, nullable minimum `outcome_reference`, nullable safe `failure_code`. It has no full source body, credential, token, password, or unrestricted payload field. |

The distinct `ExtractedFact`, `Inference`, and `Proposal` tables are mandatory. Generic support links are deliberately typed references because a derivation can cite several distinct record families; repository validation constrains their allowed kinds.

## 9. Migration plan

1. Update `Base.metadata` models and expose metadata to Alembic only if `env.py` currently lacks the approved target metadata.
2. Add revision `0002` with all section-8 tables, named foreign keys, check constraints for controlled states, uniqueness constraints, and the SQLite-compatible partial unique index for stable external source identity.
3. Create association/evidence tables in dependency order after their parent tables.
4. `downgrade()` removes only 2A association tables followed by 2A entity tables in reverse dependency order; it never targets user data outside the isolated test database.
5. Update migration tests to verify `0001 -> 0002`, a downgrade to `0001`, and a re-upgrade to head in a project-controlled SQLite temporary path.

## 10. Repository plan

- `SourceRepository`: create/get source by scoped stable identity; append observation; transition retention state; create/get checkpoint; reserve/query idempotency identity. It has no source-history delete method.
- `ProvenanceRepository`: create conversations and evidence-backed memberships; add manual source-specific records; create activities/source links; create CRM references/context links; create identity links and append corrections. It rejects duplicate conversation membership and confirmed ambiguous context.
- `DerivationRepository`: append facts, inferences, proposals, evidence, and typed support links. It rejects unsupported support kinds and cross-type conversion.
- `AuditRepository`: append/list only. It exposes no generic update or delete method and validates that safe audit fields are present.

No repository performs external I/O, dynamic model lookup from untrusted input, automatic identity matching, or a generic CRUD method that can bypass the listed invariants.

## 11. Tests and commands

### Test fixtures

- Extend `isolated_tmp_path` use only as needed for an isolated SQLite URL.
- Add a session-factory fixture that creates metadata/migrations only in the project-controlled temporary directory and disposes the engine at teardown.
- Use synthetic source text/IDs only; no production credentials, external clients, or user database paths.

### `test/test_persistence_models.py`

- Source scoped external-ID uniqueness, while two manual sources without external IDs are accepted.
- Source observation append behavior and changed/deleted-at-source retention history.
- One-to-one ManualNote/WhatsApp source relation and immutable original text through repository API.
- Conversation membership uniqueness and absence of membership for ambiguous source evidence.
- CRMReference has only the minimal reference fields; ambiguous CRMContextLink cannot be marked confirmed without explicit confirmation data.
- Identity correction creates a new correction record and supersedes, rather than deletes, the prior link.
- Fact, inference, and proposal are separate concrete model/table types; evidence/support rows are required and valid typed links succeed.
- Checkpoint scope uniqueness and idempotency `(operation_kind, scope, identity_key)` duplicate rejection.

### `test/test_persistence_repositories.py`

- Repositories use independent isolated sessions and do not open network clients.
- Source/provenance methods enforce all duplicate and state guards.
- Audit appends survive source redaction-state transition and no update/delete repository method is exposed or used.
- Negative tests reject copied CRM master-data arguments, unsupported polymorphic/support types, missing fact evidence, invalid confirmed-ambiguous links, and unsafe audit payload fields.

### `test/test_migrations.py`

- Upgrade from `0001` to `0002` on an isolated SQLite database.
- Assert expected 2A tables/constraints exist.
- Downgrade to `0001` and re-upgrade to head without accessing a user database.

### Commands for the later Implement Task

```text
python -m pytest
```

No standalone Alembic command may point at `assistant.db`; migration verification runs exclusively through the isolated test fixture.

## 12. Risks and mitigations

- **Provenance or audit loss:** prevent by append-only repository APIs and history rows; test redaction without audit deletion.
- **CRM authority leakage:** prevent by model fields and negative tests that disallow master-data copies/direct CRM access.
- **Incorrect thread/identity assignment:** prevent by unique membership, explicit evidence, and unconfirmed ambiguity states; no textual matching automation.
- **Duplicate processing:** prevent by database uniqueness plus repository get/reserve behavior.
- **Sensitive data exposure:** do not add credential fields or unrestricted audit payloads; use synthetic tests and retain minimum audit metadata.
- **Scope expansion:** do not add 2B lifecycle/action tables, adapters, routes, or packages.

## 13. Rollback

Before the later implementation, rollback is Git-only because no user migration is run. During isolated tests, revision `0002` may be downgraded to `0001` and re-upgraded. Never delete or recreate a user assistant database as a shortcut.

## 14. STOP conditions

Stop and request a new analysis/decision if implementation requires:

- a Phase 2B entity or lifecycle;
- a CRM master-data field, direct `crm.db` access, or external API client;
- a credential, external system, production database, or new dependency;
- an unlisted table/file;
- a new source retention policy, derived-information kind, or support relationship not defined above;
- a generic mutable audit/history interface.

## 15. Definition of Done

- [ ] Only the eight authorized files are changed/created.
- [ ] Revision `0002` upgrades/downgrades only isolated SQLite databases.
- [ ] All section-8 entities and association/evidence tables exist with the listed constraints.
- [ ] CRM references remain references, not master copies.
- [ ] Facts, inferences, and proposals are physically separate.
- [ ] Source observations, identity corrections, and audit events preserve history.
- [ ] All required positive and negative tests pass with `python -m pytest`.
- [ ] No external call, credential use, or `main` branch change occurs.

# SCOPE LOCK

### Authorized files

- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/env.py` only if metadata exposure is necessary
- `alembic/versions/0002_phase_2a_persistent_foundation.py`
- `test/conftest.py`
- `test/test_migrations.py`
- `test/test_persistence_models.py`
- `test/test_persistence_repositories.py`

### Authorized components

Only the Phase 2A persistent entities, constraints, repositories, Alembic revision, and isolated tests described in this plan.

### Authorized functionality

Assistant-owned local persistence and invariant enforcement only. No ingestion, synchronization execution, UI, API, external mutation, or credential access.

### Outside scope

All Phase 2B entities, every integration, new dependency, business workflow, route/template, configuration/security document change, and `main` branch change.

## 16. Status

**READY FOR APPROVAL**

This plan requires explicit implementation approval before `Implement Task` is used.
