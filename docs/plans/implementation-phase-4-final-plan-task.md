# Phase 4 Final Planning Task — Email/Thread Analysis

**Status:** Approved for planning only
**Date:** 2026-09-23
**Prerequisites:**
- docs/plans/implementation-phase-4-analysis.md
- docs/plans/implementation-phase-4-decisions.md
- Phase 3D3 ACCEPTED

## Objective

Create a deterministic implementation plan for Phase 4 using the approved D1-D9 decisions.

Do not implement code.

The plan must preserve:
- source -> extraction -> inference -> proposal;
- append-only analysis history;
- bounded remote disclosure;
- AI provider independence;
- no external execution authority;
- no live CRM lookup in Phase 4;
- no silent lifecycle closure;
- retryable/stale analysis-run behavior.

## Required design work

### 1. Phase decomposition
Split implementation into small independently reviewable subphases.

Prefer 2-4 tracked files per implementation task where practical.

The plan should strongly consider separating:
- analysis-run/evidence persistence model;
- pure input selection/minimization + DTO contracts;
- repository idempotency/supersession primitives;
- orchestration with fake AIService;
- final synthetic acceptance/security tests.

Do not bundle the full phase into one large task.

### 2. AnalysisRun/data model
Define the exact required schema for:
- analysis run identity;
- analysis input digest;
- policy/contract version;
- status lifecycle;
- stale/retryable/failure metadata;
- links to conversation/source scope;
- append-only versioning/supersession;
- source-local evidence span/reference;
- commitment responsibility/date certainty if schema changes are needed.

Reuse existing models when sufficient.
Add new entities/columns only when necessary.

### 3. Input-selection contract
Define deterministic selection rules from approved D7:
- current/new-or-changed message;
- up to 6 prior messages;
- max 30,000 chars;
- current message prioritized;
- then most recent previous context;
- bounded metadata allowlist;
- attachment bytes always excluded;
- credentials/logs/audit/unrelated context excluded.

The plan must specify how selection is canonicalized so the input digest is deterministic.

### 4. AIService contract
Define provider-neutral typed input/output DTOs.

Output must distinguish:
- extracted facts;
- inferences;
- proposals;
- exact questions;
- commitments;
- tasks;
- next steps;
- response_needed;
- commercial_risk;
- priority;
- candidate context mentions.

Use a deterministic fake for tests.

Do not select a concrete AI provider/model.

### 5. Evidence
Define exact source-local evidence representation for questions and other candidates:
- source_record_id;
- bounded span/reference;
- validation against selected source text;
- quoted-history distinction.

Ensure no raw mailbox/body duplication beyond what is already permitted by the approved model.

### 6. Operational mapping
Define deterministic mapping:
- Question -> detected;
- Commitment -> detected/confirmed per D4;
- Task -> proposed;
- NextStep -> proposed.

Define how ExtractedFact/Inference/Proposal support those operational objects.

Define bounded values for:
- response_needed;
- commercial_risk;
- priority.

Do not create Alert directly from AI output.

### 7. Reanalysis/supersession
Define:
- exact replay no-op;
- manual reanalysis/versioning;
- body change with unchanged thread topology;
- thread merge/split/repartition effects;
- supersession of derivations;
- preservation of stale/open operational history;
- prevention of silent completion/cancellation.

### 8. Transaction/failure model
Define exact orchestration:
1. build/canonicalize input;
2. persist/run reservation if applicable;
3. provider call outside long write transaction;
4. revalidate input identity;
5. atomically persist derivations and operational objects;
6. mark completed.

Provider failure, stale input, validation failure, and persistence failure must have bounded states and no partial derived records.

### 9. CRM boundary
Plan must explicitly keep live CRM API reads/writes out of Phase 4.

Only confirmed local IdentityLink / already-confirmed local CRM context may be reused.

### 10. Test plan
Include focused tests for:
- deterministic input digest;
- 6-prior/30k truncation;
- no attachment/credential/log leakage;
- exact question evidence;
- quoted old question vs new question;
- fact/inference/proposal distinction;
- commitments responsibility/date certainty;
- bounded response/risk/priority;
- replay idempotency;
- manual reanalysis;
- changed content;
- thread repartition;
- stale-before-commit;
- provider failure;
- persistence rollback;
- prompt injection treated as data;
- no external mutation;
- no live CRM call;
- fake AIService determinism.

## Required output

Create only:

docs/plans/implementation-phase-4-plan.md

The plan must include:
1. final architecture/data-flow for Phase 4;
2. exact schema/model changes;
3. exact repository/service contracts;
4. exact subphase order;
5. Scope Lock for each subphase;
6. migrations required and downgrade behavior;
7. test commands per subphase;
8. final acceptance criteria;
9. risks;
10. any remaining ambiguity.

If any new ambiguity remains that requires a business/data semantic decision:
**STOPPED FOR DECISION**

Do not invent around it.

## Scope Lock

This planning task may create/modify only:
- docs/plans/implementation-phase-4-plan.md

No implementation code.
No migrations.
No tests.
No production file changes.

## Git discipline

Do not inspect caches or untracked files.

Use only:
- git status --short --untracked-files=no
- git diff --name-only

Commit:
Plan phase 4 email thread analysis

Push only origin/codex-work.
