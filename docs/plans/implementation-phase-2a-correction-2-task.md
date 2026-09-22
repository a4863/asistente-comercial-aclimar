# Phase 2A Correction 2 Task — Repository Boundaries

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Objetivo

Implementar únicamente los repositorios faltantes y las guardas de invariantes de acceso para Fase 2A.

No modificar modelos, migración ni fixtures globales.

## 2. Archivos autorizados

Solo:

```text
app/persistence/repositories.py
test/test_persistence_repositories.py
```

No modificar ningún otro archivo.

## 3. Repositorios requeridos

### SourceRepository

Mantener y completar:

- `get_or_create_source(...)`
- `append_observation(...)`
- `mark_retention(...)`
- `get_checkpoint(scope)`
- `upsert_checkpoint(...)`
- `reserve_idempotency(...)`
- `get_idempotency(...)`

Reglas:

- no delete/update genérico;
- no acceso externo;
- checkpoint único por scope;
- idempotency reutiliza el registro existente si ya existe.

### ProvenanceRepository

Implementar operaciones explícitas para:

- crear Conversation;
- añadir ConversationMembership;
- crear ManualNote;
- crear WhatsAppImport;
- crear Activity;
- crear ActivitySourceLink;
- get/create CRMReference;
- crear CRMContextLink;
- crear IdentityLink;
- append IdentityLinkCorrection.

Guardas obligatorias:

- rechazar `CRMContextLink` confirmed sin `confirmed_at`;
- rechazar ambiguous/proposed con `confirmed_at`;
- rechazar `assistant_record_type` fuera de tipos 2A permitidos;
- no aceptar campos CRM master-data no definidos;
- IdentityLinkCorrection debe:
  - rechazar prior == replacement;
  - marcar prior como superseded;
  - no borrar prior;
  - añadir correction row.

### DerivationRepository

Implementar:

- `append_fact(...)`
- `add_fact_evidence(...)`
- `append_inference(...)`
- `add_inference_support(...)`
- `append_proposal(...)`
- `add_proposal_support(...)`

Guardas:

- inference support types: source, fact, inference;
- proposal support types: source, fact, inference, proposal;
- rechazar support type no permitido antes de flush;
- no convertir físicamente Fact <-> Inference <-> Proposal;
- no delete/update genérico.

### AuditRepository

Mantener:

- append
- list_for

Y asegurar:

- solo campos definidos por AuditEvent;
- rechazar claves arbitrarias como payload, secret, token, password, body, raw_content;
- no update/delete.

## 4. Tests obligatorios

En `test/test_persistence_repositories.py` cubrir al menos:

1. checkpoint create/update/get;
2. idempotency reserve/get y deduplicación;
3. conversation membership válida;
4. manual note y WhatsApp create;
5. activity/source link;
6. CRMReference get/create;
7. CRMContextLink valid/invalid states;
8. assistant_record_type inválido rechazado;
9. IdentityLink correction:
   - prior preserved;
   - prior superseded;
   - replacement retained;
   - correction row created;
10. append fact + evidence;
11. append inference + valid support;
12. invalid inference support rejected;
13. append proposal + valid support;
14. invalid proposal support rejected;
15. unsafe audit keys rejected;
16. no update/delete methods in audit repository.

Usar únicamente `db_session` existente.

## 5. Validación

Ejecutar:

`python -m pytest test/test_persistence_repositories.py test/test_persistence_models.py test/test_migrations.py`

Debe quedar verde.

## 6. STOP conditions

STOP si necesitas:

- modificar models.py;
- modificar migration 0002;
- modificar conftest.py;
- crear archivos nuevos;
- añadir dependencia;
- cambiar una decisión funcional del modelo.

## 7. Completion protocol

Commit:

`Fix phase 2A repository boundaries`

Push a `origin/codex-work`.

No tocar `main`.
