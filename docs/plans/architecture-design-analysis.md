# Architecture Design Analysis

**Status:** BLOCKED

## 1. Objective

Analyze the architecture required by the approved functional specification and data model, without selecting technology or creating `docs/architecture.md`.

## 2. Context

The assistant is local-only, single-user, CRM-API-only, approval-driven, and must preserve provenance, idempotency, and auditability while tolerating unavailable integrations. There is no implementation yet.

## 3. Documentation consulted

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/plans/functional-spec-readiness.md`
- `docs/plans/data-model-design-analysis.md`
- `docs/plans/architecture-design-task.md`

`docs/architecture.md`, `docs/security.md`, and `docs/testing-strategy.md` do not yet exist.

## 4. Current state

**NO IMPLEMENTATION YET.** There is no application code, dependency manifest, local database, scheduler, integration implementation, or test suite.

## 5. Required component boundaries

The approved requirements require, at minimum, these technology-neutral responsibilities:

- local user interface for review, approval, dashboard, and configuration states;
- domain workflow for facts, inferences, proposals, lifecycles, and follow-up rules;
- assistant persistence boundary implementing the approved data model;
- IMAP ingestion and thread-reconstruction boundary;
- Calendar read and approved write boundary;
- CRM API read and approved-operation boundary;
- manual-note and WhatsApp-ingestion boundary;
- AI analysis boundary that keeps providers interchangeable and applies data minimization;
- approval, external-state revalidation, and execution boundary;
- local scheduling/synchronization boundary;
- audit/logging and configuration/secret-management boundaries.

External data must enter through integration boundaries as untrusted data. Domain logic must remain separate from external protocols and persistence. External mutations must pass through a concrete approved action proposal and revalidation flow.

## 6. Required flows

- IMAP synchronization must incrementally observe sources, deduplicate them, reconstruct threads only from sufficient technical evidence, persist source/provenance information, and create internal analysis records without moving or sending mail.
- Manual notes and pasted WhatsApp text must preserve the original source before analysis.
- Calendar synchronization must read one configured primary Calendar, reconcile changed/deleted-at-source events, and keep historical references.
- CRM reads must use only its API; proposed writes must map to explicit permitted API business operations after approval.
- Analysis must retain separation of extracted facts, inferences, and proposals and retain supporting evidence.
- Approved external actions must revalidate targets, execute idempotently, and retain outcome/failure evidence.
- A failed or disconnected integration must expose a degraded/reconnect state without preventing local review of already stored information.

## 7. Persisted-state, audit, and testing implications

Architecture must use the approved assistant data model for source records, observations, activities, CRM references, derived records, lifecycles, approval decisions, execution results, and append-only audit events. It must support idempotent processing, source deletion/redaction, and audit preservation.

Future testing boundaries must isolate IMAP, Calendar, CRM, AI, clock/scheduling, persistence, and secret storage. Tests must use fixtures/mocks and must not mutate real external systems or use real credentials unnecessarily.

## 8. Security implications

Credentials must be local, independently manageable per integration, absent from code, Git, plaintext application data, and logs. The architecture must enforce the local-user scope, untrusted-data treatment, integration-specific failure states, and minimal disclosure to any remote AI provider.

The concrete storage mechanism and remote-AI policy enforcement require the security design task and cannot be selected here.

## 9. Material architectural ambiguities

**STOP — user decisions are required before `docs/architecture.md` can be designed.**

1. **Local UI and execution model**
   - Native desktop application.
   - Local web application accessed in a browser.
   - Hybrid desktop shell hosting a local web UI.

   This determines packaging, local startup, process lifetime, user interaction, and how background work remains available.

2. **Persistence and data-access approach**
   - Embedded relational persistence with a data-access layer.
   - Another local persistence approach that can represent the approved relational/audit model.

   This affects integrity enforcement, migrations, backup behavior, and implementation complexity. The functional and data-model documents intentionally do not choose an engine, ORM, or migration mechanism.

3. **Synchronization and background-execution strategy**
   - Synchronization runs only while the application is open.
   - A separately scheduled local process runs synchronization when the UI is closed.

   This affects timeliness of IMAP/Calendar ingestion, startup behavior, credential access, error recovery, and observability.

4. **Credential-storage mechanism**
   - Operating-system secure credential store.
   - A different approved local secure-storage mechanism.

   This affects lifecycle management, packaging, recovery, and the security boundary. The functional specification explicitly defers the technology choice.

5. **AI execution strategy**
   - Local model execution.
   - Remote AI provider subject to the approved disclosure limits.
   - A provider-agnostic boundary supporting a future choice while initially operating without AI automation.

   This has material effects on privacy, offline behavior, cost, analysis quality, operational dependencies, and security controls. A remote provider cannot be selected until `docs/security.md` defines allowed data classes.

## 10. Risks

- Selecting a UI/runtime model or background strategy implicitly would violate the local operating constraints and affect all integrations.
- Selecting persistence or secret storage without approval would prematurely determine security, migration, and recovery behavior.
- Selecting an AI mode without an approved data-disclosure policy risks exposing commercial information.
- Mixing domain rules with integrations would undermine testability, idempotency, and the approval/revalidation boundary.
- Treating integration outages as application failures would violate the required degraded-operation behavior.

## 11. Out-of-scope discoveries

None.

## 12. Scope Lock

### In scope

- Analyze architecture.
- Create only `docs/plans/architecture-design-analysis.md`.

### Out of scope

- `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, code, dependencies, databases, migrations, real integrations, CRM changes, and changes to functional or data-model documents.

### Restrictions

- No implementation or technology selection.
- No change to `main`.
- Commit and push only to `codex-work`.

## 13. Result

**BLOCKED**

Resolve the five material architectural decisions in section 9 before creating `docs/architecture.md`.
