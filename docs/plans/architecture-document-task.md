# Architecture Document Task

**Estado:** Approved
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Crear `docs/architecture.md` para el Asistente Comercial ACLIMAR a partir de:

- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/plans/architecture-decisions.md`
- `docs/plans/architecture-design-analysis.md`

El documento debe definir la arquitectura lógica y técnica del MVP sin implementar código.

---

## 2. Decisiones ya aprobadas

La arquitectura debe incorporar obligatoriamente:

1. aplicación web local accesible por localhost;
2. persistencia relacional embebida con capa de acceso a datos;
3. sincronización periódica dentro del proceso principal;
4. funcionamiento previsto 24h/día de lunes a viernes;
5. reconciliación incremental tras downtime y fin de semana;
6. credenciales en almacén seguro del sistema operativo;
7. frontera IA independiente de proveedor;
8. posibilidad de IA remota solo bajo las futuras reglas de `docs/security.md`.

---

## 3. Documentación obligatoria

Leer antes de modificar:

- `AGENTS.md`
- `skills/implement-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/plans/architecture-decisions.md`
- `docs/plans/architecture-design-analysis.md`

---

## 4. Contenido mínimo requerido

`docs/architecture.md` debe definir como mínimo:

1. objetivos arquitectónicos;
2. contexto de ejecución local;
3. diagrama textual de componentes;
4. UI local;
5. capa de dominio;
6. capa de persistencia;
7. integraciones/adapters;
8. IMAP;
9. Google Calendar;
10. CRM API;
11. notas/WhatsApp manual;
12. AI service boundary;
13. approval/execution boundary;
14. synchronization coordinator;
15. checkpoints;
16. degraded integration states;
17. error isolation;
18. audit/logging;
19. observabilidad local;
20. configuración;
21. secretos;
22. startup/shutdown behavior;
23. weekday 24h operation;
24. weekend downtime and Monday catch-up;
25. idempotency;
26. revalidation;
27. security boundary assumptions;
28. testing boundaries;
29. deferred decisions;
30. out-of-MVP architecture.

---

## 5. Technology decisions allowed in this document

The document MAY now propose and justify concrete MVP choices for:

- programming language;
- web framework;
- embedded relational database;
- ORM/data-access layer;
- migration mechanism;
- scheduling mechanism;
- IMAP client library;
- Google Calendar integration library;
- CRM HTTP client;
- local configuration approach;
- Windows secure credential-store integration;
- AI abstraction interface;
- local startup mechanism.

If more than one materially different option remains reasonable and the approved decisions do not resolve it, STOP rather than choosing silently.

---

## 6. Mandatory constraints

The architecture must remain:

- local-only;
- single-user;
- localhost-only;
- CRM API-only;
- no direct `crm.db`;
- no automatic email sending;
- no autonomous external mutations;
- approval-driven;
- idempotent;
- auditable;
- resilient to individual integration failures;
- simple enough for a local monolithic application;
- free of unnecessary distributed infrastructure.

Do not introduce microservices, message brokers, distributed queues, Kubernetes, cloud databases, hosted backends, or SaaS infrastructure.

---

# SCOPE LOCK

## IN SCOPE

Create only:

- `docs/architecture.md`

## OUT OF SCOPE

- `docs/security.md`
- `docs/testing-strategy.md`
- code
- tests
- dependencies
- database files
- migrations
- external integration setup
- CRM repository changes
- changes to functional-spec or data-model

## RESTRICTIONS

- no implementation;
- no modification of `main`;
- commit/push only to `codex-work`;
- no functional-rule changes.

---

## 7. Acceptance criteria

The task is complete only if:

- the approved architectural decisions are represented exactly;
- components and responsibilities are clearly separated;
- sync/checkpoint/recovery behavior is explicit;
- weekday continuous operation is documented;
- weekend catch-up behavior is documented;
- all external mutations pass through approval/revalidation/execution;
- degraded integration behavior is documented;
- AI remains provider-agnostic;
- credentials remain outside application data;
- no contradiction with `functional-spec.md` or `data-model.md` is introduced.

---

## 8. Completion protocol

1. create only `docs/architecture.md`;
2. verify diff and Scope Lock;
3. commit with:
   `Add commercial assistant architecture`
4. push to `origin/codex-work`;
5. do not merge to `main`.
