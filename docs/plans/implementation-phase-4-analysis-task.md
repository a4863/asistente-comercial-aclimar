# Phase 4 Analysis Task — Email/Thread Analysis and AIService Boundary

**Status:** Approved for Analyze Task only
**Date:** 2026-09-23
**Prerequisite:** Phase 3D3 ACCEPTED
**Mode:** READ-ONLY analysis. Do not implement.

## Objective

Analyze the next implementation phase after accepted email ingestion + synchronization + thread reconstruction.

The next capability must transform one reconstructed email conversation/thread into traceable commercial analysis, including when applicable:

- concise summary;
- exact questions;
- unanswered questions;
- commitments by Alejandro;
- commitments by the other party;
- requested documentation/actions;
- dates/deadlines;
- next steps;
- response-needed signal;
- commercial risk;
- priority;
- candidate commercial context.

This phase must preserve:
source -> extraction -> inference -> proposal
and must not give AI any execution authority.

## Authoritative inputs

Read at minimum:
- AGENTS.md
- docs/functional-spec.md
- docs/data-model.md
- docs/architecture.md
- docs/security.md
- docs/testing-strategy.md
- docs/plans/remote-ai-data-policy.md
- docs/plans/implementation-phase-3d3-plan.md
- app/domain/email_threading.py
- app/services/email_thread_reconstruction.py
- app/persistence/models.py
- app/persistence/repositories.py
- existing tests relevant to facts/inferences/proposals/questions/commitments/tasks/next steps

Do not inspect caches, __pycache__, .pytest_cache, generated temp files, or untracked files outside the task.

## Questions the analysis MUST resolve

### A. Analysis unit and trigger
Determine:
- whether analysis unit is one Conversation, latest message, or bounded relevant thread subset;
- how to avoid reanalyzing unchanged content;
- what revision/idempotency identity should govern analysis replay;
- whether new email in an existing thread causes full-thread reanalysis or bounded incremental analysis.

### B. Input minimization
Define the minimum analysis input:
- which message bodies;
- sender/recipient/subject/date metadata;
- technical thread data;
- whether quoted previous-message text should be minimized/deduplicated;
- whether attachments remain metadata-only;
- how remote-AI disclosure policy is enforced before provider call.

No whole mailbox, whole DB, unrelated CRM history, credentials, logs, audit payloads, or attachment bytes.

### C. AIService abstraction
Define a provider-agnostic contract:
- input DTO;
- structured output DTO;
- deterministic fake for tests;
- provider failure behavior;
- prompt-injection boundary;
- no execution/approval authority.

Do not select a concrete provider/model unless already explicitly approved elsewhere.

### D. Structured extraction semantics
For every candidate output distinguish:
- extracted fact;
- inference;
- proposal.

Determine which concepts map to existing:
- ExtractedFact
- Inference
- Proposal
- Question
- Commitment
- Task
- NextStep
- OperationalEvidenceLink / fact evidence

Identify any missing persistence concept only if genuinely required.

### E. Exact questions
Define how an exact question is stored and evidenced:
- verbatim/bounded quote or source span/reference;
- source message identity;
- whether question text itself is allowed in Question;
- how “open” vs “answered” is determined;
- no automatic answered transition without later source evidence/user confirmation.

### F. Commitments and next steps
Define:
- detected vs confirmed commitment;
- responsible party representation;
- due date certainty;
- proposed vs planned next step;
- how source evidence links are stored;
- what AI may create automatically vs what requires confirmation.

### G. Response-needed, risk, and priority
Determine whether these are:
- extracted facts,
- inferences,
- proposals,
- alerts,
or combinations.

Define allowed bounded values and provenance.

### H. Commercial context boundary
Determine what Phase 4 should do before CRM integration:
- candidate company/contact/work/opportunity/offer mentions only;
- confirmed IdentityLink reuse if already locally available;
- no silent CRM association from text similarity;
- whether actual CRM API lookup belongs in a later Phase 5.

Explicitly identify what is in scope now vs deferred.

### I. Reanalysis and correction
Define:
- what happens when source content changes;
- what happens when AI output differs on replay;
- whether old facts/inferences/proposals are superseded or new revisions are appended;
- how correction/history is preserved;
- how stale operational objects are prevented from silently disappearing.

### J. Transaction and failure model
Define:
- local transaction boundary for persisting one analysis;
- behavior if AI call fails before persistence;
- behavior if persistence fails after AI response;
- safe retry/idempotency;
- degraded state representation if needed.

### K. Testing strategy
Propose focused tests for:
- exact questions;
- facts vs inferences vs proposals;
- commitment ownership/dates;
- prompt injection treated as data;
- remote data minimization;
- AI failure;
- replay/idempotency;
- changed-thread reanalysis;
- no automatic external mutation;
- no credential/attachment leakage;
- deterministic fake AIService.

## Required analysis output

Create:
docs/plans/implementation-phase-4-analysis.md

The analysis must include:

1. Current-state inventory.
2. Gap analysis against the functional specification.
3. Proposed Phase 4 boundary.
4. Explicit in-scope / out-of-scope.
5. Proposed data flow.
6. Reuse of existing models/repositories.
7. Any required schema/model changes.
8. AIService contract options.
9. Idempotency/reanalysis options.
10. Security/data-minimization controls.
11. Test plan.
12. Recommended subphases small enough for Codex (prefer 2-4 tracked files per implementation task where practical).
13. A section titled **DECISIONS REQUIRED FROM USER**.

## STOP rule

If two or more reasonable designs exist for any business/data semantic, do not choose silently.

List alternatives with consequences and mark:
**STOPPED FOR DECISION**

Do not write implementation code.
Do not modify production files.
Do not run migrations.
Do not run the full test suite.
Do not create implementation tasks yet.

## Scope Lock

This Analyze Task may create/modify only:
- docs/plans/implementation-phase-4-analysis.md

No other tracked file may change.

## Git discipline

Do not inspect untracked files or caches.
Use only:
- git status --short --untracked-files=no
- git diff --name-only

Commit:
Analyze phase 4 email thread analysis

Push only origin/codex-work.
