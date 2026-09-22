# Phase 2A Correction 1B Task — Physical Constraints and Model Tests

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`
**Validated migration commit:** `57d2805e9f35c28c2d39856fb51a07a5d3da291c`

## 1. Objetivo

Corregir únicamente las restricciones físicas/invariantes del modelo 2A y sus tests de modelo.

No tocar repositorios, fixtures generales ni otras capas.

## 2. Archivos autorizados

Solo:

```text
app/persistence/models.py
alembic/versions/0002_phase_2a_persistent_foundation.py
test/test_persistence_models.py
```

No modificar ningún otro archivo.

## 3. Correcciones obligatorias

### A. CRMContextLink

Debe cumplir físicamente:

- `confirmation_state = 'confirmed'` => `confirmed_at IS NOT NULL`;
- `confirmation_state != 'confirmed'` => `confirmed_at IS NULL`.

Estados permitidos:
- `ambiguous`
- `proposed`
- `confirmed`

Añadir check constraint para valores permitidos.

### B. IdentityLink

Debe permitir como máximo una fila activa/confirmada por:

`identity_type + identity_value`

Definición de activa/confirmada para esta fase:

- `status = 'confirmed'`
- `superseded_at IS NULL`

Usar índice único parcial SQLite compatible, reflejado tanto en models.py como en migration 0002.

Estados permitidos para `status` deben quedar físicamente restringidos a los aprobados por el modelo actual. Si el plan/documentación no define una lista cerrada inequívoca, STOP en lugar de inventarla.

### C. IdentityLinkCorrection

Añadir constraint:

`prior_identity_link_id != replacement_identity_link_id`

Mantener prior único.

### D. Support types

Añadir checks físicos:

- `InferenceSupport.support_type`: solo tipos actualmente autorizados por el plan 2A.
- `ProposalSupport.support_type`: solo tipos actualmente autorizados por el plan 2A.

Según el plan:
- InferenceSupport: `source`, `fact`, `inference`
- ProposalSupport: `source`, `fact`, `inference`, `proposal`

No introducir nuevas categorías.

### E. Source external identity

Mantener unicidad por:

`source_system_scope + stable_external_id`

con múltiples NULL permitidos para manual sources.

Si el UniqueConstraint actual en SQLite ya satisface exactamente esta semántica, puede mantenerse; añadir test explícito para demostrarlo.

### F. SourceObservation version marker

Mantener:

`source_record_id + source_version_marker`

único cuando marker no sea NULL; múltiples NULL permitidos.

Añadir test explícito.

## 4. Tests obligatorios

En `test/test_persistence_models.py` cubrir al menos:

1. dos SourceRecord manuales con `stable_external_id = NULL` son válidos;
2. duplicado scope + external id no-NULL falla;
3. dos SourceObservation con marker NULL son válidos;
4. duplicado marker no-NULL para mismo source falla;
5. CRMContextLink:
   - confirmed + timestamp válido;
   - confirmed sin timestamp falla;
   - ambiguous/proposed con timestamp falla;
   - estado fuera de lista falla;
6. IdentityLink partial unique:
   - una activa confirmed válida;
   - segunda activa confirmed misma identidad falla;
   - una superseded permite nueva activa;
7. IdentityLinkCorrection prior == replacement falla;
8. InferenceSupport support_type inválido falla;
9. ProposalSupport support_type inválido falla.

Usar solo SQLite aislado existente. No tocar repositorios.

## 5. Validación

Ejecutar:

`python -m pytest test/test_persistence_models.py test/test_migrations.py`

Debe quedar verde.

## 6. STOP conditions

STOP si:

- necesitas modificar repositories.py;
- necesitas modificar conftest.py;
- necesitas crear archivos nuevos;
- necesitas una decisión funcional no resuelta;
- necesitas nueva dependencia;
- necesitas cambiar entidades fuera de 2A.

## 7. Completion protocol

Commit:

`Fix phase 2A physical constraints`

Push a `origin/codex-work`.

No tocar `main`.
