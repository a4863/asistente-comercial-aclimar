# Security Design Analysis

**Status:** READY FOR APPROVAL

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
- `docs/plans/remote-ai-data-policy.md`

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

## 6. Remote-AI disclosure matrix

Remote AI receives only the smallest context necessary for one concrete analysis operation. It has no execution authority.

| Data class | Policy |
| --- | --- |
| Email body | Allowed with minimization: relevant message, excerpt, or thread subset only. |
| Email metadata | Allowed only when relevant: sender, relevant recipients, subject, date/time, and necessary thread references. |
| Contact/company identity | Allowed when materially useful to the specific analysis; pseudonymization is not required by default. |
| Work/project and opportunity/offer context | Allowed with minimization: relevant identity, status, recent activity, commitments, and next steps only. |
| Manual notes and pasted WhatsApp text | Allowed when intentionally processed or required by the concrete workflow; only relevant content/context. |
| Calendar data | Allowed with minimization: relevant title, participants, timing, description, and linked context. |
| CRM-derived context | Allowed selectively: relevant company/contact/project/opportunity/offer/status and recent commercial context only. |
| Attachments | Automatic transmission prohibited. Future analysis needs separate scope, explicit user action/approval, and security review. |
| Credentials/tokens/secrets | Always prohibited. |
| Whole databases, dumps, exports, mailbox archives | Always prohibited. |
| Logs and audit data | Prohibited by default in the MVP. |
| Unrelated records | Always prohibited. |

When practical, unnecessary passwords, tokens, banking details, unrelated identifiers, and sensitive commercial details must be removed before transmission. AI output remains only candidate facts, inferences, proposals, summaries, questions, commitments, tasks, next steps, or drafts. It cannot approve or execute actions, alter configuration, access credentials, or override rules.

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

**READY FOR APPROVAL**

The approved remote-AI policy resolves the material disclosure ambiguity. The security requirements are sufficiently specified to create `docs/security.md` as a separate approved task.
