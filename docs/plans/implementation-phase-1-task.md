# Implementation Phase 1 Analysis Task

**Estado:** Approved for Analyze
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Analizar la primera fase de implementación del Asistente Comercial ACLIMAR.

La meta es definir el primer incremento ejecutable y verificable sin intentar construir todo el MVP de una vez.

No debe escribirse código en esta tarea.

---

## 2. Baseline documental aprobado

Leer obligatoriamente:

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/plans/technical-stack-decisions.md`
- `docs/plans/remote-ai-data-policy.md`
- `docs/plans/templates/implementation-plan.md`

---

## 3. Objetivo de la primera implementación

Proponer el mínimo vertical slice que permita arrancar la aplicación local y comprobar que la base técnica funciona.

El análisis debe evaluar, como mínimo, si la primera fase debería incluir:

- estructura inicial del paquete/app;
- FastAPI;
- Uvicorn;
- Jinja2;
- configuración TOML no secreta;
- SQLite;
- SQLAlchemy;
- Alembic;
- base de repositories/data access;
- health/status route;
- localhost-only binding;
- CSRF/session groundwork;
- minimal audit/logging groundwork;
- pytest;
- isolated test database;
- migration smoke test;
- app startup test.

No implementar todavía IMAP, Google Calendar, CRM, AI, keyring real, APScheduler workflows, or business UI unless needed only as safe interfaces/stubs.

---

## 4. Required decomposition

The analysis must propose:

1. exact files/directories to create or modify;
2. dependency list for this phase;
3. initial application module boundaries;
4. database bootstrap and migration approach;
5. configuration structure;
6. safe secret abstraction/stub boundary;
7. localhost startup behavior;
8. initial test suite;
9. acceptance criteria;
10. rollback/recovery considerations;
11. what is explicitly deferred to later phases;
12. whether a single implementation task is safe or should be split.

---

## 5. Scope principle

Prefer a small, reviewable, testable foundation.

Do not attempt the full assistant in Phase 1.

No external-system side effects.

No real credentials.

No production mailbox/calendar/CRM/AI access.

---

## 6. Required output

Create only:

`docs/plans/implementation-phase-1-analysis.md`

The document must end with:

- `READY FOR APPROVAL` if implementation can proceed safely with a precise Scope Lock; or
- `BLOCKED` with the exact unresolved decisions.

If READY, include a proposed implementation Scope Lock precise enough for a later Implement Task.

---

# SCOPE LOCK

## IN SCOPE

- Analyze the first implementation increment.
- Create only `docs/plans/implementation-phase-1-analysis.md`.

## OUT OF SCOPE

- code;
- tests;
- dependencies installation;
- database files;
- migrations;
- configuration files;
- credentials;
- external integrations;
- CRM changes;
- modifications to approved design documentation.

## RESTRICTIONS

- READ-ONLY analysis except the one authorized analysis artifact;
- no implementation;
- no modification of `main`;
- commit/push only to `codex-work`;
- STOP on material ambiguity.

---

## 7. Completion protocol

1. create only `docs/plans/implementation-phase-1-analysis.md`;
2. commit:
   `Analyze implementation phase 1`
3. push to `origin/codex-work`;
4. do not merge to `main`.
