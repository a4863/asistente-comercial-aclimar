# Testing Strategy Design Analysis

**Status:** READY FOR APPROVAL

## 1. Objective and context

Prepare `docs/testing-strategy.md` for the local ACLIMAR Commercial Assistant. The project has approved functional, data-model, architecture, and security documentation, but no implementation or test suite yet.

## 2. Documentation consulted

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- readiness and design-analysis plans for functional specification, data model, architecture, and security
- `docs/plans/testing-strategy-design-task.md`

## 3. Test layers

Use pytest with a test pyramid: broad deterministic domain/unit tests; repository, migration, and application-service tests; adapter contract tests using fakes/mocks; a smaller set of local acceptance flows. No test tier may unintentionally mutate production systems.

### Domain and unit tests

Cover lifecycle transitions; facts/inferences/proposals separation; evidence and provenance; identity ambiguity and correction history; follow-up precedence; source deletion/redaction; thread evidence rules; exact questions; approval requirements; and AI output remaining non-authoritative.

### Persistence and migrations

Use isolated SQLite databases to verify SQLAlchemy repository behavior, Alembic upgrade from an empty database, model integrity constraints, audit append-only behavior, checkpoints, idempotency identities, revalidation evidence, and redaction that preserves required audit metadata.

### Adapters and contracts

IMAP tests use controlled message fixtures covering Message-ID, In-Reply-To, References, ambiguous subjects, folder discovery, incremental changes, and drafts/moves without a real mailbox. Calendar and CRM use fakes or mocked HTTP contracts. AI tests use deterministic provider fakes. Windows Credential Manager/keyring is isolated behind a fake secret store.

## 4. Workflow and resilience tests

- Scheduler/clock tests use a deterministic clock and persisted checkpoints.
- Recovery tests cover restart after downtime and Monday catch-up after weekend shutdown without full resynchronization.
- Approval/execution tests require one concrete approval, target revalidation, idempotent retries, and auditable failure/result records.
- Degraded-state tests inject IMAP, Calendar, CRM, AI, credential, persistence, and network failures and confirm local review remains available with integration-specific reconnect states.

## 5. Security, AI, and UI tests

Security tests verify no secrets in configuration, SQLite plaintext fields, logs, errors, audit payloads, or rendered UI; untrusted embedded instructions cannot change behavior; CSRF/session/origin protections apply to localhost state changes; and temp/attachment policies are respected.

AI-boundary tests enforce the approved disclosure matrix: minimized relevant content only; no credentials, attachments, database exports, logs/audit payloads, or unrelated records; and no AI execution authority.

UI tests cover review/approval forms, CSRF behavior, validation, safe error handling, and no mutation without explicit confirmation.

## 6. Acceptance and data strategy

Acceptance tests model the approved real-email scenario entirely with synthetic fixtures: ingest, thread, analyze, link context when unambiguous, extract questions, propose filing/draft/task/follow-up, approve, revalidate, execute through fakes, and audit.

Fixtures use synthetic commercial identities and generated messages. Development/test credentials are distinct from production credentials. Any future real integration test is opt-in, explicitly configured for non-production accounts/environments, and excluded from normal test runs.

## 7. Regression and coverage

Regression tests accompany every defect in lifecycle, synchronization, approval, provenance, security, or integration behavior. Coverage should emphasize domain, approval/revalidation, idempotency, and security-critical paths rather than a universal percentage target. Critical acceptance scenarios and forbidden actions require explicit tests.

## 8. Ambiguities

**None that block creation of `docs/testing-strategy.md`.** The approved pytest stack and safety constraints provide sufficient direction. Concrete coverage thresholds and CI automation are implementation/release decisions to document later without weakening safety constraints.

## 9. Risks

- Real integration credentials or accounts accidentally entering normal tests.
- Nondeterministic time/scheduler behavior hiding checkpoint failures.
- Mock contracts drifting from IMAP, Calendar, or CRM behavior.
- Tests asserting happy paths but missing revalidation, duplicate, redaction, and degraded-state behavior.

## 10. Out-of-scope discoveries

None.

## 11. Scope Lock

### In scope

- Analyze testing strategy.
- Create only `docs/plans/testing-strategy-design-analysis.md`.

### Out of scope

- `docs/testing-strategy.md`, code, tests, dependencies, credentials, databases, migrations, external integrations, CRM changes, and changes to approved design documents.

### Restrictions

- No implementation or external-system mutation.
- No production credentials or change to `main`; commit/push only to `codex-work`.

## 12. Result

**READY FOR APPROVAL**

The approved documentation is sufficient to create `docs/testing-strategy.md` as a separate approved task.
