# Phase 3B1 Implementation Task — IMAP Connection and Folder Boundary

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3b-plan.md`

## 1. Objetivo

Implementar únicamente la frontera de conexión IMAP read-only:
- contratos/dataclasses;
- excepciones tipadas;
- conexión TLS;
- autenticación vía CredentialStore;
- cleanup;
- listado de carpetas;
- allowlist;
- selección read-only;
- UIDVALIDITY/capabilities.

No implementar search/fetch/MIME todavía.

## 2. Archivos autorizados

Solo:

```text
app/integrations/__init__.py
app/integrations/imap_adapter.py
test/test_imap_adapter.py
```

No modificar ningún otro archivo.

## 3. Contratos públicos

Definir dataclasses inmutables:
- MailboxFolder(name, delimiter, flags)
- SelectedMailbox(name, uidvalidity, capabilities)

También puede declarar ya, sin implementación de fetch:
- AttachmentMetadata
- FetchedMessage

Definir excepciones:
- IMAPAdapterError
- IMAPCredentialMissingError
- IMAPAuthenticationError
- IMAPConnectionError
- IMAPProtocolError
- IMAPFolderNotAllowedError
- IMAPFolderUnavailableError
- IMAPMessageParseError

## 4. ReadOnlyIMAPAdapter

Constructor:
`ReadOnlyIMAPAdapter(settings, credential_store, client_factory=IMAPClient)`

Métodos autorizados en 3B1:
- connect()
- disconnect()
- __enter__()
- __exit__()
- list_folders()
- allowed_folders()
- select_read_only(folder_name)

No implementar aún:
- search_uids()
- fetch_messages()

Pueden existir stubs que lancen NotImplementedError solo si el plan/test contract lo necesita; preferible no exponer comportamiento incompleto.

## 5. connect()

Secuencia obligatoria:
1. pedir secreto a CredentialStore usando credential_service + credential_account;
2. si None o vacío -> IMAPCredentialMissingError;
3. no crear cliente ni llamar login;
4. crear cliente con:
   - settings.host
   - port=settings.port
   - ssl=True
5. login(settings.account, secret)
6. no almacenar el secreto como atributo;
7. no loggear secreto;
8. mapear fallos a excepción tipada segura.

No retry.

## 6. disconnect()

- logout solo si existe cliente;
- tolerar error de logout sin propagar si es cleanup-only;
- limpiar siempre referencia interna;
- seguro tras conexión parcial fallida;
- context manager delega en disconnect().

## 7. Folders

### list_folders()
- requiere conexión;
- mapear `client.list_folders()` a tuple[MailboxFolder,...];
- decode bytes con replacement;
- flags y delimiter normalizados a strings;
- no conservar raw protocol response.

### allowed_folders()
- intersección exacta entre folders descubiertas y settings.folder_allowlist;
- preservar orden de allowlist si es razonable;
- no crear folders.

### select_read_only(folder_name)
- rechazar primero si no está en allowlist -> IMAPFolderNotAllowedError;
- si está allowlisted pero no existe -> IMAPFolderUnavailableError;
- llamar `client.select_folder(folder_name, readonly=True)`;
- extraer UIDVALIDITY positivo si existe; malformed/absent -> None;
- capabilities como tuple de strings seguros;
- no persistir nada.

## 8. Seguridad

- no red real en tests;
- no keyring real;
- no logs con secretos;
- no raw server response en excepciones;
- no IMAP mutations;
- no persistence;
- no retries;
- no main/routes/UI.

## 9. Tests obligatorios

En `test/test_imap_adapter.py` cubrir:
- factory recibe host/port/ssl=True;
- login recibe account + fake secret;
- missing secret -> no factory call;
- empty secret -> no factory call;
- authentication failure -> IMAPAuthenticationError;
- factory/transport failure -> IMAPConnectionError;
- generic protocol failure -> IMAPProtocolError;
- exception text no contiene fake secret;
- disconnect successful;
- disconnect after partial failure;
- context manager cleanup;
- list_folders mapping flags/delimiter/name;
- bytes malformed decode replacement;
- allowed_folders intersection;
- non-allowlisted select rejected without select call;
- allowlisted missing folder rejected without select call;
- select_folder(..., readonly=True);
- UIDVALIDITY valid -> int;
- invalid/missing UIDVALIDITY -> None;
- capabilities normalized tuple;
- adapter exposes no mutating mailbox method.

## 10. Validación

Ejecutar:

`python -m pytest test/test_imap_adapter.py`

Después:

`python -m pytest`

Ambas deben quedar verdes.

## 11. STOP conditions

STOP si necesitas:
- modificar config.py;
- modificar credentials.py;
- modificar pyproject.toml;
- tocar persistencia/migraciones/repositorios;
- abrir red real;
- usar keyring real;
- añadir dependencia;
- implementar search/fetch/MIME;
- tocar main.

## 12. Completion protocol

Commit:
`Implement phase 3B1 IMAP connection boundary`

Push solo a `origin/codex-work`.

No tocar `main`.
