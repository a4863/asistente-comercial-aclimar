# Security Document Task

**Estado:** Approved
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Crear `docs/security.md` para el Asistente Comercial ACLIMAR a partir de:

- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/plans/technical-stack-decisions.md`
- `docs/plans/remote-ai-data-policy.md`
- `docs/plans/security-design-analysis.md`

El documento debe definir la postura de seguridad y gobierno de datos del MVP sin implementar controles todavía.

---

## 2. Documentación obligatoria

Leer antes de modificar:

- `AGENTS.md`
- `skills/implement-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/plans/technical-stack-decisions.md`
- `docs/plans/remote-ai-data-policy.md`
- `docs/plans/security-design-analysis.md`

---

## 3. Contenido mínimo requerido

`docs/security.md` debe definir como mínimo:

1. objetivos de seguridad;
2. modelo de amenazas del MVP;
3. trust boundaries;
4. localhost-only/network posture;
5. local-user/session model;
6. CSRF protections for state-changing requests;
7. browser/session handling;
8. credential/token lifecycle;
9. Windows Credential Manager;
10. secret-reference rules;
11. IMAP/Google/CRM/AI auth handling;
12. prompt-injection/untrusted-data policy;
13. remote-AI disclosure matrix;
14. data minimization;
15. source retention;
16. deletion/redaction;
17. logs and error handling;
18. audit payload rules;
19. attachments/temp files;
20. local backup/recovery posture;
21. file permissions/local data protection;
22. test/dev credential isolation;
23. dependency/supply-chain controls;
24. approval integrity;
25. external-state revalidation;
26. idempotency/security implications;
27. incident/reconnect/degraded-state behavior;
28. prohibited security shortcuts;
29. deferred security decisions;
30. out-of-MVP controls.

---

## 4. Mandatory remote-AI policy

The document must reproduce and operationalize the approved policy from:

`docs/plans/remote-ai-data-policy.md`

Key rules include:

- minimum necessary context only;
- relevant email body allowed with minimization;
- relevant metadata allowed;
- identifiable contact/company allowed when necessary;
- work/project/opportunity/offer context allowed selectively;
- notes/WhatsApp allowed when intentionally processed;
- Calendar data allowed with minimization;
- CRM-derived context allowed selectively;
- attachments not transmitted automatically;
- credentials/tokens/secrets always prohibited;
- whole databases/exports always prohibited;
- logs/audit prohibited by default;
- unrelated records always prohibited;
- AI has no execution authority.

Do not weaken these rules.

---

## 5. Technical stack assumptions

Security design must be consistent with:

- Python 3.11+
- FastAPI
- Jinja2
- localhost 127.0.0.1
- SQLite
- SQLAlchemy
- Alembic
- APScheduler
- IMAPClient
- Google API/OAuth
- httpx
- keyring + Windows Credential Manager
- TOML non-secret config
- Uvicorn
- Windows Task Scheduler
- pytest

---

# SCOPE LOCK

## IN SCOPE

Create only:

- `docs/security.md`

## OUT OF SCOPE

- `docs/testing-strategy.md`
- code
- tests
- dependencies
- credentials
- configuration files
- database changes
- migrations
- external integration setup
- CRM repository changes
- changes to functional-spec/data-model/architecture

## RESTRICTIONS

- no implementation;
- no real secrets;
- no change to `main`;
- commit/push only to `codex-work`;
- no weakening of approved remote-AI policy;
- no new functional behavior.

---

## 6. Acceptance criteria

The task is complete only if:

- security posture is explicit and implementable;
- trust boundaries are clear;
- secrets are excluded from code/Git/TOML/SQLite/logs;
- localhost does not substitute for CSRF/session protection;
- prompt injection is explicitly addressed;
- remote-AI disclosure policy is complete and exact;
- retention/deletion/audit balance is defined;
- attachments/temp files are controlled;
- tests/development secrets are isolated;
- degraded/reconnect behavior is defined;
- no contradiction with functional/data-model/architecture documents is introduced.

---

## 7. Completion protocol

1. create only `docs/security.md`;
2. verify diff and Scope Lock;
3. commit with:
   `Add commercial assistant security design`
4. push to `origin/codex-work`;
5. do not merge to `main`.
