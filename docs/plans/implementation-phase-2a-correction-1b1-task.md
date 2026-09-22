# Phase 2A Correction 1B1 Task — Context and Support Constraints

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Objetivo

Corregir únicamente:

1. constraints físicos de `CRMContextLink`;
2. constraints físicos de `InferenceSupport.support_type`;
3. constraints físicos de `ProposalSupport.support_type`;
4. tests asociados.

No tocar IdentityLink ni IdentityLinkCorrection en esta tarea.

## 2. Archivos autorizados

Solo:

```text
app/persistence/models.py
alembic/versions/0002_phase_2a_persistent_foundation.py
test/test_persistence_models.py
```

## 3. CRMContextLink

Estados permitidos:

- ambiguous
- proposed
- confirmed

Invariantes físicas:

- confirmed => confirmed_at IS NOT NULL
- ambiguous/proposed => confirmed_at IS NULL
- cualquier otro confirmation_state => rechazo

Añadir los mismos checks tanto en SQLAlchemy model como en migration 0002.

## 4. Support types

InferenceSupport.support_type solo puede ser:

- source
- fact
- inference

ProposalSupport.support_type solo puede ser:

- source
- fact
- inference
- proposal

Añadir checks físicos en model y migration 0002.

## 5. Tests

Añadir/ajustar solo tests para:

- CRMContextLink confirmed + timestamp => válido
- confirmed sin timestamp => falla
- ambiguous con timestamp => falla
- proposed con timestamp => falla
- confirmation_state desconocido => falla
- InferenceSupport tipo inválido => falla
- ProposalSupport tipo inválido => falla

No ampliar a IdentityLink.

## 6. Validación

Ejecutar:

`python -m pytest test/test_persistence_models.py test/test_migrations.py`

Debe quedar verde.

## 7. STOP

STOP si necesitas:

- repositories.py;
- conftest.py;
- archivos nuevos;
- una nueva dependencia;
- cambiar otra entidad fuera de las tres indicadas.

## 8. Completion protocol

Commit:

`Fix phase 2A context and support constraints`

Push a `origin/codex-work`.

No tocar `main`.
