# Security Design Analysis

**Status:** BLOCKED

## 1. Objective and context

Analyze security and data-governance requirements for the local, single-user ACLIMAR Commercial Assistant. The application is localhost-only, uses SQLite for assistant data, TOML only for non-secret configuration, and `keyring` with Windows Credential Manager for credentials. No implementation exists.

## 2. Documentation consulted

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/plans/architecture-decisions.md`
- `docs/plans/technical-stack-decisions.md`
- `docs/plans/security-design-task.md`

`docs/security.md` and `docs/testing-strategy.md` do not exist.

## 3. Confirmed security posture

- The application binds only to `127.0.0.1`; there is no public or LAN exposure by default.
- The local Windows user is the sole user context. A local web UI must not treat localhost as a reason to omit authorization, CSRF protections for state-changing requests, or browser-session protections.
- Credentials and tokens reside in Windows Credential Manager through `keyring`; SQLite, TOML, source code, Git, logs, audit payloads, and error messages must contain no secrets.
- Credentials are independently configurable and revocable. Expiration/revocation disables only the affected integration and surfaces a reconnect state.
- IMAP, Calendar, CRM, notes, WhatsApp, attachments, and AI outputs are untrusted data. Embedded instructions cannot alter rules, reveal secrets, or authorize actions.
- External mutations require a concrete approval decision, target revalidation, idempotent execution, and audit result.
- Source content is retained locally under the approved retention policy; explicit deletion/redaction may remove content but must preserve required executed-action audit metadata.
- Attachments are metadata-only by default, not automatically persisted or transmitted.
- Tests require isolated fixtures/mocks and separate non-production credentials; real mailbox, Calendar, CRM, and production secrets must not be changed or used unnecessarily.

## 4. Trust boundaries and controls to design

- Browser ↔ localhost application: loopback binding, session protection, CSRF protection for mutations, safe error presentation, and no secrets in rendered pages.
- Application ↔ Windows Credential Manager: logical credential references only in application data; retrieval only at integration execution time.
- Application ↔ IMAP/Calendar/CRM: adapter-specific authentication, encrypted transport as required by the provider, least data collection, reconnect isolation, checkpoints, and audit-safe errors.
- Application ↔ AI provider: provider-agnostic boundary, disclosure minimization, no credentials/attachments/database exports, and no execution authority from AI output.
- Persistence/logging/temporary files: classify source content separately from audit metadata, avoid sensitive diagnostic payloads, and define temporary-file lifecycle before use.

## 5. Retention, logs, backups, and recovery implications

Source records, observations, provenance, approvals, executions, and audit events require local persistence. Explicit source deletion/redaction must preserve minimal action-history metadata. Logs must record operational state and failures without credentials or unnecessary source bodies. Backup, restoration, local file protection, and temporary-file lifecycle must be specified in `docs/security.md`; automatic cloud backup is outside the MVP.

## 6. Remote-AI disclosure decision required

**STOP — the exact policy is a material unresolved security decision.**

The approved documents state only that remote AI may receive the minimum required data and that `docs/security.md` must define allowed data classes. They do not decide whether the following commercial data may leave the device:

| Data class | Required decision |
| --- | --- |
| Email body and metadata | Allow, prohibit, or allow only minimized/redacted excerpts. |
| Contact and company identity | Allow identifiable values, require pseudonymization, or prohibit. |
| Work/project and opportunity/offer context | Allow, minimize/redact, or prohibit. |
| Manual notes and pasted WhatsApp text | Allow, require confirmation/redaction, or prohibit. |
| Calendar event data and CRM-derived context | Allow specific fields only, minimize/redact, or prohibit. |
| Attachments | Must remain prohibited from automatic transmission. |
| Credentials/tokens and whole database exports | Must remain prohibited. |
| Logs/audit data and unrelated records | Must remain prohibited unless an explicit future policy says otherwise. |

This choice materially affects privacy, data governance, AI adapter design, user consent, logs, testing, and incident handling. It cannot be inferred from the current documentation.

## 7. Risks

- Sending identifiable commercial source content to a remote AI without an approved policy could expose customer, pricing, project, or opportunity information.
- Localhost-only operation still permits browser-origin and local-user risks if state-changing requests lack CSRF/session controls.
- Secrets or sensitive source content may leak through error handling, logs, temporary files, backups, or audit payloads.
- Treating AI output as trusted could bypass approval, provenance, and prompt-injection controls.
- Weak revalidation or idempotency could execute stale or duplicated approved actions.

## 8. Out-of-scope discoveries

None.

## 9. Scope Lock

### In scope

- Analyze security and data-governance requirements.
- Create only `docs/plans/security-design-analysis.md`.

### Out of scope

- `docs/security.md`, `docs/testing-strategy.md`, code, dependencies, configuration files, credentials, database changes, external integrations, CRM changes, and changes to functional/data-model/architecture documents.

### Restrictions

- No implementation, secrets, or real credential handling.
- No change to `main`; commit/push only to `codex-work`.

## 10. Result

**BLOCKED**

Approve the remote-AI disclosure matrix in section 6 before creating `docs/security.md`.
