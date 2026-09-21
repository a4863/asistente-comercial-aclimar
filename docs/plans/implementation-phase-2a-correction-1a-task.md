# Phase 2A Correction 1A Task — Explicit Alembic Migration Only

**Estado:** Approved for Implement
**Fecha:** 2026-09-21
**Baseline:** current `codex-work`

## 1. Objetivo

Corregir únicamente el problema de que la revisión Alembic `0002` usa `Base.metadata.create_all()` / `drop_all()`.

No corregir todavía constraints de modelos, repositorios ni cobertura general.

## 2. Cambio autorizado

Modificar únicamente:

`alembic/versions/0002_phase_2a_persistent_foundation.py`

La revisión debe:

- eliminar cualquier uso/import de `Base.metadata.create_all()` y `drop_all()`;
- crear explícitamente con `op.create_table`, `op.create_index` y constraints Alembic todos los objetos 2A que actualmente existen en `app/persistence/models.py`;
- mantener revision = `0002` y down_revision = `0001`;
- hacer downgrade explícito en orden inverso;
- eliminar únicamente objetos creados por 0002;
- no depender de futuros cambios en `models.py`;
- no importar `Base` ni los modelos de aplicación.

El objetivo de este bloque es hacer la migración histórica y acotada, reflejando el estado físico ACTUAL de los modelos. Las mejoras adicionales de constraints se harán en una tarea posterior.

## 3. Archivos autorizados

Solo:

`alembic/versions/0002_phase_2a_persistent_foundation.py`

No modificar ningún otro archivo.

## 4. Validación

Ejecutar únicamente:

`python -m pytest test/test_migrations.py`

Si el test existente falla por una expectativa que requiere modificar tests, **STOP**. No tocar tests en esta tarea.

## 5. STOP conditions

STOP si:

- necesitas modificar models.py;
- necesitas modificar tests;
- necesitas tocar repositories.py;
- necesitas nueva dependencia;
- necesitas cambiar el esquema funcional respecto al estado actual;
- aparece una ambigüedad material sobre qué tabla/columna existe actualmente.

## 6. Completion protocol

Commit:

`Make phase 2A migration explicit`

Push a `origin/codex-work`.

No tocar `main`.
