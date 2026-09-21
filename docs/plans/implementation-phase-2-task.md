# Implementation Phase 2 Analysis Task

**Estado:** Approved for Analyze
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

## 1. Objetivo

Analizar la Fase 2 de implementación del Asistente Comercial ACLIMAR.

La Fase 1 foundation se considera cerrada sobre el baseline actual de `codex-work`.

La Fase 2 debe centrarse en implementar el **núcleo persistente assistant-owned** definido en `docs/data-model.md`, sin conectar todavía IMAP, Google Calendar, CRM, AI, keyring real ni APScheduler.

No escribir código en esta tarea.

## 2. Documentación obligatoria

Leer:

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/plans/implementation-phase-1-plan.md`
- `docs/plans/implementation-phase-1-final-review.md`

## 3. Objetivo funcional de Fase 2

Evaluar un incremento que implemente únicamente entidades assistant-owned y sus invariantes internas, priorizando:

- SourceRecord;
- SourceObservation / sync observation;
- Conversation;
- Activity;
- ManualNote;
- WhatsAppImport;
- CalendarEventRepresentation;
- CRMReference / CRMContextLink;
- IdentityLink / IdentityCorrection;
- ExtractedFact;
- Inference;
- Proposal;
- Task;
- Commitment;
- Question;
- NextStep;
- Alert;
- FollowUpPreference / override;
- ActionProposal;
- ApprovalDecision;
- ExecutionResult;
- AuditEvent;
- ConfigurationReference;
- synchronization checkpoints / idempotency identities.

El análisis debe decidir si todo lo anterior cabe con seguridad en una sola Fase 2 o si debe dividirse en 2A / 2B.

## 4. Reglas que deben quedar preservadas

- CRM master data no se copia como autoridad.
- hechos, inferencias y propuestas son tipos separados.
- correcciones/supersession preservan historia.
- audit append-only.
- deleted-at-source preserva trazabilidad.
- task lifecycle:
  `proposed -> pending -> completed | cancelled`
- commitment:
  `detected -> confirmed -> fulfilled | overdue | cancelled`
- question:
  `detected -> open -> answered | dismissed`
- next step:
  `proposed -> planned -> completed | cancelled`
- action proposal:
  `pending_approval -> approved | rejected -> executed | error`
- idempotency must be explicit.
- no external mutation or integration.
- no CRM DB access.
- no AI provider.
- no real credentials.

## 5. Required analysis

Define:

1. exact entity split for this phase;
2. SQLAlchemy models;
3. repository boundaries;
4. Alembic migration scope;
5. integrity constraints;
6. enum/state handling;
7. append-only audit mechanics;
8. correction/supersession representation;
9. idempotency identity strategy;
10. checkpoint persistence;
11. deletion/redaction representation;
12. tests required;
13. exact files to create/modify;
14. whether the phase should be one task or split;
15. STOP conditions.

## 6. Testing expectations

At minimum analyze tests for:

- lifecycle valid/invalid transitions;
- facts/inferences/proposals separation;
- immutable/auditable history;
- identity correction history;
- source dedup/idempotency;
- checkpoint persistence;
- deleted-at-source;
- approval decision uniqueness;
- execution result linkage;
- no direct CRM entities as master copies;
- SQLite migration from Phase 1 baseline;
- repository isolation.

## 7. Required output

Create only:

`docs/plans/implementation-phase-2-analysis.md`

End with:

- `READY FOR APPROVAL` if precise enough to plan safely; or
- `BLOCKED` with exact unresolved decisions.

If READY, propose a precise Scope Lock and state whether Fase 2 should be single-step or split into 2A/2B.

# SCOPE LOCK

## IN SCOPE

- Analyze Phase 2 persistent domain foundation.
- Create only `docs/plans/implementation-phase-2-analysis.md`.

## OUT OF SCOPE

- code;
- tests;
- migrations execution;
- dependency installation;
- IMAP;
- Calendar;
- CRM API;
- AI;
- keyring;
- APScheduler;
- Windows Task Scheduler;
- business UI;
- external mutations;
- changes to approved documentation;
- changes to `main`.

## RESTRICTIONS

- no implementation;
- no external calls;
- no credentials;
- STOP on material ambiguity;
- commit/push only to `codex-work`.

## 8. Completion protocol

1. create only `docs/plans/implementation-phase-2-analysis.md`;
2. commit:
   `Analyze implementation phase 2`
3. push to `origin/codex-work`;
4. do not merge to `main`.
