# Testing Strategy Document Task

**Estado:** Approved
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Crear `docs/testing-strategy.md` para el Asistente Comercial ACLIMAR a partir de:

- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/plans/testing-strategy-design-analysis.md`

El documento debe definir la estrategia de pruebas del MVP sin implementar tests todavía.

---

## 2. Documentación obligatoria

Leer antes de modificar:

- `AGENTS.md`
- `skills/implement-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/plans/testing-strategy-design-analysis.md`

---

## 3. Contenido mínimo requerido

`docs/testing-strategy.md` debe definir como mínimo:

1. objetivos de testing;
2. test pyramid;
3. unit/domain tests;
4. application-service tests;
5. repository tests;
6. SQLite isolated test databases;
7. Alembic migration tests;
8. IMAP adapter/fixture tests;
9. Calendar adapter tests;
10. CRM API contract tests;
11. AI boundary tests;
12. credential-store fake tests;
13. deterministic clock/scheduler tests;
14. checkpoint/restart/weekend catch-up tests;
15. lifecycle-state tests;
16. facts/inferences/proposals tests;
17. identity ambiguity/correction tests;
18. follow-up precedence tests;
19. approval/revalidation/idempotency tests;
20. audit/provenance tests;
21. source deletion/redaction tests;
22. degraded integration tests;
23. prompt-injection tests;
24. remote-AI disclosure/minimization tests;
25. CSRF/session/UI tests;
26. acceptance/E2E scenarios using fakes;
27. synthetic test data strategy;
28. real-integration opt-in policy;
29. regression policy;
30. coverage philosophy;
31. forbidden-test behaviors;
32. CI/release items deferred.

---

## 4. Mandatory safety rules

Normal automated tests must never:

- send real email;
- move real mailbox messages;
- create real mailbox drafts;
- modify real Google Calendar;
- modify real CRM;
- access `crm.db` directly;
- use production credentials;
- send real commercial data to remote AI;
- expose secrets in logs;
- depend on live production integrations.

Any future real integration test must be:

- explicit opt-in;
- non-production only;
- separately configured;
- excluded from normal test runs.

---

## 5. Acceptance scenario requirement

The strategy must include the approved MVP end-to-end scenario using synthetic fixtures/fakes:

1. ingest email;
2. reconstruct thread;
3. identify context when unambiguous;
4. extract exact questions;
5. query/fake CRM context;
6. generate next steps;
7. generate response proposal;
8. propose existing folder;
9. approve action;
10. revalidate;
11. execute fake move;
12. create fake draft;
13. create corresponding internal tasks;
14. record audit trail.

No production external mutation is allowed in the acceptance test.

---

# SCOPE LOCK

## IN SCOPE

Create only:

- `docs/testing-strategy.md`

## OUT OF SCOPE

- code
- tests
- dependencies
- fixtures
- credentials
- database files
- migrations
- external integration setup
- CRM repository changes
- changes to functional/data-model/architecture/security docs

## RESTRICTIONS

- no implementation;
- no real external-system mutation;
- no production credentials;
- no change to `main`;
- commit/push only to `codex-work`.

---

## 6. Acceptance criteria

The task is complete only if:

- all critical functional lifecycles are covered;
- all external adapters have a safe contract-test approach;
- production systems are isolated from normal tests;
- idempotency/revalidation/degraded-state behavior is explicit;
- security and remote-AI policy have dedicated test coverage;
- the E2E acceptance scenario is defined with synthetic sources;
- no contradiction with approved design docs is introduced.

---

## 7. Completion protocol

1. create only `docs/testing-strategy.md`;
2. verify diff and Scope Lock;
3. commit with:
   `Add commercial assistant testing strategy`
4. push to `origin/codex-work`;
5. do not merge to `main`.
