# Functional Specification — Asistente Comercial ACLIMAR

## 1. Purpose

The purpose of this application is to provide Alejandro with a local, single-user commercial assistant that helps him manage and prioritize his daily commercial activity.

The assistant must centralize and analyze information from:

- corporate email through IMAP;
- Google Calendar;
- manually entered commercial notes;
- manually pasted WhatsApp conversations;
- the ACLIMAR CRM through its API.

The assistant must help identify:

- pending responses;
- questions;
- commitments;
- next steps;
- overdue follow-ups;
- commercial risks;
- meetings requiring preparation;
- opportunities requiring attention;
- actions that should be proposed to the user.

The assistant is not an autonomous sales agent.

It analyzes, proposes, prioritizes and prepares actions.

Actions that mutate external systems require explicit user approval in the MVP.

---

## 2. Operating Context

The application is:

- local;
- single-user;
- executed on Alejandro's computer;
- intended exclusively for Alejandro's commercial activity.

There is no multi-user requirement.

There is no hosted assistant backend.

There is no SaaS deployment.

There is no mobile application requirement in the MVP.

The local-only requirement refers to execution and persistence of the assistant itself.

Outbound network connections are allowed when required for approved integrations.

---

## 3. External Systems

The MVP may communicate with:

### 3.1 ACLIMAR email

Initial account:

```text
alexllopez@aclimar.com
```

Protocol:

- IMAP for mailbox access;
- SMTP may exist technically but automatic sending is prohibited in the MVP.

The application must not depend on Outlook desktop internals.

Outlook may continue to be used by Alejandro as his normal email client.

---

### 3.2 Google Calendar

The assistant may:

- read events automatically;
- propose event creation;
- propose event modification.

Creation or modification requires explicit approval.

Deleting calendar events is outside the MVP.

---

### 3.3 ACLIMAR CRM

The CRM is a separate local application.

The CRM remains the system of record for:

- companies;
- contacts;
- works/projects;
- opportunities;
- offers.

The assistant must access the CRM exclusively through its API.

The assistant must never access the CRM database directly.

---

### 3.4 AI model

The assistant may use an AI model according to the future approved architecture.

The functional specification does not select:

- provider;
- local model;
- remote model;
- model family;
- API implementation.

That is an architectural decision.

---

## 4. Core Principles

The MVP must follow these principles.

### 4.1 Human approval

External mutations require explicit user approval.

### 4.2 Traceability

The system must preserve the relationship between:

```text
SOURCE
→ EXTRACTION
→ INFERENCE
→ PROPOSAL
→ APPROVAL / REJECTION
→ EXECUTION
```

### 4.3 No silent assumptions

If two or more reasonable interpretations exist, the assistant must not silently select one.

### 4.4 Facts and inferences are different

The assistant must distinguish:

- extracted fact;
- inference;
- proposal.

### 4.5 Original source preservation

Source information required for provenance must remain available.

---

# 5. Email

## 5.1 Email ingestion

The assistant must connect to the configured corporate mailbox through IMAP.

The MVP initially supports one mailbox.

The assistant must detect and process new or changed messages incrementally.

---

## 5.2 Initial synchronization

Initial synchronization must use a configurable historical window.

Default:

```text
30 days
```

The MVP does not require importing the entire historical mailbox.

---

## 5.3 Email content

The assistant must be able to obtain the information required to analyze a message, including when available:

- sender;
- recipients;
- subject;
- timestamp;
- Message-ID;
- In-Reply-To;
- References;
- mailbox folder;
- message body;
- attachment metadata.

Attachments are not downloaded or persisted automatically in the MVP.

---

## 5.4 Thread reconstruction

Thread reconstruction must prioritize technical email evidence:

1. `Message-ID`
2. `In-Reply-To`
3. `References`

Normalized subject may be used only as secondary evidence.

Participants, dates and CRM context may help classification but must not by themselves justify merging different conversations.

If evidence is insufficient, messages remain separated.

The assistant must not silently merge ambiguous threads.

---

## 5.5 Email analysis

For each relevant email or thread, the assistant should detect when applicable:

- summary;
- customer/company;
- contact;
- work/project;
- opportunity;
- offer;
- questions asked;
- questions still unanswered;
- commitments made by Alejandro;
- commitments made by the other party;
- requested documentation;
- requested actions;
- deadlines;
- next steps;
- possible commercial risk;
- response requirement;
- priority.

---

## 5.6 Exact questions

When an email contains questions, the assistant must be capable of presenting the exact questions separately from the summary.

The system must preserve enough source evidence to verify what was actually asked.

---

## 5.7 Email classification and filing

The assistant must discover the existing IMAP folder structure.

The existing mailbox organization may contain folders by:

- customer;
- contact/interlocutor;
- work/project;
- other existing commercial classifications.

The assistant must learn from and use the existing folder structure.

The MVP may only recommend existing folders.

It must not automatically create folders.

---

## 5.8 Filing proposal

After an email has been analyzed, the assistant may propose the most appropriate existing folder.

If several folders are reasonably plausible, the assistant must present alternatives.

It must not silently resolve ambiguous filing.

---

## 5.9 Filing execution

Filing means:

```text
MOVE message to an existing IMAP folder
```

It does not mean:

- copy;
- label;
- automatic archive;
- automatic folder creation.

Every move requires explicit approval.

---

## 5.10 Reply proposals

When the assistant detects that an email should be answered, it may propose a reply.

The assistant should explain:

- why a response appears necessary;
- what points should be addressed;
- which questions must be answered;
- any known deadlines or commitments.

---

## 5.11 Draft creation

The assistant must show the proposed reply before creating a mailbox draft.

The application must ask the user whether to create the draft.

Only after approval may the assistant create it in the mailbox Drafts folder.

---

## 5.12 Draft safety

The MVP must never send email automatically.

The assistant must avoid duplicate drafts.

Repeated execution of the same approved draft operation must not create unnecessary duplicates.

---

# 6. Manual Commercial Notes

## 6.1 Note entry

The application must provide a simple mechanism for Alejandro to enter free-text commercial notes.

Notes may represent:

- calls;
- meetings;
- site visits;
- informal conversations;
- customer feedback;
- internal reflections;
- agreements;
- follow-up reminders.

---

## 6.2 Original note preservation

The original note must be preserved unchanged.

Structured analysis must not replace the source note.

---

## 6.3 Note analysis

The assistant should extract when applicable:

- interaction type;
- date;
- company;
- contact;
- work/project;
- opportunity;
- offer;
- facts;
- questions;
- commitments;
- tasks;
- deadlines;
- next steps;
- risks;
- priority.

---

## 6.4 Ambiguous relationships

If a note could reasonably correspond to more than one:

- company;
- contact;
- work;
- opportunity;
- offer;

the assistant must ask for confirmation rather than assigning the relationship silently.

---

# 7. Manual WhatsApp Input

## 7.1 Scope

The MVP supports manually pasted WhatsApp text.

No WhatsApp API integration is included.

---

## 7.2 Supported content

The MVP processes text only.

Outside MVP:

- images;
- voice notes;
- documents;
- automated transcription;
- webhook ingestion;
- WhatsApp automation.

---

## 7.3 Processing

Pasted WhatsApp conversations are analyzed similarly to email and notes.

The assistant should detect:

- participants;
- subject/context;
- facts;
- questions;
- commitments;
- deadlines;
- tasks;
- next steps;
- CRM relationships.

The original pasted text must be preserved as source evidence.

---

# 8. Google Calendar

## 8.1 Read operations

The assistant may automatically read calendar information required for:

- daily briefing;
- meeting preparation;
- follow-up context;
- identifying scheduled commercial commitments.

---

## 8.2 Event creation

The assistant may propose creation of a new event.

Creation requires explicit user approval.

---

## 8.3 Event modification

The assistant may propose modification of an existing event.

Modification requires explicit approval.

---

## 8.4 Event deletion

Deleting calendar events is outside the MVP.

## 8.5 Calendar synchronization scope

The MVP synchronizes one configured primary Google Calendar.

All events in the configured synchronization range may be read. The assistant determines commercial relevance during analysis.

If an event is modified directly in Google Calendar, the next synchronization must update the current local representation while preserving relevant provenance and history.

If an event is deleted at source:

- it must no longer be treated as active;
- its local historical reference must be retained and marked as deleted at source.

Synchronizing multiple calendars is outside the MVP.

---

# 9. CRM Integration

## 9.1 CRM authority

The CRM is authoritative for:

- companies;
- contacts;
- works/projects;
- opportunities;
- offers.

The assistant must not maintain an independent competing master record for those entities.

---

## 9.2 CRM access

CRM integration is API-only.

Direct access to the CRM database is prohibited.

The assistant must depend on an explicit CRM API contract and must not depend on CRM internal implementation details.

---

## 9.3 CRM read operations

The assistant may retrieve CRM information required to:

- identify a company;
- identify a contact;
- identify a work/project;
- identify an opportunity;
- identify an offer;
- understand commercial context;
- prepare a meeting;
- link activity.

---

## 9.4 CRM update proposals

The assistant may propose:

- logging an interaction;
- creating a follow-up;
- updating a follow-up;
- recording a next step;
- recording a next-step date;
- updating opportunity status;
- updating offer status;

when the CRM API supports the action and the proposal is supported by the source information.

---

## 9.5 CRM approval

Every CRM write operation requires explicit user approval in the MVP.

---

## 9.6 CRM prohibited automatic actions

The assistant must never automatically:

- delete CRM records;
- modify financial amounts;
- change company identity;
- change contact identity;
- overwrite master data;
- create unsupported business rules.

## 9.7 CRM functional API contract

The CRM API must provide the following read capabilities:

- companies;
- contacts/interlocutors;
- works/projects;
- opportunities;
- offers;
- interactions/follow-ups.

Where applicable, the API must support lookup by:

- ID;
- name;
- email;
- company;
- work/project;
- status.

Permitted MVP writes, always after explicit user approval, are:

- create a commercial interaction;
- create a follow-up;
- update a follow-up;
- record a next step and date;
- associate an interaction with company, contact, work, or opportunity;
- perform an opportunity or offer status transition only through an explicit CRM business operation exposed by the CRM API.

The following are forbidden:

- direct access to `crm.db`;
- HTML scraping as an integration mechanism;
- arbitrary database-field updates;
- deletion of CRM records;
- automatic company or contact creation;
- automatic master-data modification;
- automatic financial amount modification.

If the CRM lacks required API endpoints, they must be implemented separately in the CRM repository through that project's approved Analyze, Plan, Scope Lock, Implement, and Review workflow.

---

# 10. Activities

An activity represents a commercial interaction or event processed by the assistant.

Possible activity types include:

- email;
- call;
- meeting;
- visit;
- WhatsApp;
- manual note;
- calendar event;
- other approved types.

Activities should be linkable to CRM context where available.

---

# 11. Tasks

## 11.1 Definition

A task represents an action that should be performed.

Example:

```text
Send homologation documentation before Friday.
```

---

## 11.2 Task lifecycle

The assistant may automatically create internal task records from detected or generated information without user approval, because this does not mutate an external system.

Initial state:

```text
detected/generated
→ proposed
```

Initial functional lifecycle:

```text
proposed
→ pending
→ completed | cancelled
```

---

# 12. Commitments

## 12.1 Definition

A commitment represents a promise or agreed action made by Alejandro or another participant.

Example:

```text
Customer will send measurements on Thursday.
```

---

## 12.2 Commitment lifecycle

The assistant may automatically create an internal commitment record from detected information without user approval.

Initial state:

```text
detected
```

```text
detected
→ confirmed
→ fulfilled | overdue | cancelled
```

The assistant may automatically mark a confirmed commitment as overdue when its confirmed due date has passed.

---

# 13. Questions

## 13.1 Definition

A question represents something requiring an answer or resolution.

---

## 13.2 Question lifecycle

The assistant may automatically create an internal question record from detected information without user approval.

Initial state:

```text
detected
```

```text
detected
→ open
→ answered | dismissed
```

---

# 14. Next Steps

## 14.1 Definition

A next step represents the agreed or proposed next commercial action.

---

## 14.2 Next-step lifecycle

The assistant may automatically create an internal next-step record from detected information without user approval.

Initial state:

```text
proposed
```

```text
proposed
→ planned
→ completed | cancelled
```

The assistant must not automatically mark tasks, commitments, questions, or next steps as completed, fulfilled, or answered unless explicit later source evidence proves the outcome or Alejandro confirms it.

---

# 15. Action Proposals

The assistant may generate action proposals.

Examples:

- move email;
- create draft;
- create task;
- update CRM;
- create Calendar event;
- modify Calendar event.

Lifecycle:

```text
pending_approval
→ approved | rejected
→ executed | error
```

An approved action must correspond to one concrete action.

Approval cannot silently authorize unrelated actions.

---

# 16. Facts, Inferences and Proposals

## 16.1 Extracted fact

Information explicitly present in the source.

Example:

```text
The customer says measurements will arrive Thursday.
```

---

## 16.2 Inference

A conclusion produced by the assistant.

Example:

```text
The offer may be delayed if measurements are not received.
```

Inference must remain marked as inference.

---

## 16.3 Proposal

A recommended action.

Example:

```text
Call the customer Friday morning if measurements have not arrived.
```

A proposal remains a proposal until approved.

---

## 16.4 Promotion to confirmed fact

An inference may become a confirmed fact only when:

- Alejandro explicitly confirms it; or
- later authoritative source evidence supports it.

An inference must never silently become CRM factual data.

---

# 17. Follow-up Rules

## 17.1 Default thresholds

Initial configurable defaults:

```text
New or qualified opportunity: 7 days
Sent offer: 5 days
Homologation/documentation: 7 days
Negotiation/review: 5 days
```

---

## 17.2 Configuration hierarchy

The system must support overrides.

Precedence:

```text
opportunity / offer / work
→ company / contact
→ global default
```

---

## 17.3 Explicit future dates

An explicitly agreed future date takes precedence over inactivity thresholds.

Example:

If a customer says:

```text
I will answer on September 30.
```

the assistant should not consider the opportunity inactive before that date solely because the generic threshold has elapsed.

---

## 17.4 Follow-up output

Rules may automatically generate:

- alerts;
- priorities;
- task proposals;
- follow-up proposals.

They may not automatically perform external actions.

---

# 18. Daily Dashboard

The application must provide a daily operational view.

The objective is not merely to display records.

It must help Alejandro understand what requires attention.

---

## 18.1 Suggested sections

The dashboard may include:

### High priority

Examples:

- unanswered customer request;
- overdue commitment;
- urgent offer;
- documentation deadline.

### Meetings

Today’s meetings and relevant preparation context.

### Follow-ups

- overdue;
- due today;
- upcoming.

### Email

- messages requiring response;
- messages awaiting classification;
- draft proposals;
- filing proposals.

### Opportunities

Opportunities or offers requiring attention according to configured rules.

---

# 19. Meeting Preparation

Before a scheduled meeting, the assistant should be able to provide relevant context when available:

- company;
- contact;
- work/project;
- open opportunities;
- open offers;
- latest interactions;
- pending questions;
- pending commitments;
- overdue tasks;
- suggested discussion points.

---

# 20. Post-Meeting Processing

After a meeting, call or visit, Alejandro may enter a free-text note.

The assistant should propose:

- activity registration;
- extracted facts;
- commitments;
- tasks;
- next steps;
- deadlines;
- CRM relationships;
- possible CRM updates.

Ambiguous proposals require confirmation.

---

# 21. Identity Matching

The assistant must prefer authoritative identifiers.

Priority examples:

1. exact email address;
2. CRM ID;
3. previously confirmed relationship;
4. other reliable identifiers.

Names, subject similarity or contextual similarity may generate suggestions.

They must not silently resolve ambiguity.

## 21.1 Confirmed identity links

A user-confirmed identity relationship may be reused across email, manual notes, manually pasted WhatsApp, and Calendar. For example:

```text
email address
→ person
→ CRM contact ID
```

A confirmed identity link must record its confirmation timestamp and provenance. It does not automatically expire, may be manually corrected, and must preserve correction history rather than silently rewriting history.

Confirmed identity does not automatically determine work, project, or opportunity context when multiple valid contexts exist. Ambiguous business-context relationships still require confirmation.

---

# 22. Local Assistant Database

The assistant must use a database separate from the CRM database.

This database stores the assistant's operational information.

Conceptually this includes:

- processed activity;
- source metadata;
- conversations;
- notes;
- tasks;
- commitments;
- questions;
- next steps;
- proposals;
- approvals;
- alerts;
- follow-up preferences;
- CRM links;
- audit information.

The exact physical model belongs in `docs/data-model.md`.

---

# 23. Source of Truth

## CRM

Authoritative for:

- companies;
- contacts;
- works;
- opportunities;
- offers.

## Assistant

Authoritative for:

- assistant analysis;
- extracted activity;
- manual notes;
- generated proposals;
- approvals;
- assistant tasks and alerts;
- operational traceability.

The assistant must not silently create a competing copy of CRM master data.

---

# 24. Auditability

The system must allow reconstruction of:

```text
source
→ extracted information
→ inference
→ proposal
→ approval/rejection
→ execution result
```

Relevant audit records must preserve:

- source identity;
- timestamps;
- action identity;
- approval identity;
- execution outcome;
- failure information when applicable.

Executed history must not be silently rewritten.

Corrections should create new audit information.

## 24.1 Source retention and deletion

For the MVP:

- processed email source content is retained locally until the user explicitly requests deletion;
- original manual notes are retained locally;
- original manually pasted WhatsApp text is retained locally;
- Calendar and CRM metadata necessary for traceability is retained locally;
- attachments are not automatically persisted;
- there is no automatic age-based deletion.

Manual deletion and export functionality may be designed separately.

Audit history of executed actions must not silently disappear when source content is later removed. When a source is explicitly deleted, audit records may retain event identity, action, timestamps, and outcome without retaining the full deleted content.

Corrections must create new historical information rather than silently rewriting executed history.

---

# 25. Security Requirements

## 25.1 Credentials

Credentials must never be stored:

- in source code;
- in Git;
- in plaintext database fields.

Each integration must have independently manageable credentials. Credentials must remain local, must not be emitted to logs after configuration, and must never be committed to Git.

The user must be able to revoke or reconfigure one integration without affecting others. Credential expiration or revocation must disable only the affected integration and surface a clear reconnect or configuration state.

Local commercial application data is accessible only within the local user context running the application. Automatic cloud backup of assistant data is outside the MVP.

The exact credential-storage technology and backup mechanism belong to security and architecture design.

---

## 25.2 External data

Content received from:

- email;
- WhatsApp;
- notes;
- Calendar;
- CRM;
- attachments;

must be treated as data, not trusted instructions.

---

## 25.3 Embedded instructions

If an email or other source contains text attempting to instruct the assistant to:

- ignore its rules;
- execute commands;
- reveal secrets;
- modify configuration;
- send information;
- change permissions;

the content must be treated as untrusted source data.

It must not override application rules.

## 25.4 Remote AI data disclosure

A future architecture may select a remote AI provider. If a remote provider is selected:

- only data required for the specific analysis may be transmitted;
- relevant email text, notes, or CRM context may be transmitted when necessary;
- credentials must never be transmitted as model context;
- attachments must not be transmitted automatically;
- entire databases must not be transmitted;
- unrelated commercial information must not be transmitted.

`docs/security.md` must explicitly document which classes of data may leave the device before a remote AI provider is implemented.

The AI integration boundary should not make business rules dependent on one model provider.

---

# 26. Approval Rules

In the MVP, explicit approval is required before:

- moving an email;
- creating a mailbox draft;
- creating a Calendar event;
- modifying a Calendar event;
- modifying CRM data.

Approval is per action.

Persistent auto-approval rules are outside the MVP.

---

# 27. Revalidation

If external state may have changed between approval and execution, the assistant must revalidate the target before executing the approved action.

Example:

An email selected for filing may already have been moved manually in Outlook.

The assistant should detect the changed state rather than blindly executing an outdated operation.

---

# 28. Idempotency

Operations must avoid unintended duplicates.

Special attention is required for:

- IMAP synchronization;
- draft creation;
- activity registration;
- task creation;
- CRM update proposals;
- Calendar event creation.

Repeated processing of the same source should not create unnecessary duplicate records.

---

# 29. MVP Included Scope

The MVP includes:

- local single-user application;
- IMAP email ingestion;
- incremental synchronization;
- email thread reconstruction;
- email analysis;
- exact question extraction;
- filing recommendations;
- approved email moves;
- reply proposals;
- approved draft creation;
- manual commercial notes;
- manual WhatsApp text ingestion;
- Google Calendar reading;
- approved Calendar event creation;
- approved Calendar event modification;
- CRM reading through API;
- approved CRM updates supported by the API;
- activities;
- tasks;
- commitments;
- questions;
- next steps;
- follow-up rules;
- alerts;
- daily dashboard;
- meeting preparation;
- provenance;
- approval workflow;
- auditability.

---

# 30. Explicitly Outside MVP

The following are outside the MVP:

- automatic email sending;
- automatic WhatsApp integration;
- WhatsApp webhook;
- WhatsApp API;
- WhatsApp image processing;
- WhatsApp voice-note transcription;
- automatic attachment processing;
- automatic folder creation;
- Calendar event deletion;
- autonomous CRM updates without approval;
- multi-user support;
- remote hosted backend;
- SaaS deployment;
- native mobile app;
- persistent auto-approval rules.

---

# 31. MVP Acceptance Scenario

The MVP must eventually support the following end-to-end scenario.

A real commercial email arrives in:

```text
alexllopez@aclimar.com
```

Without requiring Alejandro to open Outlook first, the local application should be able to:

1. detect the email;
2. reconstruct its thread;
3. analyze its content;
4. identify customer/contact/work when possible;
5. consult CRM context;
6. extract exact questions;
7. detect commitments and next steps;
8. identify whether a response is required;
9. propose a reply;
10. propose an existing mailbox folder;
11. request approval;
12. move the email after approval;
13. create a mailbox draft after approval;
14. generate relevant tasks or follow-up proposals;
15. preserve traceability of what happened.

The email must not be sent automatically.

---

# 32. Functional Constraints

The MVP must remain:

- simple;
- local;
- single-user;
- traceable;
- approval-driven;
- compatible with Alejandro's existing workflow.

The project must not be transformed into:

- enterprise SaaS;
- multi-tenant system;
- autonomous communication agent;
- generic CRM replacement.

---

# 33. Open Technical Decisions

This functional specification intentionally does not decide:

- programming framework;
- UI framework;
- persistence technology;
- database engine;
- migration framework;
- AI model/provider;
- background scheduling mechanism;
- IMAP library;
- Google API library;
- secret-storage implementation;
- packaging method;
- startup mechanism.

These decisions belong to architecture and security design.

No implementation should assume them before those documents are approved.
