# Phase 2A Focused Correction Task

**Estado:** Approved for Implement
**Fecha:** 2026-09-21
**Baseline:** `b12354916459e1ded329f443be4401cd57a3e422`
**Review:** `docs/plans/implementation-phase-2a-review.md`

## 1. Objetivo

Corregir exclusivamente los hallazgos Major/Minor de la revisión de Fase 2A.

No añadir nuevas entidades fuera de 2A, no introducir integraciones y no ampliar el modelo funcional.

---

## 2. Correcciones obligatorias

### A. Migración Alembic histórica y acotada

Reemplazar `Base.metadata.create_all()` / `drop_all()` en revisión `0002` por operaciones Alembic explícitas.

Debe:

- crear únicamente las tablas 2A;
- declarar explícitamente PK, FK, unique constraints, check constraints e índices necesarios;
- crear índices parciales SQLite donde el plan los requiera;
- hacer downgrade solo de objetos 2A, en orden inverso de dependencias;
- ser reproducible aunque `models.py` cambie en el futuro;
- no importar ni usar `Base.metadata.create_all/drop_all` para upgrade/downgrade.

### B. Invariantes físicas faltantes

Asegurar al menos:

- Source scoped stable external identity con semántica correcta para NULL;
- ConversationMembership: un source solo puede pertenecer a una conversation;
- ManualNote y WhatsAppImport 1:1 con SourceRecord;
- SynchronizationCheckpoint único por `source_system_scope`;
- IdempotencyIdentity único por `operation_kind + scope + identity_key`;
- CRMContextLink:
  - `confirmed` exige `confirmed_at`;
  - estados no-confirmed no pueden tener `confirmed_at`;
- IdentityLink:
  - una única identidad activa/confirmada por `identity_type + identity_value`;
  - superseded links dejan de contar como activos;
- IdentityLinkCorrection:
  - prior link corregido como máximo una vez;
  - prior y replacement no pueden ser el mismo link;
- soporte/evidencia con tipos permitidos;
- AuditEvent sin payload arbitrario ni campos de secretos.

Si alguna de estas restricciones no puede expresarse físicamente en SQLite, implementar repository guard + test explícito y documentar la limitación en código mínimo, sin cambiar docs aprobados.

### C. Repository boundaries completos

Implementar los repositorios previstos en el plan:

- `SourceRepository`
- `ProvenanceRepository`
- `DerivationRepository`
- `AuditRepository`

Como mínimo incluir:

#### SourceRepository
- get/create source scoped;
- append observation;
- transition retention preserving history;
- checkpoint get/upsert seguro;
- idempotency reserve/get.

#### ProvenanceRepository
- conversation + membership;
- manual note / WhatsApp source record linkage;
- activity/source links;
- CRM references/context links;
- identity link create/confirm;
- identity correction append + prior supersession.

#### DerivationRepository
- append fact + evidence;
- append inference + typed supports;
- append proposal + typed supports;
- reject unsupported support types;
- reject cross-type conversion semantics.

#### AuditRepository
- append/list only;
- no update/delete;
- reject unsafe/unapproved fields.

No generic unrestricted CRUD.

### D. Append-only / history semantics

- SourceObservation insert-only.
- IdentityLinkCorrection insert-only.
- AuditEvent insert-only.
- Retention transition must preserve prior evidence and create traceable history through observation and/or audit behavior consistent with plan.
- No repository delete/update path for these historical records.
- Original text in ManualNote/WhatsApp must not be mutable through repository API.

### E. Test isolation on Windows

Repair the residual `test/tmp*` issue.

Requirements:

- no stale inaccessible temp folders break future collection;
- tests use a deterministic controlled temp root;
- engines/sessions are always disposed before cleanup;
- no SQLite handle remains open;
- test suite can be rerun consecutively without manual cleanup.

Do not solve by ignoring arbitrary directories or weakening pytest discovery unless fully justified and scoped.

### F. Test coverage completa

Add/complete tests for:

- migration 0001 -> 0002;
- downgrade 0002 -> 0001;
- re-upgrade;
- expected 2A table set;
- key constraints/indexes;
- checkpoint uniqueness;
- idempotency uniqueness;
- CRMContextLink valid/invalid confirmation states;
- IdentityLink active-confirmed uniqueness;
- IdentityLinkCorrection supersession/history;
- Fact evidence;
- Inference support valid/invalid types;
- Proposal support valid/invalid types;
- CRMReference minimal-fields boundary;
- rejection of master-data-style unexpected inputs;
- Audit unsafe fields;
- append-only repository shape;
- retention history;
- ManualNote/WhatsApp immutability via repositories;
- conversation uniqueness;
- no external calls/user DB;
- rerunnable Windows temp isolation.

---

## 3. Archivos autorizados

Solo pueden modificarse estos ocho archivos/rutas:

```text
app/persistence/models.py
app/persistence/repositories.py
alembic/env.py
alembic/versions/0002_phase_2a_persistent_foundation.py
test/conftest.py
test/test_migrations.py
test/test_persistence_models.py
test/test_persistence_repositories.py
```

No crear archivos adicionales.

Si una corrección material requiere otro archivo: **STOP**.

---

## 4. Prohibiciones

- no Phase 2B;
- no nuevas entidades funcionales;
- no IMAP/SMTP;
- no Google Calendar API;
- no CRM API ni `crm.db`;
- no AI;
- no keyring;
- no APScheduler;
- no UI/routes;
- no nuevas dependencias;
- no cambios en docs aprobados;
- no `main`;
- no credenciales;
- no datos reales;
- no network.

---

## 5. Ejecución obligatoria

Después de implementar:

1. ejecutar `python -m pytest`;
2. ejecutar la suite una segunda vez consecutiva;
3. ambas deben pasar;
4. inspeccionar que no quedan `test/tmp*` residuales creados por esta ejecución;
5. verificar diff completo;
6. confirmar que solo cambian los ocho archivos autorizados.

---

## 6. Acceptance criteria

- migración explícita y histórica;
- downgrade acotado a 2A;
- todos los Major findings resueltos;
- repository boundaries completos según plan;
- invariantes físicas/guardas implementadas;
- historial append-only protegido por API de repositorio;
- tests obligatorios presentes;
- dos ejecuciones consecutivas de pytest completamente verdes;
- sin residuos temporales bloqueantes;
- sin archivos fuera de Scope Lock;
- sin nuevas dependencias ni integraciones.

---

## 7. Completion protocol

Implementar con `Implement Task`.

Commit:

`Fix phase 2A persistence review findings`

Push únicamente a `origin/codex-work`.

No merge a `main`.
