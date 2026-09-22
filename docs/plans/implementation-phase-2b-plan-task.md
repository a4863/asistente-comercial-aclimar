# Phase 2B Plan Task — Operational Entities

**Estado:** Approved for Plan
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Objetivo

Preparar el plan de implementación de Fase 2B usando como base:

- `docs/plans/implementation-phase-2b-analysis.md`
- `docs/plans/implementation-phase-2b-decisions.md`
- documentación funcional y técnica aprobada.

No implementar código.

## 2. Decisiones ya cerradas

- Follow-up mapping: CRM primero; clasificación manual solo como fallback.
- Overdue: evaluación periódica; 2B implementa la operación evaluadora, no el scheduler.
- Alert lifecycle: `active -> resolved | dismissed` con deduplicación por condición y nueva alerta tras recurrencia.

No reabrir estas decisiones.

## 3. El plan debe definir

1. tablas exactas de 2B;
2. campos y FKs;
3. constraints/checks físicos;
4. lifecycle guards;
5. qué registros son current-state vs append-only history;
6. evidencia/confirmación requerida para completar/fulfill/answer;
7. operación de overdue evaluable con reloj inyectable/controlado;
8. modelo exacto de FollowUpPreference + history + precedence;
9. Alert dedup/resolution semantics;
10. ActionProposal -> ApprovalDecision -> ExecutionResult;
11. idempotency;
12. repositories y métodos explícitos;
13. migration `0003`;
14. tests obligatorios;
15. Scope Lock exacto de archivos;
16. orden de implementación por bloques para reducir riesgo.

## 4. Requisitos de diseño

- no CRUD genérico;
- no ejecución externa;
- no network;
- no scheduler real todavía;
- no UI;
- no rutas;
- no dependencias nuevas;
- no tocar `main`;
- toda mutación externa sigue proposal -> explicit approval -> revalidation -> execution -> audit;
- facts/inferences/proposals siguen separados;
- history/approval/execution records append-only.

## 5. Salida

Crear únicamente:

`docs/plans/implementation-phase-2b-plan.md`

Debe incluir:

- Status READY FOR APPROVAL;
- Scope Lock;
- entity/table plan;
- transition rules;
- repository plan;
- migration plan;
- test plan;
- implementation sequence;
- STOP conditions;
- Definition of Done.

## 6. Completion protocol

Commit:

`Plan implementation phase 2B`

Push solo a `origin/codex-work`.

No tocar `main`.
