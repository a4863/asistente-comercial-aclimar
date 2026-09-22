# Phase 3B2 Correction Task — IMAP FETCH Response Keys and BODYSTRUCTURE Extensions

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Problemas confirmados

La corrección anterior ya acepta IMAPClient BodyData tuple/list, pero quedan dos incompatibilidades con respuestas IMAP reales:

### A. FETCH response keys

El selector solicitado no tiene por qué coincidir literalmente con la clave devuelta.

Ejemplos reales:
- solicitar `BODY.PEEK[HEADER]` puede devolver clave `BODY[HEADER]`;
- solicitar `BODY.PEEK[1]` devuelve `BODY[1]`;
- solicitar parcial `BODY.PEEK[1]<0.65>` puede devolver clave `BODY[1]<0>`.

Por tanto no se debe buscar únicamente la clave exacta solicitada.

### B. BODYSTRUCTURE extension positions

La posición de campos de extensión depende del media type.

Para partes `text/*`, después de octets aparece line count antes de MD5/disposition.
Para partes no-text simples, no existe line count y disposition aparece una posición antes.

El parser actual usa el mismo índice de disposition para todos los tipos y puede perder attachments text/*.

## 2. Objetivo

Corregir únicamente:
- resolución robusta de response keys para BODY/BODY.PEEK y partial fetch;
- extracción type-aware de disposition / filename / metadata en BodyData;
- tests representativos.

## 3. Archivos autorizados

Solo:

```text
app/integrations/imap_adapter.py
test/test_imap_adapter.py
```

## 4. FETCH key normalization

Implementar helper interno que permita obtener de un item de fetch:

### Header
Solicitud:
`BODY.PEEK[HEADER]`

Aceptar respuesta equivalente:
- `BODY[HEADER]`
- bytes o str
- tolerar selector PEEK exacto solo como compatibilidad de fake, pero los tests principales deben usar la clave real sin PEEK.

### MIME part
Solicitud:
`BODY.PEEK[1.2.MIME]`

Aceptar:
- `BODY[1.2.MIME]`
- bytes o str

### Partial body
Solicitud:
`BODY.PEEK[1.2]<0.N>`

Aceptar:
- `BODY[1.2]<0>`
- bytes o str
- no depender de que la longitud N aparezca en la response key.

No aceptar accidentalmente:
- BODY[] whole message;
- otra part;
- attachment part no seleccionada.

## 5. BODYSTRUCTURE type-aware parsing

Mantener BodyData tuple/list.

Para single part:
- type = index 0
- subtype = index 1
- params = index 2
- content-id = index 3
- encoding = index 5
- octets = index 6

Después:
- si media_type == text:
  - line count en index 7
  - MD5/disposition/ext fields después;
  - disposition debe extraerse de la posición correcta para text BODYSTRUCTURE.
- si media_type != text y no message/rfc822:
  - no line-count;
  - disposition/ext fields comienzan una posición antes.

El parser debe manejar ausencia de extensiones sin inventar valores.

Cubrir específicamente:
- text/plain inline;
- text/plain attachment con filename/disposition;
- application/pdf attachment;
- multipart mixed/alternative;
- nested paths.

## 6. Tests obligatorios

Actualizar los fakes para que las respuestas principales usen claves IMAP reales:

- top header response: `b"BODY[HEADER]"`;
- MIME part: `b"BODY[1.MIME]"` o nested equivalent;
- partial body: `b"BODY[1]<0>"`, aunque la request fue `BODY.PEEK[1]<0.N>`.

Verificar:
- header parse funciona con key sin PEEK;
- selected text body funciona con partial key `<0>`;
- MIME header key sin PEEK;
- part 1.2 funciona;
- no match con BODY[] whole message;
- text/plain attachment se detecta como attachment y no se elige como body;
- PDF attachment metadata sigue correcta;
- filename desde disposition params y desde content-type name fallback;
- no attachment body fetch.

## 7. No cambiar

- API pública;
- config;
- credentials;
- pyproject;
- persistence;
- main;
- networking;
- retry behavior.

## 8. Validación

Ejecutar:

`python -m pytest test/test_imap_adapter.py`

Después:

`python -m pytest`

## 9. Completion protocol

Commit:
`Fix phase 3B2 IMAP fetch response compatibility`

Push solo a `origin/codex-work`.

No tocar `main`.
