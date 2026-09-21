# Data Model Design Task

**Estado:** Approved for Analyze
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Diseñar `docs/data-model.md` para el Asistente Comercial ACLIMAR a partir de la especificación funcional aprobada.

El diseño debe definir el modelo conceptual y lógico necesario para soportar el MVP sin elegir todavía detalles físicos de implementación no aprobados.

---

## 2. Contexto

La especificación funcional ha sido declarada `READY FOR APPROVAL` en:

- `docs/plans/functional-spec-readiness.md`

El proyecto sigue en fase documental.

**NO IMPLEMENTATION YET.**

No existe todavía código de aplicación, base de datos, migraciones, dependencias ni test suite.

---

## 3. Documentación obligatoria

Leer antes de analizar:

- `AGENTS.md`
- `docs/functional-spec.md`
- `docs/plans/functional-spec-readiness.md`
- `docs/plans/templates/implementation-plan.md`

Aplicar estrictamente `skills/analyze-task/SKILL.md`.

---

## 4. Alcance funcional que debe cubrir el modelo

El modelo debe contemplar, cuando corresponda:

- sources / source records;
- activities;
- conversations / threads;
- manual notes;
- manually pasted WhatsApp text;
- Calendar event representations;
- CRM links;
- confirmed identity links and correction history;
- extracted facts;
- inferences;
- proposals;
- tasks;
- commitments;
- questions;
- next steps;
- alerts;
- follow-up preferences and overrides;
- action proposals;
- approvals / rejections;
- execution results;
- audit trail;
- provenance;
- idempotency keys / source identifiers;
- external-state reconciliation markers;
- source deletion / redaction state;
- configuration references that belong in the data model.

The CRM remains authoritative for:

- companies;
- contacts/interlocutors;
- works/projects;
- opportunities;
- offers.

The assistant must not create competing master copies of those CRM entities.

---

## 5. Required design questions

Analyze and resolve from approved documentation where possible:

1. Which entities are required?
2. Which are first-class entities vs attributes?
3. Which relationships are 1:1, 1:N, N:M?
4. Which records require immutable history?
5. Which records represent current state vs event history?
6. How should facts, inferences and proposals remain distinguishable?
7. How should provenance be represented?
8. How should corrections be modeled without silent history rewrite?
9. How should confirmed identity links be represented and superseded?
10. How should CRM references be stored without duplicating CRM master data?
11. How should external source IDs support deduplication/idempotency?
12. How should deleted-at-source states be represented?
13. Which lifecycle states require explicit modeling?
14. Which timestamps are functionally required?
15. Which uniqueness/integrity constraints are required at logical level?
16. Which elements are deliberately deferred to architecture or security?

---

## 6. Prohibited decisions

Do NOT choose yet:

- database engine;
- ORM;
- migration framework;
- encryption library;
- storage driver;
- framework;
- AI provider;
- scheduler;
- deployment method;
- packaging mechanism.

Do not create code.

Do not create migrations.

Do not create a database.

Do not install dependencies.

Do not modify external systems.

---

## 7. Ambiguity rule

If two or more reasonable data-model interpretations exist and the functional specification does not resolve them:

STOP.

Record the ambiguity precisely.

Do not choose silently.

Escalate only the decision that requires user approval.

---

## 8. Required Analyze Task output

Create:

`docs/plans/data-model-design-analysis.md`

It must contain:

1. Objective
2. Context
3. Documentation consulted
4. Current state
5. Proposed conceptual entities
6. Proposed relationships
7. Lifecycle/state implications
8. Provenance/audit implications
9. CRM-boundary implications
10. Integrity/idempotency requirements
11. Security/data-governance implications that affect the model
12. Ambiguities
13. Risks
14. Out-of-scope discoveries
15. Scope Lock
16. Result:
   - `READY FOR APPROVAL`
   - `BLOCKED`

Do NOT create `docs/data-model.md` yet.

---

# SCOPE LOCK

## IN SCOPE

- Read approved project documentation.
- Analyze the logical/conceptual data model.
- Create only:
  - `docs/plans/data-model-design-analysis.md`

## OUT OF SCOPE

- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- application code;
- tests;
- dependencies;
- database creation;
- migrations;
- external-system changes;
- CRM repository changes.

## RESTRICTIONS

- No implementation.
- No architecture selection.
- No physical database selection.
- No change to approved functional rules.
- No modification of `main`.
- Commit and push only to `codex-work`.

---

## 9. Completion protocol

After the analysis:

1. verify that only the authorized analysis file was added;
2. commit with:
   `Analyze commercial assistant data model`
3. push to `origin/codex-work`;
4. report the resulting commit SHA.

Do not create `docs/data-model.md` until the analysis is reviewed and explicitly approved.
