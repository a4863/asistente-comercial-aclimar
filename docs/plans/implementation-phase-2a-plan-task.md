# Implementation Phase 2A Plan Task

**Estado:** Approved for planning
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

## 1. Objetivo

Crear el plan de implementación ejecutable para la Fase 2A del Asistente Comercial ACLIMAR.

Fase 2A implementa exclusivamente el backbone persistente assistant-owned de:

- fuentes;
- observaciones;
- conversaciones;
- notas/WhatsApp manual;
- Calendar representation;
- actividades;
- referencias CRM;
- identidad/correcciones;
- hechos/inferencias/propuestas;
- auditoría;
- checkpoints;
- idempotencia.

No escribir código todavía.

## 2. Documentación obligatoria

Leer:

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/plans/implementation-phase-2-analysis.md`
- `docs/plans/templates/implementation-plan.md`

## 3. Entidades exactas autorizadas

El plan debe cubrir solo:

- `ConfigurationReference`
- `SourceRecord`
- `SourceObservation`
- `Conversation`
- `ConversationMembership`
- `ManualNote`
- `WhatsAppImport`
- `CalendarEventRepresentation`
- `Activity`
- `ActivitySourceLink`
- `CRMReference`
- `CRMContextLink`
- `IdentityLink`
- `IdentityLinkCorrection`
- `ExtractedFact`
- `Inference`
- `Proposal`
- `AuditEvent`
- `SynchronizationCheckpoint`
- `IdempotencyIdentity`
- association/support/evidence tables strictly required by the above.

No Phase 2B entity may appear.

## 4. Files expected by analysis

The plan must use, unless it proves a STOP-worthy omission:

### Modify

- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/env.py` only if necessary
- `test/test_migrations.py`
- `test/conftest.py`

### Create

- `alembic/versions/0002_phase_2a_persistent_foundation.py`
- `test/test_persistence_models.py`
- `test/test_persistence_repositories.py`

No other file is authorized without STOP.

## 5. Plan requirements

The plan must define:

1. baseline commit;
2. exact SQLAlchemy table/model set;
3. exact association/support tables;
4. keys and uniqueness constraints;
5. nullable/non-null semantics;
6. retention/deleted-at-source representation;
7. correction/supersession semantics;
8. append-only audit repository behavior;
9. checkpoint uniqueness;
10. idempotency uniqueness;
11. CRM reference minimal fields;
12. ambiguity/confirmation fields;
13. migration steps;
14. repository methods;
15. exact tests;
16. negative tests;
17. commands;
18. rollback;
19. STOP conditions;
20. Definition of Done.

## 6. Mandatory invariants

- CRM references do not become CRM master copies.
- facts/inferences/proposals remain separate physical types.
- identity correction never deletes prior confirmed links.
- observations/audit/corrections are history-preserving.
- audit has no generic update/delete repository method.
- one source cannot belong to more than one conversation.
- manual note and WhatsApp original text is preserved.
- stable external source identity is unique within source-system scope when present.
- idempotency unique by operation_kind + scope + key.
- checkpoint unique per source-system scope.
- no credentials/secrets in any model.
- no external calls.

## 7. Testing expectations

At minimum include tests for:

- migration 0001 -> 0002;
- downgrade/upgrade smoke on isolated SQLite;
- source uniqueness and manual local identity;
- append-only observations;
- deleted-at-source history;
- checkpoint persistence;
- idempotency duplicate rejection;
- one-to-one ManualNote/WhatsApp source relationship;
- conversation membership uniqueness;
- CRMReference without authoritative master-data duplication;
- ambiguous CRMContextLink not confirmed;
- identity correction supersession;
- fact/inference/proposal physical separation;
- evidence/support links;
- append-only audit repository;
- no network/external systems;
- no user DB usage.

# SCOPE LOCK

## IN SCOPE

- Create only `docs/plans/implementation-phase-2a-plan.md`.

## OUT OF SCOPE

- code;
- tests;
- migration execution;
- dependencies;
- external integrations;
- Phase 2B entities;
- application/domain service layer;
- business UI;
- changes to approved documentation;
- changes to `main`.

## RESTRICTIONS

- no implementation;
- no external calls;
- no credentials;
- no new dependencies;
- STOP on material ambiguity;
- commit/push only to `codex-work`.

## 8. Completion protocol

1. create only `docs/plans/implementation-phase-2a-plan.md`;
2. commit:
   `Plan implementation phase 2A`
3. push to `origin/codex-work`;
4. do not merge to `main`.
