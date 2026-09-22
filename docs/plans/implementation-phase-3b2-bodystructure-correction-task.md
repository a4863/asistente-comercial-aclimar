# Phase 3B2 Correction Task — Real IMAPClient BODYSTRUCTURE Contract

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`

## 1. Problema confirmado

La implementación 3B2 actual modela `BODYSTRUCTURE` como diccionarios sintéticos.

IMAPClient 4.x devuelve `BODYSTRUCTURE` como `BodyData`, una estructura tuple/list anidada. El parser actual `_walk_bodystructure()` rechazaría esa respuesta real.

Esto invalida la compatibilidad del adapter con IMAPClient aunque los tests actuales estén verdes.

## 2. Objetivo

Corregir únicamente:
- parsing de BODYSTRUCTURE para el formato real de IMAPClient;
- fakes/tests para usar estructuras representativas del contrato real;
- mantener todas las garantías de 3B2.

## 3. Archivos autorizados

Solo:

```text
app/integrations/imap_adapter.py
test/test_imap_adapter.py
```

No modificar ningún otro archivo.

## 4. Contrato IMAPClient a soportar

El parser debe aceptar la forma `BodyData`/tuple/list que devuelve IMAPClient.

Características relevantes:
- single-part: tuple-like; primer elemento = major media type;
- multipart: primer elemento = lista de partes hijas;
- las partes hijas pueden estar anidadas;
- strings protocolarios pueden llegar como bytes;
- BODYSTRUCTURE contiene media type/subtype, parámetros, content-id, encoding, octets y disposition según el tipo de parte.

No convertir BODYSTRUCTURE a un dict ficticio fuera del adapter.

## 5. Requisitos funcionales

Mantener:
- localizar recursivamente text/plain;
- fallback text/html solo si plain no existe;
- extraer metadata de attachments;
- part path correcto (1, 1.1, 1.2, 2, etc.);
- jamás fetch de attachment body;
- jamás whole-message fetch;
- size declarado usado para truncation;
- malformed structure -> excepción segura tipada.

## 6. Tests obligatorios

Reemplazar/añadir fakes con BODYSTRUCTURE tuple/list realista para:
- single-part text/plain;
- multipart/alternative html + plain;
- multipart/mixed con nested alternative + PDF attachment;
- content-disposition attachment;
- filename en parámetros/disposition cuando aplique;
- content-id;
- declared size;
- malformed BodyData/tuple;
- plain preference;
- HTML fallback;
- part path exacto;
- attachment body no solicitado.

Los tests no deben usar el dict simplificado anterior como única representación.

## 7. Verificación adicional

Revisar también que las claves devueltas por fake `fetch()` reflejen razonablemente las claves que IMAPClient devuelve para los campos solicitados, incluyendo bytes/string normalization ya soportada por `_response_value`.

## 8. No cambiar

- conexión/auth 3B1;
- config;
- credentials;
- persistence;
- dependencies;
- main;
- API pública salvo helpers internos estrictamente necesarios;
- no red real.

## 9. Validación

Ejecutar:

`python -m pytest test/test_imap_adapter.py`

Después:

`python -m pytest`

## 10. Completion protocol

Commit:
`Fix phase 3B2 IMAPClient BODYSTRUCTURE parsing`

Push solo a `origin/codex-work`.

No tocar `main`.
