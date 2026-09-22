# Phase 3 IMAP Decisions

**Fecha:** 2026-09-22
**Estado:** APPROVED

## D1 — Authentication

**Decisión:** B — usuario + provider-approved password/app password.

- Usuario configurado: `alexllopez@aclimar.com`.
- El secreto se almacena únicamente mediante `keyring` respaldado por Windows Credential Manager.
- No almacenar secretos en código, Git, TOML, SQLite, logs, auditoría ni respuestas web.
- El diseño debe permitir sustituir el mecanismo de autenticación en el futuro sin cambiar el modelo de correo.

## D2 — Incremental cursor

**Decisión:** A — `UIDVALIDITY + UID`.

- Checkpoint por cuenta/carpeta.
- Persistir `UIDVALIDITY` y mayor UID procesado.
- Si cambia `UIDVALIDITY`, tratar la carpeta como nuevo namespace y reconciliar la ventana histórica configurada.
- MODSEQ/CONDSTORE podrá añadirse después como optimización; no es requisito MVP.

## D3 — Source identity across folders

**Decisión:** C — identidad de ubicación + identidad lógica.

Ubicación IMAP:
- cuenta
- carpeta
- UIDVALIDITY
- UID

Identidad lógica:
- Message-ID normalizado cuando exista.

Reglas:
- mover un mensaje de carpeta no crea conceptualmente un nuevo correo;
- si falta Message-ID, conservar la ocurrencia IMAP;
- puede existir una huella técnica conservadora para idempotencia, pero no se usa para fusionar threads automáticamente;
- duplicados o Message-ID ausente no autorizan merges agresivos.

## D4 — Physical email representation and retention

**Decisión:** aprobada.

Crear representación física `EmailMessage` enlazada a `SourceRecord`.

Persistir:
- sender/recipients;
- subject;
- sent/received timestamps;
- Message-ID;
- In-Reply-To;
- References;
- carpeta/ubicación técnica mediante estructura separada o campos aprobados;
- texto normalizado;
- metadata de adjuntos.

No persistir:
- MIME/raw completo;
- bytes de adjuntos.

El contenido queda local en SQLite sujeto a las reglas de retención aprobadas.

## D5 — Folder selection

**Decisión:** allowlist configurable.

Por defecto:
- Inbox
- Sent

Proceso:
- descubrir todas las carpetas existentes;
- sincronizar solo allowlist;
- permitir añadir carpetas existentes por configuración sin cambio de código;
- no incluir Spam/Junk/Trash por defecto.

## D6 — Deletion and move semantics

**Decisión:** distinguir ubicación de mensaje lógico.

- desaparecer de una carpeta no equivale a borrado;
- si el mensaje lógico aparece en otra carpeta sincronizada, registrar cambio de ubicación;
- solo marcar como no disponible/borrado en origen cuando no aparezca en ninguna ubicación sincronizada tras reconciliación suficiente;
- no borrar silenciosamente el histórico local.

## D7 — MIME normalization and size limits

**Decisión:** aprobada.

- preferir `text/plain`;
- si no existe, convertir `text/html` a texto normalizado;
- si existen ambos, conservar como canónico plain text y no duplicar HTML;
- máximo de body procesado por mensaje: 2 MB;
- si se supera, guardar metadata y marcar `content_truncated`;
- adjuntos: solo metadata disponible (nombre, MIME type, tamaño, content-id/disposition), nunca bytes.
