# Architecture Design Analysis

**Status:** READY FOR APPROVAL

## 1. Objective

Prepare a future `docs/architecture.md` from the approved functional specification, data model, and architecture decisions. This analysis does not create that document or implementation.

## 2. Context

The MVP is a local, single-user commercial assistant on Alejandro's Windows PC. It is a local web application accessed through localhost, not a hosted service or SaaS. The CRM remains API-only and authoritative for master commercial entities.

## 3. Documentation consulted

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/plans/functional-spec-readiness.md`
- `docs/plans/data-model-design-analysis.md`
- `docs/plans/architecture-design-task.md`
- `docs/plans/architecture-decisions.md`

`docs/architecture.md`, `docs/security.md`, and `docs/testing-strategy.md` do not yet exist.

## 4. Current state

**NO IMPLEMENTATION YET.** No code, dependencies, database, migrations, integrations, scheduler, or tests exist.

## 5. Proposed components

- Local web UI, served and accessed only on localhost, for dashboard, review, approval, and integration status.
- Application/domain workflow for facts, inferences, proposals, lifecycles, follow-up rules, and approval requirements.
- Embedded relational persistence behind a dedicated data-access boundary, implementing the approved data model.
- IMAP adapter for incremental mailbox reads, folder discovery, and technical-evidence-based thread reconstruction.
- Google Calendar adapter for one primary Calendar, reads, reconciliation, and approved writes.
- CRM API adapter for the explicit read and approved-operation contract only.
- Manual note and WhatsApp-text ingestion boundary.
- Provider-agnostic AI service boundary, separate from domain rules.
- Action-execution boundary for approval, revalidation, idempotency, and audit outcomes.
- In-process periodic synchronization coordinator with persisted checkpoints.
- Local configuration, operating-system secure credential-store, audit, and minimal observability boundaries.

## 6. Boundaries and responsibilities

External adapters translate untrusted source data into source records and observations. Domain workflows operate on assistant-owned records and must not call external protocols directly. Persistence owns current state, history, idempotency identities, and audit records. The execution boundary is the only route for external mutations and requires a concrete approved action proposal plus target revalidation.

The AI boundary receives only the minimal permitted analysis context and returns analysis output that remains fact, inference, or proposal according to domain rules. It must not contain provider-specific business logic.

## 7. Main flows

1. While the application is running, periodic synchronization reads IMAP, Calendar, and permitted CRM context using persisted checkpoints.
2. Source adapters record source identity/observations, deduplicate, reconcile changed external state, and preserve provenance.
3. Email threading uses Message-ID, In-Reply-To, and References first; ambiguous messages remain separate.
4. The domain analysis flow creates internal records and proposals, preserving the distinction between facts, inferences, and proposals.
5. The UI presents proposed external actions. Approval records one concrete decision.
6. Execution revalidates the target, performs the approved operation idempotently, and records the result or failure.
7. After downtime, including weekends, startup uses the last persisted checkpoint to incrementally catch up without a full historical synchronization.

## 8. IMAP integration

The IMAP adapter supports one mailbox initially, incremental reads, the configured initial history window, existing-folder discovery, source identities, and synchronization checkpoints. It may not send email, create folders, or move a message except through the approved action-execution flow. Draft creation also requires approval and duplicate prevention.

## 9. Calendar and CRM API

The Calendar adapter reads one configured primary Calendar, retains historical references for changed/deleted-at-source events, and allows only approved create/modify actions. Calendar deletion is outside the MVP.

The CRM adapter uses only the explicit CRM API contract. It reads permitted context and maps approved writes only to explicit business operations. It never accesses `crm.db`, scrapes HTML, or performs arbitrary field updates.

## 10. Persistence and scheduling

Persistence is embedded relational storage with a dedicated data-access layer. This suits the approved relational model, integrity constraints, lifecycle state, provenance, audit history, and idempotency requirements. Database engine, ORM/data-access technology, and migrations remain to be proposed in `docs/architecture.md`, not selected by this analysis.

Synchronization runs inside the main application process while it is active. The application and CRM are expected to run continuously on weekdays; a separate Windows service is outside the MVP. Integration-specific failures must not terminate the local application, and checkpoints must be persisted.

## 11. Approval, audit, and error isolation

Approval decisions, revalidation evidence, execution attempts, outcomes, failures, and corrections must use the approved data model and append-only audit history. Local review of existing data remains available when IMAP, Calendar, CRM, or AI is unavailable. Each affected integration exposes a clear degraded or reconnect state.

## 12. Security, testing, and observability implications

Credentials use the operating-system secure credential store and remain independently manageable, local, absent from code/Git/plaintext application data/logs. The exact Windows secure-storage technology and the remote-AI data-class policy remain work for architecture and security documentation.

Future tests must isolate adapters, clock/scheduler, persistence, AI, and secret storage with mocks/fixtures. They must cover idempotency, revalidation, lifecycle rules, audit history, degraded integrations, and no external mutation without approval.

Minimal local observability must expose synchronization/checkpoint status, integration degradation, action outcomes, and failures without logging credentials or unnecessarily retaining sensitive source content.

## 13. Alternatives and ambiguities

**None that block the architecture-document design phase.**

The material choices from the prior analysis are approved in `architecture-decisions.md`. Remaining choices—database engine, ORM/data-access technology, migration mechanism, IMAP/Calendar/HTTP libraries, precise Windows secure-store API, AI provider/model, and local packaging—are intentionally deferred for explicit treatment in the architecture or security documents. They must not be silently selected during implementation.

## 14. Risks

- A local web application must remain localhost-only and must not become a hosted backend.
- In-process synchronization depends on the application remaining active; checkpoint recovery is therefore essential.
- Remote AI cannot be implemented until security defines allowed data classes.
- Blurring adapters, domain logic, and persistence would endanger provenance, testability, and approval controls.
- Credentials and sensitive source content require disciplined logging and retention boundaries.

## 15. Out-of-scope discoveries

None.

## 16. Scope Lock

### In scope

- Update only `docs/plans/architecture-design-analysis.md`.

### Out of scope

- `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, code, dependencies, databases, migrations, integrations, CRM changes, and changes to functional or data-model documents.

### Restrictions

- No implementation or technology selection beyond the approved decisions.
- No change to `main`.
- Commit and push only to `codex-work`.

## 17. Result

**READY FOR APPROVAL**

The approved decisions and existing documentation are sufficient to create `docs/architecture.md` as a separately approved design task.
