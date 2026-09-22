# Phase 2B1 Implementation Task — Models and Migration

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-2b-plan.md`

## 1. Objetivo

Implementar únicamente el esquema persistente de Fase 2B y su migración Alembic 0003.

No implementar todavía repositories ni lógica de transición.

## 2. Entidades/tablas autorizadas

Crear únicamente:

- task
- commitment
- question
- next_step
- alert
- follow_up_preference
- follow_up_preference_history
- action_proposal
- approval_decision
- execution_result
- operational_evidence_link

## 3. Constraints mínimos obligatorios

### Task
Estados:
- proposed
- pending
- completed
- cancelled

### Commitment
Estados:
- detected
- confirmed
- fulfilled
- overdue
- cancelled

### Question
Estados:
- detected
- open
- answered
- dismissed

### NextStep
Estados:
- proposed
- planned
- completed
- cancelled

### Alert
Estados:
- active
- resolved
- dismissed

Debe existir mecanismo físico para impedir duplicar una alerta activa para la misma:
`alert_type + target_type + target_id + condition_key`

Una alerta resolved/dismissed no debe bloquear una recurrencia futura.

### ActionProposal
Estados:
- pending_approval
- approved
- rejected
- executed
- error

### ApprovalDecision
Append-only.
Debe referenciar exactamente una ActionProposal.

### ExecutionResult
Append-only.
Debe referenciar ActionProposal y, cuando aplique, ApprovalDecision.
Debe poder almacenar evidencia/referencia de revalidación, outcome, external result reference y failure code sin payload externo arbitrario.

### OperationalEvidenceLink
Append-only.
Debe enlazar un objeto operacional a uno de:
- source
- fact
- inference
- proposal
- user_confirmation

El tipo debe estar físicamente restringido.

### FollowUpPreference
Debe soportar:
- scope_type
- scope_reference
- classification
- inactivity_days
- explicit_future_date
- provenance/current timestamps

Una preferencia actual por scope.

### FollowUpPreferenceHistory
Append-only.
Debe preservar cambios de preferencia con timestamp/provenance.

## 4. Relaciones 2A

Usar FKs a entidades 2A solo cuando el plan lo requiera y exista FK física viable.

No copiar master data CRM.

## 5. Migración 0003

Crear:

`alembic/versions/0003_phase_2b_operational_entities.py`

Requisitos:

- operaciones Alembic explícitas;
- no `Base.metadata.create_all/drop_all`;
- no import de modelos de aplicación;
- upgrade solo 2B;
- downgrade solo 2B en orden inverso;
- índices necesarios para:
  - due dates;
  - follow-up precedence;
  - active alert dedup;
  - action idempotency/lookup.

## 6. Archivos autorizados

Solo:

```text
app/persistence/models.py
alembic/versions/0003_phase_2b_operational_entities.py
test/test_migrations.py
test/test_persistence_models.py
```

No modificar ningún otro archivo.

## 7. Tests obligatorios

Añadir tests para:

- migration 0002 -> 0003;
- downgrade 0003 -> 0002;
- re-upgrade;
- expected 2B tables;
- state check constraints;
- active alert dedup and recurrence after closed state;
- one current follow-up preference per scope;
- OperationalEvidenceLink type restriction;
- append-only history tables structurally separate;
- ActionProposal state check;
- required FK integrity.

No repository tests todavía.

## 8. Validación

Ejecutar:

`python -m pytest test/test_persistence_models.py test/test_migrations.py`

Debe quedar verde.

## 9. STOP conditions

STOP si:

- necesitas repositories.py;
- necesitas conftest.py;
- necesitas otra entidad;
- necesitas nueva dependencia;
- necesitas tocar main;
- necesitas decidir una regla funcional no incluida en el plan/decisions.

## 10. Completion protocol

Commit:

`Implement phase 2B1 models and migration`

Push solo a `origin/codex-work`.

No tocar `main`.
