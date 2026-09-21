# Security Design Analysis Task

**Estado:** Approved for Analyze
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Analizar los requisitos de seguridad y gobierno de datos del Asistente Comercial ACLIMAR a partir de la especificación funcional, el modelo de datos y la arquitectura aprobados.

El resultado debe preparar una futura redacción de `docs/security.md`.

No debe crear todavía ese documento ni implementar controles.

---

## 2. Documentación obligatoria

Leer:

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/plans/architecture-decisions.md`
- `docs/plans/technical-stack-decisions.md`

---

## 3. Alcance del análisis

Analizar como mínimo:

- clasificación de datos;
- credenciales y tokens;
- Windows Credential Manager;
- secretos fuera de SQLite/TOML/logs;
- localhost-only;
- exposición de red;
- OAuth/tokens Google;
- IMAP credentials;
- CRM credentials/API auth;
- AI credentials;
- remote AI disclosure policy;
- data minimization;
- prompt injection;
- untrusted external content;
- source retention;
- deletion/redaction;
- logs;
- audit events;
- sensitive content in errors;
- local-user access model;
- backups;
- recovery;
- temporary files;
- attachments;
- browser/session security;
- CSRF considerations for localhost mutations;
- action approval integrity;
- revalidation;
- idempotency security implications;
- dependency and supply-chain controls;
- development/test credential separation;
- failure/reconnect states.

---

## 4. Required remote-AI decision

The analysis MUST define the exact data classes that may and may not leave the device if a remote AI provider is later selected.

At minimum distinguish:

- email body;
- email metadata;
- contact identity;
- company identity;
- work/project context;
- opportunity/offer context;
- manual notes;
- manually pasted WhatsApp text;
- Calendar event data;
- CRM-derived context;
- attachments;
- credentials/tokens;
- whole database exports;
- logs/audit data;
- unrelated records.

If there is a material ambiguity about what commercial content may be disclosed remotely, STOP and escalate that decision.

---

## 5. Security posture constraints

Mandatory:

- local-only application;
- bind only to 127.0.0.1;
- single-user;
- no public/LAN exposure by default;
- credentials in Windows secure store;
- secrets excluded from Git, TOML, SQLite plaintext fields, and logs;
- external content treated as untrusted data;
- no instructions embedded in source content can override application rules;
- no external mutation without explicit approval;
- no automatic email sending;
- no direct CRM database access;
- remote AI receives minimum necessary data only;
- attachments not transmitted automatically;
- whole databases never transmitted to AI.

---

## 6. Required output

Create only:

`docs/plans/security-design-analysis.md`

It must contain:

1. objective;
2. context;
3. documentation consulted;
4. current state;
5. data classification;
6. trust boundaries;
7. credential/token lifecycle;
8. localhost/network posture;
9. browser/session protections;
10. external-content/prompt-injection controls;
11. remote-AI disclosure matrix;
12. retention/deletion/redaction;
13. logging/audit controls;
14. attachment/temp-file policy;
15. backup/recovery implications;
16. test/dev secret isolation;
17. dependency/supply-chain implications;
18. approval/execution integrity;
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

- Analyze security and data-governance requirements.
- Create only `docs/plans/security-design-analysis.md`.

## OUT OF SCOPE

- `docs/security.md`
- `docs/testing-strategy.md`
- code
- dependencies
- configuration files
- credentials
- database changes
- external integrations
- CRM changes
- changes to functional-spec/data-model/architecture

## RESTRICTIONS

- no implementation;
- no secrets;
- no real credential handling;
- no modification of `main`;
- commit/push only to `codex-work`;
- STOP on unresolved material disclosure/security decisions.

---

## 7. Completion protocol

1. create only `docs/plans/security-design-analysis.md`;
2. commit:
   `Analyze commercial assistant security`
3. push to `origin/codex-work`;
4. do not merge to `main`.
