# Testing Strategy Design Analysis Task

**Estado:** Approved for Analyze
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Analizar la estrategia de pruebas necesaria para el Asistente Comercial ACLIMAR a partir de la especificación funcional, modelo de datos, arquitectura y seguridad aprobados.

El resultado debe preparar una futura redacción de `docs/testing-strategy.md`.

No debe crear todavía ese documento ni implementar tests.

---

## 2. Documentación obligatoria

Leer:

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/plans/functional-spec-readiness.md`
- `docs/plans/data-model-design-analysis.md`
- `docs/plans/architecture-design-analysis.md`
- `docs/plans/security-design-analysis.md`

---

## 3. Alcance del análisis

Analizar como mínimo:

- pirámide/estrategia de tests;
- unit tests de dominio;
- repository/persistence tests;
- migration tests;
- adapter contract tests;
- IMAP fixtures;
- Calendar mocks/fakes;
- CRM API contract tests;
- AI boundary tests;
- prompt-injection/security tests;
- lifecycle tests;
- facts/inferences/proposals separation;
- identity ambiguity;
- follow-up precedence;
- idempotency;
- revalidation;
- approvals/execution;
- degraded integrations;
- checkpoint recovery;
- Monday/weekend catch-up;
- audit/provenance;
- deletion/redaction;
- remote-AI minimization;
- credential/logging exclusion;
- UI/form/CSRF tests;
- acceptance tests;
- non-production integration tests;
- test data strategy;
- fixtures;
- deterministic clock;
- failure injection;
- regression strategy;
- coverage expectations;
- test isolation from real external systems.

---

## 4. Mandatory safety constraints

Tests must never unintentionally:

- send real email;
- move real mailbox messages;
- create real drafts;
- modify real Google Calendar;
- modify real CRM;
- use production credentials;
- expose secrets in logs;
- transmit real commercial data to remote AI;
- mutate `crm.db` directly.

Real external integration tests, if any are ever added, must use explicitly configured non-production accounts/environments and remain opt-in.

---

## 5. Required output

Create only:

`docs/plans/testing-strategy-design-analysis.md`

It must contain:

1. objective;
2. context;
3. documentation consulted;
4. current state;
5. test layers;
6. domain/unit test scope;
7. persistence/migration scope;
8. adapter/contract test scope;
9. scheduler/checkpoint tests;
10. approval/execution tests;
11. security tests;
12. AI-boundary tests;
13. UI/CSRF tests;
14. degraded-state tests;
15. acceptance/E2E strategy;
16. test data/fixtures;
17. isolation from production systems;
18. regression/coverage strategy;
19. ambiguities;
20. risks;
21. out-of-scope discoveries;
22. Scope Lock;
23. result:
   - READY FOR APPROVAL
   - BLOCKED

---

# SCOPE LOCK

## IN SCOPE

- Analyze testing strategy.
- Create only `docs/plans/testing-strategy-design-analysis.md`.

## OUT OF SCOPE

- `docs/testing-strategy.md`
- code
- tests
- dependencies
- credentials
- database changes
- migrations
- external integrations
- CRM changes
- changes to functional/data-model/architecture/security docs

## RESTRICTIONS

- no implementation;
- no real external-system mutation;
- no production credentials;
- no modification of `main`;
- commit/push only to `codex-work`;
- STOP if a material testing policy ambiguity remains.

---

## 6. Completion protocol

1. create only `docs/plans/testing-strategy-design-analysis.md`;
2. commit:
   `Analyze commercial assistant testing strategy`
3. push to `origin/codex-work`;
4. do not merge to `main`.
