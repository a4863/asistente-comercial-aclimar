# Implementation Phase 1 Plan Task

**Estado:** Approved for planning
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Crear el plan de implementación ejecutable para la Fase 1 del Asistente Comercial ACLIMAR a partir del análisis aprobado.

No escribir código todavía.

---

## 2. Documentación obligatoria

Leer:

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/plans/technical-stack-decisions.md`
- `docs/plans/implementation-phase-1-analysis.md`
- `docs/plans/templates/implementation-plan.md`

---

## 3. Entregable

Crear únicamente:

`docs/plans/implementation-phase-1-plan.md`

El plan debe seguir la plantilla de implementación existente y ser suficientemente preciso para una posterior ejecución con `Implement Task`.

---

## 4. Contenido mínimo

El plan debe incluir:

1. objetivo del incremento;
2. baseline/commit de partida;
3. precondiciones;
4. Scope Lock exacto;
5. lista exacta de archivos/directorios a crear/modificar;
6. dependencias a añadir;
7. orden de implementación;
8. estructura de módulos;
9. configuración TOML;
10. bootstrap SQLite/SQLAlchemy;
11. Alembic inicial;
12. health/status route y template;
13. localhost-only enforcement;
14. sesión/CSRF groundwork sin mutaciones externas;
15. logging/audit groundwork;
16. tests exactos a crear;
17. comandos de test;
18. criterios de aceptación;
19. validaciones negativas/prohibiciones;
20. rollback/recovery;
21. riesgos;
22. condiciones STOP;
23. Definition of Done.

---

## 5. Scope constraints inherited from analysis

### In scope

- FastAPI/Uvicorn local app foundation;
- Jinja2 status UI;
- non-secret TOML config;
- SQLite;
- SQLAlchemy 2.x;
- Alembic;
- repository/session foundation;
- safe audit/logging groundwork;
- session/CSRF groundwork;
- pytest;
- isolated test DB;
- startup/status/config/migration tests.

### Out of scope

- IMAP;
- Google Calendar;
- CRM API;
- AI;
- keyring real integration;
- APScheduler workflows;
- Windows Task Scheduler setup;
- business workflows;
- full commercial data model;
- real credentials;
- external mutations;
- production integration tests.

---

## 6. Required file set

The plan must validate whether the following exact file set is sufficient and, if so, use it as the implementation Scope Lock:

```text
app/
  __init__.py
  main.py
  config.py
  web/routes.py
  web/templates/status.html
  persistence/database.py
  persistence/models.py
  persistence/repositories.py
  audit.py
  security/session.py
alembic/
  env.py
  versions/<initial_baseline>.py
alembic.ini
pyproject.toml
config.example.toml
test/
  conftest.py
  test_startup.py
  test_status.py
  test_config.py
  test_migrations.py
```

If a materially necessary file is missing, STOP and explain before expanding scope.

---

# SCOPE LOCK

## IN SCOPE

- Create only `docs/plans/implementation-phase-1-plan.md`.

## OUT OF SCOPE

- code;
- tests;
- dependency installation;
- database files;
- migrations execution;
- configuration files;
- external integrations;
- changes to approved design docs;
- changes to `main`.

## RESTRICTIONS

- no implementation;
- no external calls;
- no real credentials;
- commit/push only to `codex-work`;
- STOP on material ambiguity.

---

## 7. Completion protocol

1. create only `docs/plans/implementation-phase-1-plan.md`;
2. commit:
   `Plan implementation phase 1`
3. push to `origin/codex-work`;
4. do not merge to `main`.
