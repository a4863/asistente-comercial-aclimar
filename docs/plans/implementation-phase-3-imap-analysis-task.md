# Phase 3 Analysis Task — Outlook IMAP Integration

**Estado:** Approved for Analyze
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Objetivo

Analizar la primera integración real del asistente comercial con la cuenta corporativa de Outlook mediante IMAP.

Cuenta objetivo configurada por el usuario:
- `alexllopez@aclimar.com`

La cuenta se usa desde Outlook Desktop, pero la integración del asistente debe ser IMAP directa, sin depender de Outlook Desktop internamente.

No implementar código en esta tarea.

## 2. Fuentes autoritativas

Revisar:

- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- Fase 2A y 2B ya aceptadas
- `app/persistence/models.py`
- `app/persistence/repositories.py`

## 3. Alcance funcional esperado

La integración IMAP debe permitir, como mínimo:

1. configurar una única cuenta corporativa;
2. conectar mediante IMAP seguro;
3. leer carpetas existentes;
4. sincronizar mensajes de forma incremental;
5. persistir identidad estable del mensaje y observaciones;
6. reconstruir threads usando, por prioridad:
   - Message-ID
   - In-Reply-To
   - References
   - subject solo como fallback secundario;
7. conservar contenido suficiente para posterior análisis;
8. detectar mensajes nuevos/modificados/eliminados del origen;
9. usar checkpoints e idempotencia ya existentes;
10. aislar fallos sin corromper el estado local;
11. soportar catch-up tras desconexión;
12. no enviar mensajes;
13. no mover mensajes todavía;
14. no crear borradores todavía;
15. no descargar/persistir attachments automáticamente.

## 4. Seguridad

Credenciales:
- no código;
- no Git;
- no SQLite;
- no logs;
- preferir Windows Credential Manager/keyring según arquitectura aprobada.

TLS obligatorio.

Contenido remoto no confiable.

No enviar contenido a IA remota en esta fase salvo que la documentación aprobada lo exija explícitamente; esta fase debe centrarse en ingestión/sincronización.

## 5. Decisiones que el análisis debe cerrar o elevar

Determinar:

1. librería IMAP exacta dentro del stack aprobado;
2. modelo de configuración no secreta;
3. almacenamiento de credenciales;
4. estrategia de conexión/reintento;
5. selección de carpetas;
6. mecanismo incremental:
   - UID
   - UIDVALIDITY
   - MODSEQ/CONDSTORE si aplica;
7. qué identificadores forman la identidad estable;
8. cómo mapear mensaje -> SourceRecord/SourceObservation;
9. cómo representar message metadata y body sin duplicar innecesariamente;
10. threading;
11. borrados/movimientos detectados en origen;
12. checkpoints por cuenta/carpeta;
13. idempotencia;
14. formato de errores y retry policy;
15. límites de tamaño;
16. HTML/text/plain;
17. attachments: metadata sí/no, bytes no;
18. repository/service boundaries;
19. tests con IMAP fake/mock; sin red real;
20. Scope Lock exacto de archivos;
21. si la integración debe dividirse en subfases pequeñas.

## 6. Prohibiciones

READ-ONLY salvo el artefacto de análisis.

No:
- implementar IMAP;
- tocar credenciales reales;
- conectarse a la cuenta real;
- instalar dependencias;
- modificar documentación aprobada;
- crear migraciones;
- tocar `main`;
- enviar/mover/borrar correos;
- crear drafts;
- implementar AI analysis.

Si hay dos o más interpretaciones razonables sobre autenticación, UID/UIDVALIDITY, retención de bodies, threading o eliminación: **STOP** y documentar la decisión pendiente.

## 7. Salida obligatoria

Crear únicamente:

`docs/plans/implementation-phase-3-imap-analysis.md`

Debe incluir:

- Status: READY FOR APPROVAL o STOPPED FOR DECISION;
- architecture/data-flow;
- account/config design;
- credential strategy;
- sync/checkpoint strategy;
- message identity strategy;
- threading strategy;
- deletion/move semantics;
- persistence mapping to 2A/2B;
- error/retry model;
- test matrix;
- proposed subphases;
- exact Scope Lock;
- ambiguities/decisions needed;
- risks.

## 8. Completion protocol

Commit:

`Analyze phase 3 Outlook IMAP integration`

Push solo a `origin/codex-work`.

No tocar `main`.
