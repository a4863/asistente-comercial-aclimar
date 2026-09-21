# Phase 2A Correction 1 Task — Migration and Physical Constraints

**Estado:** Approved for Implement
**Fecha:** 2026-09-21
**Baseline:** current `codex-work`
**Review:** `docs/plans/implementation-phase-2a-review.md`

## 1. Objetivo

Corregir exclusivamente la migración Alembic 0002 y las restricciones físicas del modelo 2A.

No implementar todavía ProvenanceRepository, DerivationRepository ni ampliar tests de repositorios salvo lo estrictamente necesario para validar esta corrección.

## 2. Correcciones obligatorias

### A. Reescribir migración 0002

En `alembic/versions/0002_phase_2a_persistent_foundation.py`:

- eliminar uso de `Base.metadata.create_all()` y `drop_all()`;
- usar operaciones Alembic explícitas;
- crear únicamente tablas/índices/constraints de Fase 2A;
- downgrade solo de objetos 2A;
- no depender de futuros cambios en `models.py`.

### B. Constraints físicos

Alinear `app/persistence/models.py` y migración con estas invariantes:

- `SourceRecord`: identidad estable única por `source_system_scope + stable_external_id` cuando external id no sea NULL;
- `ConversationMembership.source_record_id`: unique;
- `ManualNote.source_record_id`: unique;
- `WhatsAppImport.source_record_id`: unique;
- `SynchronizationCheckpoint.source_system_scope`: unique;
- `IdempotencyIdentity(operation_kind, scope, identity_key)`: unique;
- `CRMContextLink`:
  - confirmed => confirmed_at NOT NULL;
  - non-confirmed => confirmed_at IS NULL;
- `IdentityLink`: solo una identidad activa/confirmada por `identity_type + identity_value`;
- `IdentityLinkCorrection.prior_identity_link_id`: unique;
- correction prior != replacement;
- support/evidence type columns con constraints/checks para los valores autorizados;
- no campos de credenciales ni payload arbitrario en AuditEvent.

Si una restricción no puede expresarse de forma fiable en SQLite, usar el mecanismo físico más cercano aprobado y dejar la guarda de repositorio para Correction 2. No ampliar alcance.

## 3. Archivos autorizados

Solo:

```text
app/persistence/models.py
alembic/versions/0002_phase_2a_persistent_foundation.py
test/test_migrations.py
test/test_persistence_models.py
```

No modificar ningún otro archivo.

## 4. Tests obligatorios

Añadir o ajustar pruebas únicamente para:

- upgrade 0001 -> 0002;
- downgrade 0002 -> 0001;
- re-upgrade;
- expected 2A table set;
- expected key constraints/indexes;
- CRMContextLink confirmation check;
- IdentityLink active-confirmed uniqueness;
- IdentityLinkCorrection prior != replacement;
- nullable external-id semantics;
- support-type check constraints.

Ejecutar:

`python -m pytest test/test_migrations.py test/test_persistence_models.py`

La ejecución debe quedar verde.

## 5. STOP conditions

STOP si:

- necesitas tocar repositories.py;
- necesitas crear otro archivo;
- necesitas nueva dependencia;
- necesitas una entidad fuera de 2A;
- una invariantes exige una decisión funcional no contenida en docs/plan.

## 6. Completion protocol

Commit:

`Fix phase 2A migration and constraints`

Push solo a `origin/codex-work`.

No tocar `main`.
