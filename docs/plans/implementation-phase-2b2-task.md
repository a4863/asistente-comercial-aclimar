# Phase 2B2 Implementation Task — Operational Repositories and Lifecycles

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-2b-plan.md`

## 1. Objetivo

Implementar únicamente la lógica de repositorio y lifecycle para entidades 2B ya creadas.

No modificar modelos ni migración 0003.

## 2. Archivos autorizados

Solo:

```text
app/persistence/repositories.py
test/test_persistence_repositories.py
```

No modificar ningún otro archivo.

## 3. OperationalRepository

Implementar métodos explícitos, sin CRUD genérico.

### Task

- create_task(...)
- transition_task(task_id, target_state, evidence_reference=None)

Transiciones válidas:
- proposed -> pending
- pending -> completed
- pending -> cancelled
- proposed -> cancelled

Regla:
- completed requiere `evidence_reference` o confirmación de usuario representada explícitamente.

### Commitment

- create_commitment(...)
- transition_commitment(...)
- evaluate_overdue(now)

Transiciones válidas:
- detected -> confirmed
- confirmed -> fulfilled
- confirmed -> overdue
- confirmed -> cancelled
- detected -> cancelled

Reglas:
- fulfilled requiere evidencia/confirmación explícita;
- overdue solo desde confirmed;
- evaluate_overdue(now) solo afecta commitments confirmed con due_at < now;
- evaluate_overdue no marca fulfilled ni cancelled;
- reloj recibido por argumento; no datetime.now interno para esa evaluación.

### Question

- create_question(...)
- transition_question(...)

Transiciones:
- detected -> open
- open -> answered
- open -> dismissed
- detected -> dismissed

answered requiere evidencia/confirmación explícita.

### NextStep

- create_next_step(...)
- transition_next_step(...)

Transiciones:
- proposed -> planned
- planned -> completed
- planned -> cancelled
- proposed -> cancelled

completed requiere evidencia/confirmación explícita.

### Alert

- get_or_create_alert(...)
- resolve_alert(...)
- dismiss_alert(...)

Reglas:
- una activa por condition key;
- resolved puede ser automática;
- dismissed requiere argumento explícito de actor/user confirmation;
- recurrencia posterior crea nueva fila, nunca reabre la antigua.

### Follow-up preference

- set_follow_up_preference(...)
- get_follow_up_preference(...)
- resolve_follow_up_preference(...)

Reglas:
- cada cambio crea `FollowUpPreferenceHistory` append-only;
- precedence:
  1. opportunity / offer / work
  2. company / contact
  3. global
- CRM-derived scope debe preferirse frente a manual fallback cuando ambos se aporten;
- explicit_future_date prevalece sobre inactivity_days en la resolución;
- defaults:
  - new_or_qualified_opportunity: 7
  - sent_offer: 5
  - homologation_docs: 7
  - negotiation_review: 5

No consultar CRM real; resolver únicamente sobre referencias ya persistidas/argumentos.

## 4. ActionRepository

Implementar:

- create_action_proposal(...)
- decide_action(...)
- append_execution_result(...)

### create_action_proposal

- reserva/reutiliza IdempotencyIdentity;
- una identity concreta corresponde a una sola ActionProposal;
- estado inicial pending_approval.

### decide_action

- solo desde pending_approval;
- approved o rejected;
- crea ApprovalDecision append-only;
- actualiza estado del ActionProposal;
- no permite segunda decisión.

### append_execution_result

Requisitos:
- proposal debe estar approved;
- debe existir ApprovalDecision approved;
- `revalidation_reference` obligatorio y no vacío;
- no ejecuta nada externo;
- outcome executed -> proposal state executed;
- outcome error -> proposal state error;
- crea ExecutionResult append-only;
- múltiples intentos permitidos solo si el proposal aún no está executed; después de executed no más intentos.

## 5. Operational evidence

Implementar helper explícito:

- add_operational_evidence(...)

Validar:
- target operational_type permitido;
- evidence_type permitido;
- user_confirmation exige reference y no evidence_id;
- otros tipos exigen evidence_id.

No permitir conversión entre Facts/Inferences/Proposals.

## 6. Audit

Cada transition/approval/execution/evaluation relevante debe append un AuditEvent mediante el patrón existente, sin payload arbitrario.

No modificar `AuditRepository` salvo que sea imprescindible para reutilizar su API existente. Si fuese necesaria una modificación material fuera de este alcance funcional: STOP.

## 7. Tests obligatorios

En `test/test_persistence_repositories.py` cubrir:

- todas las transiciones válidas e inválidas de Task;
- completed sin evidencia => rechazo;
- Commitment valid transitions;
- fulfilled sin evidencia => rechazo;
- controlled-clock evaluate_overdue;
- Question answered sin evidencia => rechazo;
- NextStep completed sin evidencia => rechazo;
- alert active dedup;
- resolve + recurrence nueva fila;
- dismiss exige actor explícito;
- follow-up preference history;
- precedence exacta;
- explicit_future_date beats inactivity_days;
- default thresholds;
- action idempotency reuse;
- approve/reject;
- segunda decisión rechazada;
- execution sin aprobación rechazada;
- execution sin revalidation rechazada;
- executed/error state updates;
- no second execution after executed;
- evidence validation;
- audit event appended on lifecycle/decision/execution.

## 8. Validación

Ejecutar:

`python -m pytest test/test_persistence_repositories.py test/test_persistence_models.py test/test_migrations.py`

Debe quedar verde.

Después ejecutar:

`python -m pytest`

Debe quedar verde.

## 9. STOP conditions

STOP si necesitas:

- modificar models.py;
- modificar migration 0003;
- modificar conftest.py;
- crear otra entidad;
- implementar scheduler;
- hacer network/external call;
- tocar main;
- añadir dependencia;
- inventar una regla no contenida en plan/decisions.

## 10. Completion protocol

Commit:

`Implement phase 2B2 operational repositories`

Push solo a `origin/codex-work`.

No tocar `main`.
