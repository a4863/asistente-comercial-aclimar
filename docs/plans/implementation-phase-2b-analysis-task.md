# Phase 2B Analysis Task — Operational Entities

**Estado:** Approved for Analyze
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Objetivo

Analizar la implementación de Fase 2B para las entidades operativas del asistente comercial, sin escribir código de producto.

Entidades 2B previstas:

- Task
- Commitment
- Question
- NextStep
- Alert
- FollowUpPreference / override history
- ActionProposal
- ApprovalDecision
- ExecutionResult

## 2. Fuentes autoritativas

Revisar:

- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/plans/implementation-phase-2-analysis.md`
- `docs/plans/implementation-phase-2a-plan.md`
- implementación actual de 2A en:
  - `app/persistence/models.py`
  - `app/persistence/repositories.py`
  - `alembic/versions/0002_phase_2a_persistent_foundation.py`

## 3. Reglas funcionales a preservar

### Task
Lifecycle:
`proposed -> pending -> completed | cancelled`

### Commitment
Lifecycle:
`detected -> confirmed -> fulfilled | overdue | cancelled`

Puede pasar automáticamente a overdue cuando vence la fecha, pero no a fulfilled salvo evidencia explícita posterior o confirmación del usuario.

### Question
Lifecycle:
`detected -> open -> answered | dismissed`

No marcar answered automáticamente salvo evidencia explícita posterior o confirmación del usuario.

### NextStep
Lifecycle:
`proposed -> planned -> completed | cancelled`

### ActionProposal
Lifecycle:
`pending_approval -> approved | rejected -> executed | error`

Toda mutación externa debe seguir:
proposal -> explicit approval -> revalidation -> execution -> audit.

### Alerts
Deben representar condiciones derivadas, no sustituir facts/inferences/tasks.

### Follow-up preferences
Defaults:
- new/qualified opportunity: 7 días
- sent offer: 5 días
- homologation/docs: 7 días
- negotiation/review: 5 días

Overrides precedence:
opportunity/offer/work -> company/contact -> global.

Una fecha futura explícita prevalece sobre inactividad.

## 4. Alcance del análisis

Determinar:

1. entidades/tablas exactas de 2B;
2. campos mínimos por entidad;
3. FKs hacia entidades 2A;
4. estados permitidos y checks físicos;
5. transiciones válidas e inválidas;
6. qué transiciones pueden ser automáticas;
7. qué transiciones requieren confirmación/evidencia;
8. reglas temporales para due dates/overdue;
9. modelo de FollowUpPreference y su historial/overrides;
10. relación ActionProposal -> ApprovalDecision -> ExecutionResult;
11. idempotencia necesaria;
12. append-only vs mutable current state;
13. repository boundaries exactos;
14. audit requirements;
15. migration `0003`;
16. tests obligatorios;
17. Scope Lock exacto de archivos.

## 5. Prohibiciones

READ-ONLY salvo el artefacto de análisis.

No:

- modificar código existente;
- modificar documentación aprobada;
- crear migraciones;
- cambiar dependencias;
- tocar main;
- implementar IMAP/Calendar/CRM/AI;
- escribir fuera del archivo de salida.

Si aparece una ambigüedad funcional material con dos interpretaciones razonables: **STOP** y documentar la decisión pendiente.

## 6. Salida obligatoria

Crear únicamente:

`docs/plans/implementation-phase-2b-analysis.md`

Debe incluir:

- Status: READY FOR APPROVAL o STOPPED FOR DECISION;
- entity matrix;
- state-transition matrix;
- repository proposal;
- migration proposal;
- test matrix;
- exact file Scope Lock;
- ambiguities/decisions needed;
- implementation risks.

## 7. Completion protocol

Commit:

`Analyze implementation phase 2B`

Push solo a `origin/codex-work`.

No tocar `main`.
