# Security and Data Governance — Asistente Comercial ACLIMAR

## 1. Objectives and threat model

The MVP protects commercial source content, CRM context, credentials, approvals, and audit history in a local, single-user Windows application. Primary threats are local unauthorized access, credential leakage, browser-origin attacks, untrusted-content prompt injection, accidental external mutation, excessive remote-AI disclosure, sensitive logs/errors/temp files, and compromised dependencies.

The application is not a public service. It must nevertheless protect localhost state-changing operations and treat all external content as hostile data.

## 2. Trust boundaries and network posture

The FastAPI/Uvicorn process binds only to `127.0.0.1`. No LAN/public binding, hosted backend, SaaS, or remote administration is part of the MVP.

Trust boundaries are: browser↔localhost UI; application↔SQLite; application↔Windows Credential Manager; application↔IMAP/Google/CRM; and application↔future AI provider. External adapters provide data, never application authority.

The local Windows user is the intended sole user. Browser sessions must be scoped to the local application, avoid exposing secrets in rendered pages, and protect state-changing requests with CSRF defenses. Localhost does not waive session, origin, or CSRF protections.

## 3. Credentials and tokens

Python `keyring` uses Windows Credential Manager for IMAP credentials, Google OAuth tokens, CRM authentication material, AI credentials, and other secrets. Each integration has an independently manageable credential reference.

Secrets must never be stored in source code, Git, TOML, SQLite plaintext fields, normal logs, audit payloads, error text, or browser responses. TOML contains only non-secret settings. SQLite may store only logical credential references where necessary.

Credential expiration, revocation, or authentication failure disables only the affected integration and presents a reconnect/configuration state. Credentials are retrieved only for the relevant adapter operation and are never sent as AI context.

## 4. Untrusted external data and approval integrity

Email, notes, WhatsApp text, Calendar data, CRM responses, attachments, and AI output are untrusted data. Embedded text cannot request commands, secrets, configuration changes, permission changes, or external actions.

AI output can only be candidate facts, inferences, proposals, summaries, questions, commitments, tasks, next steps, or drafts. It has no execution authority.

Every external mutation follows:

```text
ActionProposal → explicit approval → target revalidation → idempotent execution → audit result
```

Approval is per concrete action. Revalidation protects against changed mailbox, Calendar, or CRM state. Idempotency identities prevent duplicate actions and reduce replay risk.

## 5. Remote-AI disclosure policy

Remote AI receives only the smallest context needed for one concrete analysis operation.

| Data class | Policy |
| --- | --- |
| Email body | Allowed with minimization: relevant message, excerpt, or thread subset only. |
| Email metadata | Allowed only when relevant: sender, needed recipients, subject, date/time, and thread references. |
| Contact/company identity | Allowed when materially useful to the specific analysis. |
| Work/project/opportunity/offer context | Allowed selectively and minimized to relevant identity, status, activity, commitment, or next step. |
| Manual notes/WhatsApp | Allowed when intentionally processed; only relevant content and context. |
| Calendar data | Allowed with minimization for concrete scheduling/meeting workflows. |
| CRM-derived context | Allowed selectively; no full histories or unrelated records. |
| Attachments | Automatic transmission prohibited. |
| Credentials, tokens, secrets | Always prohibited. |
| SQLite databases, dumps, exports, mailbox archives | Always prohibited. |
| Logs and audit data | Prohibited by default. |
| Unrelated records | Always prohibited. |

Where practical, remove unnecessary passwords, tokens, banking details, unrelated identifiers, and sensitive commercial information before transmission. A future attachment-analysis workflow requires separate scope, explicit user action/approval, and security review.

## 6. Data retention, deletion, and audit

Processed email content, original notes, original pasted WhatsApp, and required Calendar/CRM metadata remain local until explicit deletion. There is no automatic age-based deletion. Attachments are metadata-only by default.

Explicit deletion/redaction may remove source content, but executed-action audit history retains minimum identity, action, timestamps, and outcome. Corrections and identity-link changes add history instead of silently rewriting it.

Audit payloads must contain minimum necessary provenance and outcome data, never credentials and never unnecessary full source bodies.

## 7. Logs, errors, temporary files, backups

Logs record operational status, checkpoints, integration degradation, action outcomes, and failures without secrets or unnecessary source content. Errors shown in the browser must be safe, concise, and non-sensitive.

Temporary files are avoided by default. If a future workflow requires them, they must be local, access-restricted, minimized, cleaned after use, and excluded from AI transmission unless separately approved.

Automatic cloud backup is outside the MVP. Any local backup/recovery mechanism must preserve local-user protection, encryption/access requirements defined during implementation, retention rules, and recoverable audit history.

## 8. Local protection, development, and supply chain

Assistant data is accessible only in the local user context. File permissions and Windows account protections must prevent unintended access by other users. SQLite, TOML, logs, backups, and temp locations must not be shared or publicly exposed.

Development/test credentials are separate from production credentials. pytest uses fixtures, fakes, mocks, or controlled test doubles; tests must not send real email, move messages, create drafts, alter Calendar/CRM data, or use production credentials unnecessarily.

Dependencies must be declared, version-controlled, reviewed, and updated deliberately. New packages require approval through project workflow; dependency sources must be trusted and vulnerabilities addressed before release planning.

## 9. Degraded states and deferred decisions

IMAP, Calendar, CRM, and AI failures are isolated. The application remains available for stored local information and shows integration-specific reconnect status. Failure records remain auditable without secrets.

Deferred: concrete encryption and backup implementation, exact filesystem locations/permissions, session-cookie details, CSRF mechanism, dependency scanning tooling, incident-response process, and specific AI provider/model. These require implementation planning and must not weaken this policy.

## 10. Prohibited shortcuts and out-of-MVP controls

Prohibited: direct CRM database access, HTML scraping, secrets in code/config/database/logs, public/LAN binding by default, automatic email sending, autonomous external writes, trusting embedded instructions, bulk AI disclosure, automatic attachment AI transmission, and bypassing approval/revalidation/audit.

Out of MVP: public authentication/multi-user authorization, cloud backup, remote administration, automatic WhatsApp ingestion, attachment analysis, and autonomous agents.
