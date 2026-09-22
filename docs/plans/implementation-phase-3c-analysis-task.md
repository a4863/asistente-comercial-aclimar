# Phase 3C Analysis Task — IMAP Synchronization and Recovery

**Estado:** Approved for Analyze
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Objetivo

Analizar la Fase 3C: sincronización persistente y recuperación entre el adapter IMAP read-only ya aceptado y el modelo de datos aprobado.

Esta fase debe cubrir:
- ingestión incremental;
- persistencia de mensajes y localizaciones;
- SourceRecord / SourceObservation;
- SynchronizationCheckpoint;
- IdempotencyIdentity;
- reconciliación UIDVALIDITY;
- detección conservadora de movimientos/desapariciones;
- reintentos seguros a nivel servicio;
- recuperación tras ejecución parcial;
- auditabilidad técnica suficiente.

No debe implementar todavía:
- threading/conversation reconstruction;
- extracción semántica;
- tareas/compromisos/preguntas;
- IA;
- UI;
- scheduler real;
- movimientos/drafts/sends;
- mutaciones externas.

## 2. Fuentes autoritativas

Revisar:
- `docs/plans/implementation-phase-3-imap-analysis.md`
- `docs/plans/implementation-phase-3-imap-decisions.md`
- `docs/plans/implementation-phase-3a-plan.md`
- `docs/plans/implementation-phase-3b-analysis.md`
- `docs/plans/implementation-phase-3b-plan.md`
- implementación aceptada 3A/3B
- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `app/integrations/imap_adapter.py`
- `docs/data-model.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`

## 3. Decisiones ya aprobadas que no deben reabrirse

### Cursor
- incremental por account + folder + UIDVALIDITY + highest UID;
- cambio de UIDVALIDITY = nuevo namespace + reconciliación de ventana histórica;
- MODSEQ opcional futura, no requerido ahora.

### Identidad
- location identity = account + folder + UIDVALIDITY + UID;
- logical identity = normalized Message-ID cuando exista;
- un move no crea conceptualmente un email nuevo;
- sin Message-ID: conservar ocurrencia; fingerprint conservador solo para idempotencia si se justifica, nunca merge agresivo.

### Retención
- desaparecer de una carpeta != borrado;
- si aparece en otra carpeta sincronizada, tratar como cambio de localización/move;
- solo marcar unavailable/deleted-at-source tras reconciliación suficiente;
- conservar historial local.

### Contenido
- persistir metadata/body normalizado/attachment metadata;
- no raw MIME;
- no attachment bytes.

## 4. Preguntas que el análisis debe cerrar o elevar

1. servicio exacto de sincronización;
2. boundary entre adapter y persistence;
3. cómo crear/reusar SourceRecord;
4. cómo registrar SourceObservation por ejecución;
5. cómo mapear FetchedMessage -> EmailMessage;
6. cómo crear/reusar IMAPMessageLocation;
7. algoritmo exacto de IdempotencyIdentity;
8. qué significa highest_uid cuando hay huecos;
9. cuándo avanzar checkpoint;
10. comportamiento si una transacción parcial falla;
11. atomicidad por mensaje vs por carpeta;
12. estrategia para primera sync;
13. estrategia para sync incremental;
14. ventana de reconciliación tras UIDVALIDITY reset;
15. cómo detectar moves entre carpetas sincronizadas;
16. cuándo location pasa active -> unavailable;
17. umbral de “sufficient reconciliation”;
18. si hace falta nuevo estado/campo/modelo o puede resolverse con los existentes;
19. qué ocurre con Message-ID duplicado real;
20. mensajes sin Message-ID;
21. reaparición de location previamente unavailable;
22. attachment metadata replace/upsert;
23. body/content updates sobre misma logical identity;
24. qué metadata se considera authoritative vs observation;
25. error handling/retry;
26. transaction boundaries;
27. audit event exacto si aplica;
28. test matrix;
29. exact Scope Lock;
30. si conviene dividir 3C en subfases.

## 5. Guardarraíles

READ-ONLY salvo artefacto de análisis.

No:
- red real;
- credenciales reales;
- cambios schema/migraciones salvo que el análisis demuestre que son imprescindibles y entonces STOP;
- código de implementación;
- threading;
- IA;
- scheduler real;
- mailbox mutation;
- UI;
- main;
- CRM/Calendar.

## 6. Criterio de STOP

Si los modelos actuales no permiten representar de forma segura:
- múltiples localizaciones del mismo email;
- reset UIDVALIDITY;
- unavailable/reactivation;
- checkpoints independientes por folder;
- idempotencia sin duplicados;
- recuperación tras fallo parcial;

entonces STOPPED FOR DECISION con alternativas concretas antes de implementar.

## 7. Salida

Crear únicamente:

`docs/plans/implementation-phase-3c-analysis.md`

Status:
- READY FOR APPROVAL
- o STOPPED FOR DECISION

Debe incluir:
- service API;
- transaction model;
- source/observation lifecycle;
- identity/idempotency algorithm;
- checkpoint semantics;
- initial sync;
- incremental sync;
- UIDVALIDITY recovery;
- move/unavailable reconciliation;
- reactivation;
- duplicate Message-ID policy;
- missing Message-ID policy;
- retry/recovery behavior;
- persistence calls required;
- schema gap analysis;
- test matrix;
- proposed subphases;
- exact Scope Lock;
- open decisions.

## 8. Completion protocol

Commit:
`Analyze phase 3C IMAP synchronization and recovery`

Push solo a `origin/codex-work`.

No tocar `main`.
