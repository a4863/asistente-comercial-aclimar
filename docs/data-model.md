# Data Model — Asistente Comercial ACLIMAR

## 1. Purpose and principles

This document defines the MVP conceptual and logical data model. It is implementation-neutral: it does not select a database engine, ORM, migration system, physical keys, indexes, encryption implementation, or storage mechanism.

The model is local, single-user, traceable, approval-driven, and source-preserving. It must represent current operational state and the history needed to reconstruct:

```text
source → extraction → inference → proposal → approval/rejection → execution result
```

Corrections add historical information; they do not silently rewrite executed history.

## 2. Authority boundaries

The CRM is authoritative for companies, contacts/interlocutors, works/projects, opportunities, and offers. The assistant stores only typed CRM references and metadata needed for context, provenance, and approved API operations. It does not own competing master copies of CRM entities.

The assistant is authoritative for source ingestion, activities, analysis, facts, inferences, proposals, internal tasks and alerts, approvals, executions, configuration references, and audit history.

## 3. Common logical conventions

Every first-class assistant record has a logical identity, creation timestamp, and provenance where it is derived from a source or user decision. Records with mutable operational state expose a current state; state transitions, corrections, approvals, and executions are represented as historical records where auditability is required.

`CRMReference` means a typed external identifier, never a copied CRM master record. `SourceRecord` means the retained source material or source metadata. `SourceObservation` means an observed external version or synchronization fact.

No model entity contains credentials, secrets, or executable instructions from external content.

## 4. Sources and synchronization

### SourceRecord

Represents a source item or manually supplied source material.

Main attributes: logical identity; source type; source-system scope; stable external/source identifier when available; original content or retained source reference; source timestamp; ingestion timestamp; retention state; deletion/redaction state; and provenance.

Supported source types include email message, manual note, manually pasted WhatsApp text, Calendar event, and CRM metadata read. Attachments may be represented as metadata only; attachment content is not automatically persisted.

Logical integrity: a stable external identifier is unique within its source-system scope. A manually created source has a locally assigned logical identity and manual-entry provenance.

### SourceObservation

Represents one synchronization or read observation of a source record.

Main attributes: logical identity; source record; observed timestamp; source version/change marker when available; observed active/deleted status; synchronization outcome; and reconciliation provenance.

Observations distinguish repeated processing from changed external state. They support incremental IMAP synchronization, Calendar updates, and external-state revalidation.

### Source deletion and redaction

`SourceRecord` has an explicit current retention/deletion/redaction state and relevant timestamp. A Calendar event deleted at source is retained historically but inactive. Explicit source deletion may remove sensitive content while retaining the minimum audit metadata for executed actions: event identity, action, timestamps, and outcome.

## 5. Source-specific representations

### EmailMessage and Conversation

`EmailMessage` is a source-specific representation linked to one `SourceRecord`. It records sender, recipients, subject, timestamp, Message-ID, In-Reply-To, References, mailbox folder, body/source reference, and attachment metadata when available.

`Conversation` represents an email thread. It may contain zero or more messages; a message belongs to no conversation when evidence is insufficient, or one conversation when technical evidence supports reconstruction. Thread membership records retain the technical evidence used. Subject, participant, date, and CRM context cannot alone justify a merge.

### ManualNote and WhatsAppImport

`ManualNote` and `WhatsAppImport` are source-specific representations linked to one `SourceRecord`. Each preserves original entered or pasted text unchanged, manual-ingestion provenance, and the relevant input timestamp. WhatsApp imports are text-only in the MVP.

### CalendarEventRepresentation

Represents an event from the one configured primary Calendar. Main attributes: stable Calendar event reference; event timing and relevant metadata; current active/deleted-at-source state; latest observed representation; and source-observation history. It may be analyzed for commercial relevance but is not automatically considered commercial merely because it was synchronized.

## 6. Activities and CRM context

### Activity

Represents a commercial interaction or event. Its allowed types are email, call, meeting, visit, WhatsApp, manual note, Calendar event, and other approved types.

Main attributes: logical identity; type; current descriptive state; relevant occurrence time; source/provenance links; and creation timestamp. An activity may be supported by one or more source records.

### CRMReference and CRMContextLink

`CRMReference` stores CRM entity type and external CRM identifier, plus only the metadata necessary for traceability. Allowed CRM entity types are company, contact/interlocutor, work/project, opportunity, offer, interaction, and follow-up where applicable to the API contract.

`CRMContextLink` associates an assistant record, such as an activity, with a CRM reference. It records relationship purpose, provenance, confirmation/ambiguity status, and timestamps. Links are optional: uncertainty must remain unresolved rather than forcing a CRM association.

## 7. Identity and derived information

### IdentityLink and IdentityLinkCorrection

`IdentityLink` records a user-confirmed reusable relationship between a source-level identity value or person representation and a CRM contact reference. Main attributes: logical identity; identity value/type; target CRM reference; confirmation timestamp; confirmation provenance; current status; and correction/supersession reference.

`IdentityLinkCorrection` records correction or supersession of a prior link with timestamp and provenance. Confirmed links do not expire automatically. Identity links may be reused across email, notes, WhatsApp, and Calendar, but do not resolve ambiguous work, project, or opportunity context.

### ExtractedFact, Inference, and Proposal

These are distinct first-class concepts.

- `ExtractedFact`: information explicitly present in source evidence. It links to the supporting source record(s), extraction provenance, and any correction history.
- `Inference`: an assistant conclusion. It links to supporting sources and/or facts, remains marked as inference, and may record later confirmation by user action or authoritative source evidence.
- `Proposal`: a recommended action or commercial suggestion. It links to its support and remains a proposal until separately approved or rejected where an approval is required.

All three may be related to activities, CRM context links, tasks, commitments, questions, next steps, and alerts. They must never collapse into a single undifferentiated factual record.

## 8. Internal operational objects

### Task

Represents an assistant-owned action to be performed. Main attributes include logical identity, description, current lifecycle state, relevant due date, provenance, and supporting records.

Lifecycle: `proposed → pending → completed | cancelled`. The assistant may create a task internally from detected or generated information. It must not automatically mark it completed without explicit later source evidence or user confirmation.

### Commitment

Represents a promise or agreed action by Alejandro or another participant. Main attributes include logical identity, responsible participant context, due date when confirmed, current lifecycle state, provenance, and supporting records.

Lifecycle: `detected → confirmed → fulfilled | overdue | cancelled`. A confirmed commitment may become overdue automatically when its confirmed due date passes. Fulfilment requires explicit later source evidence or user confirmation.

### Question

Represents an item requiring answer or resolution, including exact questions extracted from sources. It retains source evidence sufficient to show what was asked.

Lifecycle: `detected → open → answered | dismissed`. Answered status requires explicit later source evidence or user confirmation.

### NextStep

Represents an agreed or proposed commercial action. Main attributes include logical identity, description, relevant target date, lifecycle state, provenance, and supporting records.

Lifecycle: `proposed → planned → completed | cancelled`. Completed status requires explicit later source evidence or user confirmation.

### Alert and FollowUpPreference

`Alert` represents an operational signal with generation provenance, priority/context, current state, and related records.

`FollowUpPreference` represents a configurable default or override. It stores the applicable threshold/rule, scope reference, and change history. Logical precedence is opportunity/offer/work, then company/contact, then global default. It references CRM context where needed without copying CRM entities. An explicitly agreed future date takes precedence over inactivity thresholds.

## 9. External action approval and execution

### ActionProposal

Represents exactly one proposed external mutation: an IMAP message move, mailbox draft creation, Calendar event creation/modification, or permitted CRM API operation.

Main attributes: logical identity; action type; target reference; requested payload/reference; source/proposal provenance; current lifecycle state; idempotency identity; and creation timestamp.

Lifecycle: `pending_approval → approved | rejected → executed | error`. Approval of one action proposal cannot authorize another action.

### ApprovalDecision

Represents an explicit user approval or rejection of one action proposal. Main attributes: logical identity; action proposal; decision; decision timestamp; user identity in the local single-user context; and decision provenance. It is immutable.

### ExecutionResult

Represents an attempt to execute an approved action. Main attributes: logical identity; action proposal; attempt timestamp; target revalidation evidence/outcome; execution outcome; external result reference when available; failure information; and idempotency/retry reference.

An approved action may have multiple execution attempts, each separately retained. Execution must revalidate targets when external state could have changed.

## 10. Audit and current state

### AuditEvent

`AuditEvent` is append-only history for material operations and corrections. It links, as applicable, to source records, derived information, lifecycle transitions, identity-link corrections, approval decisions, action proposals, and execution results.

Main attributes: logical identity; event type; affected-record reference; actor/source; timestamp; provenance; and minimal outcome/failure information. Audit events preserve executed history even when source content is later deleted or redacted.

Current operational records provide the current state needed for dashboard and workflow use. Historical records and audit events provide the evidence and transitions needed to reconstruct why that state exists.

## 11. Configuration references

`ConfigurationReference` represents non-secret configuration identity and scope required by the model, such as the configured mailbox identity, primary Calendar identity, source-system scope, and follow-up configuration scope. It contains no credential material.

The MVP has one configured mailbox initially and one configured primary Calendar. Credentials and credential-storage mechanisms are intentionally outside this model.

## 12. Logical integrity and idempotency

- Source identifiers are unique within source-system scope; manual sources have local logical identities.
- A message cannot be assigned to multiple conversations. Uncertain thread membership remains absent.
- CRM context links and identity links preserve their provenance and cannot be treated as confirmed merely through textual similarity.
- Lifecycle records accept only their approved states and must retain transition evidence.
- A confirmed identity correction supersedes rather than deletes the previous link.
- Each action proposal identifies one concrete operation and target; approval/rejection belongs only to that proposal.
- Source processing, draft creation, activity registration, task creation, CRM update proposals, and Calendar event creation require logical idempotency identities or equivalent deduplication evidence.
- Source observations and execution results preserve changed external-state and revalidation evidence.
- Redaction/deletion cannot erase the audit metadata required for completed external actions.

## 13. Deferred physical-design decisions

This document intentionally does not select database engine, storage driver, ORM, migration framework, physical primary-key format, index design, transaction behavior, encryption library, filesystem layout, scheduler, application framework, integration library, AI provider, packaging, or deployment mechanism. Those decisions belong to approved architecture and security design.
