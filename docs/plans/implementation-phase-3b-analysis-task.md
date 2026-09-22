# Phase 3B Analysis Task — Read-only IMAP Adapter

**Estado:** Approved for Analyze
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Objetivo

Analizar el adapter IMAP read-only de la Fase 3B.

Esta fase debe cubrir solo:
- conexión segura IMAP;
- autenticación con CredentialStore;
- descubrimiento/listado de carpetas existentes;
- selección de carpetas permitidas;
- fetch read-only de metadata/body;
- parsing MIME;
- normalización técnica del mensaje;
- metadata de adjuntos sin bytes;
- manejo de errores y desconexión.

No debe implementar todavía sincronización persistente, checkpoints, repositorios de correo, threading ni scheduler.

## 2. Fuentes autoritativas

Revisar:
- `docs/plans/implementation-phase-3-imap-analysis.md`
- `docs/plans/implementation-phase-3-imap-decisions.md`
- `docs/plans/implementation-phase-3a-plan.md`
- Fase 3A implementada
- `app/config.py`
- `app/security/credentials.py`
- `app/persistence/models.py`
- documentación funcional/arquitectura/seguridad/testing aprobada.

## 3. Alcance funcional esperado

El adapter futuro debe:
1. usar `IMAPClient`;
2. usar TLS obligatorio;
3. obtener secreto solo vía `CredentialStore`;
4. no loggear secretos;
5. listar carpetas existentes;
6. no crear, renombrar, mover ni borrar carpetas;
7. aplicar allowlist configurada;
8. seleccionar una carpeta en modo read-only;
9. obtener capacidades/UIDVALIDITY cuando proceda;
10. buscar UIDs por ventana/criterio definido;
11. fetch de headers/body necesarios;
12. parsear Message-ID/In-Reply-To/References;
13. extraer sender/recipients/subject/date;
14. preferir text/plain; HTML fallback normalizado;
15. respetar max_body_bytes;
16. devolver `content_truncated`;
17. devolver attachment metadata sin bytes;
18. no persistir nada;
19. no llamar IA;
20. no enviar/mover/draft/delete.

## 4. Preguntas que el análisis debe cerrar o elevar

Determinar:

1. interfaz exacta del adapter;
2. tipos de retorno;
3. lifecycle de conexión;
4. timeout/retry responsibilities;
5. cómo se inyecta CredentialStore;
6. comportamiento si falta secreto;
7. validación de host `imap.invalid` / configuración no preparada;
8. TLS/SSL exacto con IMAPClient;
9. LIST/folder discovery mapping;
10. read-only select;
11. obtención UIDVALIDITY;
12. estrategia de SEARCH para ventana inicial;
13. FETCH fields exactos;
14. parsing con stdlib `email`;
15. charset/decoding;
16. malformed headers;
17. HTML->text: si requiere dependencia nueva o solución stdlib;
18. 2 MB guard semantics;
19. attachment metadata extraction;
20. manejo de BODYSTRUCTURE/parts;
21. error taxonomy;
22. fake/mock strategy sin servidor real;
23. exact Scope Lock;
24. si conviene dividir 3B en subfases.

## 5. Restricciones

READ-ONLY salvo artefacto de análisis.

No:
- red real;
- credenciales reales;
- persistencia;
- migraciones;
- cambios en modelos;
- repositories;
- main;
- scheduler;
- threading;
- sync/checkpoints;
- SMTP;
- mutations IMAP;
- AI;
- nuevas dependencias sin decisión explícita.

Si parsing HTML requiere dependencia adicional, STOP y elevar decisión.

## 6. Salida

Crear únicamente:

`docs/plans/implementation-phase-3b-analysis.md`

Status:
- READY FOR APPROVAL
- o STOPPED FOR DECISION

Debe incluir:
- adapter API;
- connection/auth flow;
- folder discovery;
- read-only selection;
- UID/search/fetch design;
- MIME parsing;
- normalization;
- body limit;
- attachment metadata;
- error model;
- security considerations;
- fake test matrix;
- proposed subphases;
- exact Scope Lock;
- open decisions.

## 7. Completion protocol

Commit:
`Analyze phase 3B read-only IMAP adapter`

Push solo a `origin/codex-work`.

No tocar `main`.
