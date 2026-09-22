# Phase 3B Plan Task — Read-only IMAP Adapter

**Estado:** Approved for Plan
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`
**Analysis:** `docs/plans/implementation-phase-3b-analysis.md`

## 1. Objetivo

Preparar el plan de implementación de la Fase 3B, limitada al adapter IMAP read-only.

Debe dividirse en:
- 3B1: conexión TLS, autenticación, carpetas, read-only select, errores y cleanup;
- 3B2: UID search, fetch selectivo, parsing MIME, normalización de body y attachment metadata.

## 2. Decisiones ya cerradas

No reabrir:
- IMAPClient;
- TLS obligatorio;
- usuario + provider-approved/app password desde CredentialStore;
- no retries dentro del adapter;
- allowlist configurable;
- select read-only;
- UIDVALIDITY expuesto pero no persistido;
- search ALL/SINCE;
- no RFC822/BODY[] completo;
- plain text preferido, HTML fallback con stdlib;
- límite max_body_bytes;
- attachments metadata-only;
- typed exceptions;
- fake-only tests;
- no persistence/sync/threading/scheduler.

## 3. API objetivo

El plan debe concretar:
- dataclasses inmutables:
  - MailboxFolder
  - SelectedMailbox
  - AttachmentMetadata
  - FetchedMessage
- ReadOnlyIMAPAdapter:
  - connect()
  - disconnect()
  - context manager si procede
  - list_folders()
  - allowed_folders()
  - select_read_only()
  - search_uids()
  - fetch_messages()
- excepciones:
  - IMAPAdapterError
  - IMAPCredentialMissingError
  - IMAPAuthenticationError
  - IMAPConnectionError
  - IMAPProtocolError
  - IMAPFolderNotAllowedError
  - IMAPFolderUnavailableError
  - IMAPMessageParseError

## 4. Scope Lock máximo

Solo:

```text
app/integrations/__init__.py
app/integrations/imap_adapter.py
test/test_imap_adapter.py
```

No modificar ningún otro archivo.

## 5. Requisitos de seguridad

- ninguna red real en tests;
- ningún keyring real;
- ningún secreto en logs/excepciones;
- no persistencia;
- no raw MIME retenido;
- no attachment bytes;
- no métodos IMAP mutantes;
- no login si falta credencial;
- cleanup seguro tras fallo parcial.

## 6. 3B1 debe planificar

- constructor e inyección de client_factory;
- obtención de secreto;
- IMAPClient(host, port, ssl=True);
- login;
- mapeo seguro de errores;
- logout;
- list_folders;
- allowlist;
- readonly select;
- UIDVALIDITY/capabilities;
- tests focales.

## 7. 3B2 debe planificar

- search_uids(ALL/SINCE);
- validación de UID;
- campos FETCH exactos;
- nunca full-message fetch;
- elección text/plain vs text/html;
- decoding/charset;
- HTMLParser stdlib;
- bounded body fetch;
- content_truncated;
- body_size_bytes;
- attachment metadata;
- malformed message behavior;
- tests focales.

## 8. Salida

Crear únicamente:

`docs/plans/implementation-phase-3b-plan.md`

Status:
- READY FOR APPROVAL
- o STOPPED FOR DECISION

Debe incluir:
- implementation order;
- contracts exactos;
- error mapping;
- fake client contract;
- test matrix;
- STOP conditions;
- Definition of Done;
- Scope Lock por 3B1 y 3B2.

## 9. Completion protocol

Commit:
`Plan phase 3B read-only IMAP adapter`

Push solo a `origin/codex-work`.

No tocar `main`.
