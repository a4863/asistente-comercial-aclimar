# Phase 3A1 Implementation Task — Email Data Model and Migration

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3a-plan.md`

## 1. Objetivo

Implementar únicamente la base persistente de correo aprobada para Phase 3A.

No implementar configuración IMAP, keyring, IMAPClient, credenciales ni red en este bloque.

## 2. Entidades autorizadas

Crear únicamente:

- `EmailMessage`
- `IMAPMessageLocation`
- `EmailAttachmentMetadata`

## 3. EmailMessage

Campos mínimos:
- id
- created_at
- source_record_id FK unique required
- normalized_message_id nullable
- sender_address nullable
- recipient_addresses nullable text
- subject nullable
- sent_at nullable
- received_at nullable
- in_reply_to nullable
- references_header nullable text
- normalized_body nullable text
- body_size_bytes nullable non-negative
- content_truncated required boolean default false
- provenance required

Reglas:
- no unique global sobre normalized_message_id;
- no raw MIME;
- no HTML raw duplicado;
- no attachment bytes.

## 4. IMAPMessageLocation

Campos mínimos:
- id
- created_at
- email_message_id FK required
- account_scope required
- folder_name required
- uidvalidity required integer-compatible non-negative
- uid required integer-compatible positive
- location_state required, default active
- last_observed_at required
- provenance required

Constraints:
- unique (account_scope, folder_name, uidvalidity, uid)
- location_state IN ('active','unavailable')
- uidvalidity >= 0
- uid > 0
- lookup index por account_scope/folder_name/uidvalidity/uid

No unique sobre email_message_id.

## 5. EmailAttachmentMetadata

Campos mínimos:
- id
- created_at
- email_message_id FK required
- part_index required
- filename nullable
- media_type nullable
- byte_size nullable
- content_id nullable
- disposition nullable
- provenance required

Constraints:
- unique (email_message_id, part_index)
- part_index >= 0
- byte_size IS NULL OR byte_size >= 0

No campo de bytes/blob/raw content.

## 6. Migración 0004

Crear:

`alembic/versions/0004_phase_3a_email_data_foundation.py`

Requisitos:
- down_revision = 0003
- operaciones Alembic explícitas
- no Base.metadata.create_all/drop_all
- no import de modelos
- upgrade crea solo las tres tablas y sus índices/constraints
- downgrade elimina solo objetos 0004 en orden inverso
- reversible 0003 -> 0004 -> 0003 -> 0004

## 7. Archivos autorizados

Solo:

```text
app/persistence/models.py
alembic/versions/0004_phase_3a_email_data_foundation.py
test/test_persistence_models.py
test/test_migrations.py
```

No modificar ningún otro archivo.

## 8. Tests obligatorios

Cubrir:
- EmailMessage 1:1 con SourceRecord mediante unique source_record_id;
- normalized_message_id absent/duplicate permitido;
- body_size_bytes negativo rechazado;
- location duplicate key rechazado;
- múltiples locations para un EmailMessage permitidas;
- location_state inválido rechazado;
- uid/uidvalidity inválidos rechazados;
- attachment duplicate part_index rechazado;
- negative part_index / byte_size rechazados;
- schema no contiene raw MIME/attachment bytes fields;
- migration 0003 -> 0004 -> 0003 -> 0004;
- las tablas 0001–0003 sobreviven al downgrade de 0004.

## 9. Validación

Ejecutar:

`python -m pytest test/test_persistence_models.py test/test_migrations.py`

Debe quedar verde.

## 10. STOP conditions

STOP si necesitas:
- repositories.py
- config.py
- pyproject.toml
- credentials.py
- conftest.py
- main.py
- otra entidad
- red/IMAP/keyring real
- cambiar 0001–0003
- inventar una regla no aprobada

## 11. Completion protocol

Commit:

`Implement phase 3A1 email data foundation`

Push solo a `origin/codex-work`.

No tocar `main`.
