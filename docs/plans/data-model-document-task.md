# Data Model Document Task

**Estado:** Approved
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Crear `docs/data-model.md` para el Asistente Comercial ACLIMAR a partir de:

- `docs/functional-spec.md`
- `docs/plans/functional-spec-readiness.md`
- `docs/plans/data-model-design-analysis.md`

El documento debe definir el modelo conceptual y lógico aprobado para el MVP.

No debe seleccionar todavía tecnología física de persistencia.

---

## 2. Preconditions

Antes de modificar archivos, leer:

- `AGENTS.md`
- `skills/implement-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/plans/functional-spec-readiness.md`
- `docs/plans/data-model-design-analysis.md`

La fase de diseño fue aprobada explícitamente por el usuario.

---

## 3. Alcance del documento

`docs/data-model.md` debe definir como mínimo:

1. principios del modelo;
2. límites de autoridad entre CRM y asistente;
3. entidades conceptuales;
4. atributos lógicos principales;
5. relaciones y cardinalidades;
6. estados y lifecycles;
7. current state vs history;
8. provenance;
9. auditability;
10. facts vs inferences vs proposals;
11. source records and source observations;
12. conversations / email threads;
13. activities;
14. manual notes;
15. manual WhatsApp imports;
16. Calendar event representations;
17. CRM references;
18. confirmed identity links and correction history;
19. tasks;
20. commitments;
21. questions;
22. next steps;
23. alerts;
24. follow-up preferences / overrides;
25. action proposals;
26. approval decisions;
27. execution results;
28. audit events;
29. configuration references that belong in the model;
30. idempotency and uniqueness requirements;
31. deleted-at-source / redaction states;
32. required timestamps;
33. logical integrity constraints;
34. deferred physical-design decisions.

---

## 4. Design constraints

The model must:

- keep CRM authoritative for companies, contacts/interlocutors, works/projects, opportunities and offers;
- store only external CRM references needed for context and traceability;
- preserve unresolved ambiguity instead of forcing links;
- keep facts, inferences and proposals distinct;
- preserve correction/supersession history;
- support append-only audit history for executed actions;
- support source deletion/redaction without erasing required audit metadata;
- support idempotency;
- support external-state revalidation evidence;
- support one configured primary Calendar in MVP;
- support one mailbox initially;
- not contain credentials or secrets.

---

## 5. Prohibited decisions

Do NOT choose:

- database engine;
- ORM;
- migration framework;
- encryption library;
- filesystem implementation;
- scheduler;
- application framework;
- AI provider;
- integration library;
- packaging/deployment mechanism.

Do not create code.
Do not create migrations.
Do not create a database.
Do not modify external systems.

---

## 6. Required level of detail

The document must be concrete enough that later architecture and implementation work can use it without inventing new business semantics.

For each first-class entity, include where applicable:

- purpose;
- logical identity;
- main attributes;
- lifecycle/state;
- provenance requirements;
- history requirements;
- relationships;
- integrity constraints;
- external-reference behavior;
- deletion/redaction behavior.

Use names that are implementation-neutral.

---

## 7. Scope Lock

### IN SCOPE

Create only:

- `docs/data-model.md`

### OUT OF SCOPE

- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- application code
- tests
- dependencies
- database files
- migrations
- CRM repository changes
- external-system changes
- changes to `docs/functional-spec.md`

### RESTRICTIONS

- no technology selection;
- no functional-rule changes;
- no architecture decisions outside what is necessary to express the logical model;
- no changes to `main`;
- commit and push only to `codex-work`.

---

## 8. Acceptance criteria

The task is complete only if:

- every assistant-owned domain concept in the functional spec is represented or explicitly justified as non-first-class;
- CRM master entities are not duplicated;
- lifecycle states exactly match the approved functional specification;
- provenance and audit chain are representable;
- identity-link corrections are representable without silent rewrite;
- idempotency requirements are explicit;
- source deletion/redaction behavior is defined logically;
- no physical storage technology is selected;
- no contradiction with `functional-spec.md` or `AGENTS.md` is introduced.

---

## 9. Completion protocol

After creating the document:

1. verify that only `docs/data-model.md` was added or modified for this task;
2. review the document against the analysis and functional specification;
3. commit with:
   `Add commercial assistant data model`
4. push to `origin/codex-work`;
5. report the resulting commit SHA.

Do not merge to `main`.
