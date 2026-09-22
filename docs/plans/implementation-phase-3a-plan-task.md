# Phase 3A Plan Task — Email Data, Configuration and Credential Boundary

**Estado:** Approved for Plan
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Objetivo

Preparar el plan de implementación de Fase 3A.

3A debe limitarse a:
- modelo físico de correo;
- migración correspondiente;
- configuración IMAP no secreta;
- frontera de credenciales vía keyring/Windows Credential Manager;
- tests unitarios/fake.

No conectar la cuenta real ni implementar todavía sincronización IMAP.

## 2. Fuentes obligatorias

Revisar:
- `docs/plans/implementation-phase-3-imap-analysis.md`
- `docs/plans/implementation-phase-3-imap-decisions.md`
- documentación funcional/técnica aprobada;
- persistencia actual 2A/2B;
- config actual;
- dependencias actuales.

## 3. Decisiones cerradas

No reabrir:
- D1 usuario + app/provider password en keyring;
- D2 UIDVALIDITY + UID;
- D3 identidad lógica + ubicación IMAP separada;
- D4 EmailMessage físico, sin raw MIME;
- D5 allowlist, Inbox + Sent por defecto;
- D6 move != delete;
- D7 plain-first, HTML fallback, 2 MB, attachment metadata only.

## 4. El plan debe definir

1. entidades/tablas exactas necesarias en 3A;
2. relación EmailMessage -> SourceRecord;
3. representación de ubicaciones IMAP por carpeta/UIDVALIDITY/UID;
4. attachment metadata;
5. campos de content_truncated;
6. constraints/uniques;
7. si hace falta migration `0004`;
8. cambios exactos en Settings/TOML;
9. referencia lógica a credencial sin secreto;
10. interfaz/adaptador mínimo de CredentialStore;
11. incorporación de dependencias `IMAPClient` y `keyring` si procede en 3A;
12. tests sin red real;
13. Scope Lock exacto;
14. orden de implementación por bloques;
15. STOP conditions;
16. Definition of Done.

## 5. Restricciones

- no IMAP real;
- no conexión de red;
- no mailbox access;
- no sync;
- no threading;
- no scheduler;
- no UI;
- no AI;
- no SMTP;
- no move/draft/send;
- no tocar main salvo que el plan demuestre que es estrictamente necesario; preferir no tocarlo.

## 6. Salida

Crear únicamente:

`docs/plans/implementation-phase-3a-plan.md`

Status:
- READY FOR APPROVAL, o
- STOPPED FOR DECISION.

## 7. Completion protocol

Commit:
`Plan phase 3A email data and credential foundation`

Push solo a `origin/codex-work`.

No tocar `main`.
