# Phase 3A2 Implementation Task — IMAP Configuration and Credential Boundary

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3a-plan.md`

## 1. Objetivo

Implementar únicamente:
- configuración IMAP no secreta;
- frontera de credenciales mediante keyring;
- declaración de dependencias aprobadas;
- tests correspondientes.

No implementar conexión IMAP ni red.

## 2. Archivos autorizados

Solo:

```text
pyproject.toml
app/config.py
app/security/credentials.py
test/test_config.py
test/test_credentials.py
```

No modificar ningún otro archivo.

## 3. Dependencias

Añadir únicamente las aprobadas:
- IMAPClient
- keyring

No usar IMAPClient todavía en código.

## 4. Configuración IMAP

Extender Settings con una configuración IMAP inmutable que contenga únicamente datos no secretos:

- host
- port (default 993)
- account / mailbox user
- account_scope
- folder_allowlist (default INBOX, Sent)
- initial_window_days (default 30)
- max_body_bytes (default 2 * 1024 * 1024)
- credential_service
- credential_account

Reglas:
- host no vacío
- port > 0
- account no vacío
- account_scope no vacío
- allowlist sin entradas vacías ni duplicadas
- initial_window_days >= 0
- max_body_bytes > 0
- no secretos en TOML

## 5. Rechazo explícito de secretos en TOML

El loader debe rechazar claves IMAP secretas o equivalentes, incluyendo al menos:
- password
- app_password
- secret
- token
- access_token
- refresh_token

No ignorarlas silenciosamente.

## 6. Credential boundary

Crear:

`app/security/credentials.py`

Interfaz mínima:

```text
CredentialStore.get_secret(service: str, account: str) -> str | None
KeyringCredentialStore
```

Reglas:
- KeyringCredentialStore delega solo en `keyring.get_password(service, account)`
- no setter
- no cache
- no logs
- no persistencia
- no UI
- no exposición por rutas
- no acceso real en tests

## 7. Tests obligatorios

### test_config.py
Cubrir:
- defaults 993 / INBOX+Sent / 30 / 2MB
- config válida
- host vacío rechazado
- port <= 0 rechazado
- account vacío rechazado
- account_scope vacío rechazado
- allowlist vacía/duplicada/entrada vacía rechazada según reglas aprobadas
- initial_window_days negativo rechazado
- max_body_bytes <= 0 rechazado
- claves secretas rechazadas
- validación localhost existente sigue verde

### test_credentials.py
Cubrir:
- adapter llama a keyring.get_password(service, account)
- retorno de secreto falso solo como valor de retorno
- missing credential -> None
- no llamadas reales a Windows Credential Manager
- no setter
- no logging/caching/persistencia

## 8. Validación

Ejecutar:

`python -m pytest test/test_config.py test/test_credentials.py`

Después:

`python -m pytest`

Ambas deben quedar verdes.

## 9. STOP conditions

STOP si necesitas:
- tocar models.py
- tocar migration 0004
- tocar repositories.py
- tocar main.py
- abrir red
- importar/crear cliente IMAP
- acceder a credenciales reales
- añadir otra dependencia
- crear UI/rutas
- almacenar secretos

## 10. Completion protocol

Commit:

`Implement phase 3A2 IMAP config and credential boundary`

Push solo a `origin/codex-work`.

No tocar `main`.
