# Phase 2A Implementation Review Task

**Estado:** Approved for Review
**Fecha:** 2026-09-21
**Baseline implementado:** `db9ae5bf4c6f753286b1fa053a48ac73c3c100d2`

## 1. Objetivo

Revisar en modo READ-ONLY la implementación de Fase 2A contra:

- `docs/plans/implementation-phase-2-analysis.md`
- `docs/plans/implementation-phase-2a-plan.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`

No modificar código.

## 2. Verificaciones obligatorias

Revisar especialmente:

1. cumplimiento exacto del Scope Lock;
2. que estén implementadas todas las entidades 2A y tablas de soporte/evidencia;
3. constraints físicos y repository guards exigidos;
4. source uniqueness nullable semantics;
5. observation history append-only;
6. retention/deleted-at-source semantics;
7. checkpoint uniqueness;
8. idempotency uniqueness;
9. one-to-one ManualNote/WhatsApp;
10. conversation membership uniqueness;
11. CRMReference sin copia de master-data;
12. CRMContextLink ambiguity/confirmation invariant;
13. IdentityLink active-confirmed uniqueness y correction/supersession history;
14. Fact/Inference/Proposal separation;
15. evidence/support link validation;
16. AuditEvent append-only and safe payload constraints;
17. repository coverage for all planned boundaries;
18. migration correctness from 0001 -> 0002 and downgrade behavior;
19. isolated SQLite tests and full pytest result;
20. absence of external calls, credentials, and Phase 2B entities.

## 3. Posibles hallazgos a confirmar/refutar

Revisar independientemente estos puntos:

- Revision `0002` usa `Base.metadata.create_all()` y `drop_all()` en vez de operaciones Alembic explícitas; evaluar riesgo de borrar tablas fuera de 2A y de que la migración deje de ser histórica/reproducible si cambian los modelos.
- El plan exige enums/check constraints/partial unique indexes; comprobar cuáles realmente existen.
- `SourceRecord` y `SourceObservation` usan UniqueConstraint simple con nullable columns; confirmar comportamiento SQLite y si cumple exactamente la semántica aprobada.
- No parece existir partial unique index para un único IdentityLink activo/confirmado.
- `CRMContextLink` parece asegurar solo confirmed_at cuando state=confirmed, pero no impedir estados no confirmados con confirmed_at.
- `InferenceSupport` y `ProposalSupport` parecen no tener FK polimórfica ni repository validation implementada.
- Solo existen `SourceRepository` y `AuditRepository`; comprobar ausencia de ProvenanceRepository y DerivationRepository respecto al plan.
- `mark_retention()` muta SourceRecord directamente y no parece generar historia/audit por sí mismo; evaluar contra modelo aprobado.
- Los tests parecen cubrir solo una pequeña parte de los casos obligatorios (checkpoint, CRM context, identity correction, evidence/support, negative CRM master fields, unsafe audit fields, migration table set/constraints, etc.).
- El fixture de tests usa `Base.metadata.create_all()`, lo que podría ocultar defectos de la migración Alembic.

No asumir estos hallazgos: verificarlos y clasificarlos.

## 4. Salida requerida

Crear únicamente:

`docs/plans/implementation-phase-2a-review.md`

Formato:

- Status: ACCEPT / CHANGES REQUIRED
- Scope Lock: PASS / FAIL
- Test result exacto
- Findings:
  - Critical
  - Major
  - Minor
  - Observation
- Coverage of required invariants
- Required corrections
- Final verdict

# SCOPE LOCK

## IN SCOPE

- revisión READ-ONLY;
- crear únicamente `docs/plans/implementation-phase-2a-review.md`.

## OUT OF SCOPE

- modificar código;
- modificar tests;
- instalar dependencias;
- ejecutar cambios sobre bases de usuario;
- integraciones;
- tocar `main`;
- corregir hallazgos.

## Completion

Ejecutar:

`python -m pytest`

Commit:

`Review implementation phase 2A`

Push únicamente a `origin/codex-work`.
