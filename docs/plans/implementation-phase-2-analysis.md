# Analysis: Implementation Phase 2 Persistent Assistant-Owned Core

## 1. Objective

Plan the first persistent assistant-owned domain increment defined by `docs/data-model.md`, without external adapters, credentials, business UI, or external mutations.

## 2. Context

Phase 1 provides a local FastAPI/SQLite/SQLAlchemy/Alembic foundation. Its initial migration is intentionally empty. The approved model requires a source-preserving, auditable assistant store while keeping CRM entities external and authoritative.

## 3. Interpretation

Phase 2 should establish the persistent domain, not ingest or execute against any external system. The listed model is too broad for one safe implementation unit: it combines source/provenance identity, internal workflow lifecycles, and external-action approval/execution. These have distinct invariants and test matrices.

The phase should therefore be split into **2A** and **2B**. This analysis defines a precise 2A implementation scope and a bounded follow-up 2B scope. No external integration is implied by either increment.

## 4. Documentation consulted

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/plans/implementation-phase-1-plan.md`
- `docs/plans/implementation-phase-1-final-review.md`
- `docs/plans/implementation-phase-2-task.md`

All required documents exist.

## 5. Current state

Phase 1 supplies SQLAlchemy's declarative `Base`, a SQLite session factory, an empty initial Alembic baseline, a placeholder repository boundary, and isolated migration/session tests. There are no persistent assistant-owned domain tables, repositories, synchronization adapters, external calls, commercial entities, or production credentials.

## 6. Entity split

### Phase 2A — source, provenance, and derived-information foundation

Implement the following assistant-owned records and their internal relationships:

- `ConfigurationReference`
- `SourceRecord`
- `SourceObservation`
- `Conversation` and `ConversationMembership`
- `ManualNote`
- `WhatsAppImport`
- `CalendarEventRepresentation`
- `Activity` and `ActivitySourceLink`
- `CRMReference`
- `CRMContextLink`
- `IdentityLink`
- `IdentityLinkCorrection`
- `ExtractedFact`
- `Inference`
- `Proposal`
- `AuditEvent`
- `SynchronizationCheckpoint`
- `IdempotencyIdentity`

2A establishes the durable source → derivation → audit backbone, source deletion/redaction state, correction/supersession history, and synchronization/idempotency evidence. It creates no `EmailMessage` representation because IMAP ingestion and MIME/header mapping are explicitly deferred; it does not prevent a future email representation from linking to `SourceRecord`.

### Phase 2B — internal workflow and external-action records

Implement only after 2A is reviewed and accepted:

- `Task`
- `Commitment`
- `Question`
- `NextStep`
- `Alert`
- `FollowUpPreference` and preference-change history
- `ActionProposal`
- `ApprovalDecision`
- `ExecutionResult`

2B owns the approved state machines, approval-decision uniqueness, execution-attempt linkage, target-revalidation evidence, and workflow-specific idempotency. It still creates no adapter, external mutation, or UI.

## 7. Phase 2A model and integrity plan

### Source and synchronization

- `SourceRecord` has a local identity; `source_type`, `source_system_scope`, optional stable external identifier, retained content/reference, source/ingestion timestamps, retention state, and deletion/redaction metadata.
- A unique constraint applies to `(source_system_scope, stable_external_identifier)` only when the external identifier is present. Manual sources use the local identity and manual-entry provenance.
- `SourceObservation` links to one source record and retains observed timestamp, optional source version marker, active/deleted state, outcome, and reconciliation provenance. Repeated observations are retained rather than overwriting prior evidence.
- `SynchronizationCheckpoint` is unique per source-system scope and records a non-secret checkpoint marker, last successful synchronization timestamp, and outcome metadata. It must not contain credentials.
- `IdempotencyIdentity` stores an operation kind, scope, key, target/source reference, creation timestamp, and optional resolution metadata. `(operation_kind, scope, key)` is unique.
- Calendar deleted-at-source is represented by a historical source record/observation plus inactive deletion state; retained provenance is not erased.

### Source-specific and activity records

- `ManualNote` and `WhatsAppImport` each have a one-to-one link to `SourceRecord`, immutable original entered/pasted text, manual-ingestion provenance, and input timestamp. WhatsApp is text-only.
- `CalendarEventRepresentation` links to one source record and retains the stable Calendar event reference, relevant time metadata, and current active/deleted-at-source representation. It does not call Calendar.
- `Conversation` represents a candidate email thread; `ConversationMembership` links a source record to at most one conversation and retains technical-evidence type/reference. A uniqueness constraint on its source-record link prevents multi-conversation assignment. No membership is created where evidence is insufficient.
- `Activity` retains only assistant-owned interaction type, occurrence time, descriptive state, provenance, and timestamps. `ActivitySourceLink` supports one or more source records per activity without copying source material.

### CRM and identity boundaries

- `CRMReference` contains only CRM entity type, external CRM identifier, permitted minimal traceability metadata, and timestamps. `(entity_type, external_identifier)` is unique; it has no company/contact/project/opportunity/offer master-data fields.
- `CRMContextLink` relates an assistant record to a CRM reference with relationship purpose, provenance, confirmation/ambiguity status, and timestamps. An ambiguous link must remain non-confirmed.
- `IdentityLink` holds a source-level identity value/type and target CRM reference, confirmation provenance/timestamp, current status, and optional supersession reference.
- `IdentityLinkCorrection` is an immutable record linking old and replacement identity links with correction provenance/timestamp. Corrections supersede; they do not delete or rewrite the prior link. Confirmed links do not expire automatically.

### Derived records and audit

- `ExtractedFact`, `Inference`, and `Proposal` are separate tables with separate type discriminators, payload/reference fields, provenance, timestamps, and current/correction status where applicable.
- Facts link to one or more supporting source records through explicit evidence-link association records. Inferences and proposals link to their supporting source/fact/proposal records through typed support links. No row can change type from fact to inference or proposal.
- `AuditEvent` is append-only: it has no repository update/delete operation. It records event type, affected-record type/identity, actor/source, timestamp, provenance, and minimum safe outcome/failure metadata. It must not store credentials or unnecessary source bodies.
- Repository methods expose explicit creation/transition operations and never generic unrestricted mass-update/delete methods for audit, correction, or source-history rows.

## 8. Repository boundaries

2A repositories should be narrow and transaction-neutral, using the Phase 1 session factory:

- source/configuration repository: source creation, observation append, retention-state transition, checkpoint and idempotency lookup/create;
- provenance repository: conversations/memberships, activities/source links, CRM references/context links, identity confirmation/correction;
- derivation repository: append facts, inferences, proposals, and support/evidence links;
- audit repository: append and query audit events only.

Repositories may receive a session supplied by application services/tests. They must not open external connections, store secrets, access `crm.db`, or encode business actions outside their declared invariant.

## 9. Migration scope

2A requires one new Alembic revision after `0001`, creating only the 2A tables, association tables, enum/check constraints, uniqueness constraints, and required foreign keys. The migration must be reversible for an empty assistant database and must be tested only with isolated SQLite databases. It must not inspect, migrate, or create a user database outside the test fixture.

## 10. Phase 2B model outline

2B is intentionally deferred because it needs independent lifecycle and approval invariants:

- state-specific tables or constrained current-state fields plus immutable transition/audit evidence;
- valid-only transitions for task, commitment, question, and next-step lifecycles;
- follow-up override precedence and explicit future-date precedence;
- exactly one immutable `ApprovalDecision` per decision event for one `ActionProposal`, never reusable across proposals;
- one-or-more `ExecutionResult` attempt rows per approved proposal, retaining revalidation and retry/idempotency evidence.

No 2B operation performs an external mutation; adapters and execution services remain later work.

## 11. Exact files for a 2A implementation task

### Modify

- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/env.py` only if necessary to expose approved metadata to Alembic
- `test/test_migrations.py`
- `test/conftest.py`

### Create

- `alembic/versions/0002_phase_2a_persistent_foundation.py`
- `test/test_persistence_models.py`
- `test/test_persistence_repositories.py`

### Not affected

- FastAPI routes/templates and startup;
- configuration and credential code;
- adapter/integration packages;
- approved documentation;
- Phase 2B records.

The exact revision filename may vary only to match Alembic revision conventions; no other file should be added without a new analysis.

## 12. Dependencies

Use the already approved and installed SQLAlchemy 2.x, Alembic, SQLite, and pytest foundation. No new package is required. There are no IMAP/SMTP, Google, CRM API, AI, keyring, APScheduler, or network dependencies in 2A or 2B.

## 13. Risks

- **High — provenance loss:** collapsing facts, inferences, or proposals would violate the model. Mitigate with distinct tables and explicit support/evidence links.
- **High — CRM authority leakage:** copied CRM master fields or direct database access would create a competing source of truth. Mitigate with typed external references only and tests that reject master-data columns.
- **High — history mutation:** generic updates/deletes could erase corrections, source observations, or audit evidence. Mitigate with append-only repository operations and correction records.
- **High — duplicate processing:** missing scope-aware unique identities can create duplicate sources or retries. Mitigate with database constraints and idempotency lookup/create tests.
- **Medium — phase overreach:** adding every lifecycle/action invariant together with provenance makes review and migration risk unbounded. Mitigate by splitting 2A/2B.
- **Medium — sensitive data:** source material and audit details could carry commercial content. Mitigate with minimum payload fields, redaction state, no credentials, and synthetic test data only.
- **Medium — untrusted data:** stored source content is data only; no content may become executable instruction or configuration.

## 14. Required tests for 2A

- isolated SQLite migration from Phase 1 baseline and downgrade/upgrade smoke coverage;
- repository/session isolation with no user database path;
- source uniqueness within scope, while manual sources retain local identities;
- append-only source observations and explicit active/deleted-at-source state;
- checkpoint persistence and scope-aware idempotency uniqueness;
- one-to-one manual-note/WhatsApp source links and immutable original text behavior;
- conversation membership rejects assigning a source to multiple conversations and accepts no membership for ambiguity;
- CRM references retain only type/external identifier/minimal metadata, without copied master records;
- ambiguous CRM context links remain non-confirmed;
- identity correction supersedes without deleting the prior confirmed link;
- separate fact/inference/proposal tables and supporting-evidence links;
- audit repository only appends, retains minimum metadata after redaction, and rejects secret-bearing fields;
- no network, keyring, mailbox, Calendar, CRM, AI, or external mutation in any test.

2B later requires the lifecycle, approval, execution-linkage, follow-up-precedence, revalidation, and retry/idempotency tests listed in `docs/testing-strategy.md`.

## 15. Scope Lock for the next task — Phase 2A

### IN SCOPE

- The 2A records, constraints, repositories, isolated Alembic revision, and tests enumerated in sections 6–14.
- SQLite/SQLAlchemy persistence for assistant-owned data only.
- Synthetic fixtures and isolated test databases.

### OUT OF SCOPE

- Every Phase 2B workflow/action record.
- IMAP/SMTP, Google Calendar API, CRM API, AI, keyring, APScheduler, Task Scheduler, UI, and external mutations.
- Email MIME/header ingestion representation.
- CRM master-data copies or direct `crm.db` access.
- Credentials, remote data, attachments, production databases, and changes to `main`.

### RESTRICTIONS

- No new dependency or framework.
- No generic delete/update mechanism for audit, source-observation, or identity-correction history.
- No automatic identity resolution from textual similarity.
- No external system call, credential retrieval, or test against real data.
- STOP if implementation needs an unlisted assistant entity, a physical-design choice not constrained here, or a change outside the listed files.

## 16. STOP conditions and decisions pending

STOP before implementation if any of these emerge:

- an entity needs a business field or lifecycle not specified by `docs/data-model.md`;
- a derived record requires a new semantic type beyond fact/inference/proposal;
- a CRM reference requires copying authoritative master data;
- source deletion/redaction needs a retention policy beyond the approved explicit state/history rules;
- implementation needs an external adapter, credential, real database, or new package;
- a required relationship cannot be represented with the 2A entities and constraints described here.

No unresolved functional, architecture, security, or data-model decision blocks the proposed 2A scope.

## 17. Out-of-scope discoveries

- Phase 1's final review report predates the subsequently committed controlled localhost launcher; it is historical review evidence and is not part of Phase 2 persistence scope.
- The repository has no current domain/application-service layer. Introducing one is not required for the 2A persistence-only increment and must not be inferred into scope.

## 18. Result

**READY FOR APPROVAL**

Proceed only with a separate approved Phase 2A plan and Scope Lock. Phase 2 should be split into 2A/2B; it is not safe or reviewable as one implementation task.
