# Testing Strategy — Asistente Comercial ACLIMAR

## 1. Goals and pyramid

Testing protects the approval-driven, local-only MVP from incorrect commercial interpretation, duplicate/stale actions, provenance loss, and security regressions. The pyramid is: broad deterministic domain/unit tests; application-service and repository/migration tests; adapter contract tests using controlled doubles; and a small set of synthetic acceptance flows.

pytest is the test framework. Normal tests are isolated from production systems and credentials.

## 2. Domain and application tests

Unit/domain tests cover facts, inferences, and proposals as distinct types; source evidence; exact questions; thread-evidence rules; ambiguous identity/business context; identity corrections; follow-up precedence; alerts; and all approved lifecycles:

- task: `proposed → pending → completed | cancelled`;
- commitment: `detected → confirmed → fulfilled | overdue | cancelled`;
- question: `detected → open → answered | dismissed`;
- next step: `proposed → planned → completed | cancelled`;
- action proposal: `pending_approval → approved | rejected → executed | error`.

Application-service tests cover manual ingestion, analysis orchestration, approval decisions, explicit user confirmation, source deletion/redaction, audit creation, and safe error/degraded-state presentation.

## 3. Persistence and migration tests

Repository tests use isolated SQLite test databases only. They verify SQLAlchemy data access, integrity constraints, CRM references without copied master records, source identifiers, idempotency identities, checkpoints, current state versus history, append-only audit events, and redaction retaining minimum executed-action metadata.

Alembic migration tests upgrade an empty isolated database and applicable prior test revisions, then verify the expected schema/data behavior. They never operate on a user database.

## 4. Adapter and scheduler tests

- **IMAP:** controlled MIME/header fixtures for Message-ID, In-Reply-To, References, duplicate observations, ambiguous subjects, existing folders, draft/move proposals, and failure states.
- **Calendar:** fake or mocked official-client responses for primary-Calendar reads, changed/deleted-at-source reconciliation, and approved create/modify contracts.
- **CRM:** mocked `httpx` contract tests for permitted reads and explicit approved operations only; no `crm.db` access or HTML scraping.
- **AI:** deterministic fake `AIService` tests for structured candidates, untrusted output, no execution authority, and provider independence.
- **Credential store:** fake keyring/Windows Credential Manager tests for logical references, revocation/expiration, and no secret persistence/logging.
- **Scheduler/clock:** deterministic clock and APScheduler-facing tests for intervals, persisted checkpoints, restart recovery, weekend downtime, and Monday incremental catch-up.

## 5. Approval, resilience, and audit tests

Tests must require one concrete approval per external action, target revalidation before execution, idempotent retry behavior, and an execution/audit result for both success and failure.

Failure injection covers unavailable IMAP, Calendar, CRM, AI, credentials, network, scheduler, and persistence. It verifies that one failed integration produces a reconnect/degraded state without preventing local review of stored data.

Audit/provenance tests reconstruct source → extraction → inference → proposal → approval/rejection → execution result, including corrections and identity-link supersession.

## 6. Security, UI, and AI tests

Security tests verify localhost/session/origin/CSRF protections for state-changing UI requests; safe browser errors; no secrets in TOML, SQLite plaintext fields, logs, audit payloads, or rendered responses; and prompt-injection content remaining data rather than instruction.

AI tests enforce the approved disclosure policy: minimized relevant email/metadata/context only; no attachments, credentials, tokens, database/export data, logs/audit records, or unrelated records; and no AI authority to approve or execute actions.

Temporary-file and attachment tests verify metadata-only default behavior and future temp-file controls where applicable.

## 7. Acceptance scenario

An end-to-end synthetic acceptance test uses fakes and fixtures to:

1. ingest an email;
2. reconstruct its thread;
3. identify context only when unambiguous;
4. extract exact questions;
5. retrieve fake CRM context;
6. generate next steps and response/folder proposals;
7. approve one action;
8. revalidate target state;
9. execute a fake message move and fake draft creation;
10. create internal tasks; and
11. record the full audit trail.

It must not contact or mutate production systems.

## 8. Test data and integration policy

Fixtures use synthetic names, companies, projects, offers, messages, Calendar events, and CRM records. Development/test credentials are separate from production credentials and normally unnecessary because adapters are faked.

Future real integration tests are explicit opt-in, use non-production accounts/environments only, require separate configuration, and are excluded from normal runs.

## 9. Regression, coverage, and prohibited behavior

Every defect in lifecycle, provenance, synchronization, approval, security, or integration behavior receives a regression test. Coverage focuses on domain, security-critical, approval/revalidation, idempotency, and recovery paths rather than a universal percentage target.

Normal automated tests must never send real email, move real messages, create real drafts, modify real Calendar/CRM data, use production credentials, transmit real commercial data to remote AI, expose secrets in logs, access `crm.db`, or depend on live production integrations.

CI/release automation, coverage thresholds, performance testing, and any real-integration test harness are deferred to later implementation/release planning.
