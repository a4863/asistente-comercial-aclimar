# Phase 3B2 Implementation Task — IMAP Read-only Retrieval and MIME Normalization

**Estado:** Approved for Implement
**Fecha:** 2026-09-22
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3b-plan.md`

## 1. Objetivo

Implementar únicamente la lectura read-only de mensajes ya seleccionados:
- búsqueda UID;
- fetch selectivo;
- parsing de headers;
- elección text/plain / text/html;
- normalización;
- límite de body;
- attachment metadata.

No persistir nada.

## 2. Archivos autorizados

Solo:

```text
app/integrations/imap_adapter.py
test/test_imap_adapter.py
```

No modificar ningún otro archivo.

## 3. Métodos a implementar

### search_uids(since: date | None) -> tuple[int, ...]

Requisitos:
- requiere conexión;
- requiere mailbox seleccionada previamente;
- since=None -> ALL;
- since!=None -> SINCE usando date compatible con IMAPClient;
- devolver solo UIDs positivos como ints;
- UID inválido/malformado -> IMAPProtocolError;
- no calcular initial_window_days aquí;
- no persistir checkpoints.

### fetch_messages(uids: Iterable[int]) -> tuple[FetchedMessage, ...]

Requisitos:
- validar UIDs positivos antes de llamar al cliente;
- nunca fetch full-message;
- nunca fetch attachment bodies;
- obtener:
  - BODY.PEEK[HEADER]
  - BODYSTRUCTURE
  - MIME headers del text part elegido
  - payload parcial del text part elegido

## 4. Fetch prohibido

No usar:
- RFC822
- BODY[]
- BODY.PEEK[] completo
- RFC822.TEXT
- attachment part body
- cualquier whole-message equivalent

Los tests deben auditar las claves/fields pedidos al fake.

## 5. MIME y headers

Usar solo stdlib:
- email
- email.parser.BytesParser
- policy=default
- html.parser.HTMLParser

Extraer:
- normalized_message_id
- sender_address
- recipient_addresses
- subject
- sent_at
- in_reply_to
- references_header

Reglas:
- headers malformados deben normalizarse o producir IMAPMessageParseError sin raw response;
- Message-ID ausente permitido;
- recipients tuple;
- no thread merge.

## 6. BODYSTRUCTURE

Recorrer recursivamente.

Debe:
- identificar candidatos text/plain;
- si no existe plain, text/html;
- identificar attachment metadata;
- no solicitar bytes de attachment;
- soportar multipart anidado en tests.

Si BODYSTRUCTURE es inválido de forma que no puede interpretarse de forma segura -> IMAPProtocolError o IMAPMessageParseError según el punto de fallo.

## 7. Normalización body

### text/plain
- normalizar line endings;
- whitespace conservador;
- no alterar semántica comercial.

### text/html fallback
- HTMLParser stdlib;
- ignorar script/style;
- convertir boundaries razonables a newlines;
- entidades HTML a texto;
- devolver solo texto normalizado;
- nunca raw HTML.

## 8. Size guard

- no solicitar más de max_body_bytes + 1 bytes del text part;
- devolver contenido como máximo equivalente al límite aprobado;
- content_truncated=True si:
  - BODYSTRUCTURE declara size > max_body_bytes; o
  - payload recuperado supera max_body_bytes;
- body_size_bytes = número de bytes fuente retenidos/bounded según plan;
- no body -> normalized_body=None, body_size_bytes=0.

## 9. AttachmentMetadata

Extraer únicamente:
- part_index
- filename
- media_type
- byte_size
- content_id
- disposition

Nunca:
- payload
- bytes
- raw MIME

## 10. Error handling

- search/fetch sin conexión -> IMAPConnectionError;
- search/fetch sin mailbox seleccionada -> IMAPProtocolError segura;
- invalid UID input -> IMAPProtocolError sin llamada fetch;
- malformed UID server result -> IMAPProtocolError;
- malformed individual message -> IMAPMessageParseError;
- no exception chain con raw/sensitive cause;
- no secreto/body/raw server response en mensaje de error.

## 11. Tests obligatorios

Añadir en `test/test_imap_adapter.py` cobertura para:
- ALL search;
- SINCE search;
- search requiere selected mailbox;
- malformed server UID;
- invalid requested UID blocks fetch;
- fetch fields audit;
- no whole-message fetch;
- no attachment-body fetch;
- encoded subject/sender;
- absent Message-ID;
- In-Reply-To/References;
- recipients;
- parsed date;
- plain preferred over HTML;
- HTML-only fallback;
- script/style ignored;
- unknown charset replacement;
- no-text message;
- nested multipart attachment metadata;
- below/equal/above max_body_bytes;
- content_truncated;
- body_size_bytes;
- malformed message -> IMAPMessageParseError;
- malicious-looking content remains inert text;
- returned dataclasses contain no raw MIME/attachment bytes.

## 12. Seguridad

- fake-only;
- sin red;
- sin keyring real;
- sin persistence;
- sin logs de body/secret;
- sin mutations IMAP;
- sin retries;
- sin AI;
- sin main/routes/UI.

## 13. Validación

Ejecutar:

`python -m pytest test/test_imap_adapter.py`

Después:

`python -m pytest`

Ambas deben quedar verdes.

## 14. STOP conditions

STOP si necesitas:
- modificar config.py;
- modificar credentials.py;
- modificar pyproject.toml;
- tocar persistence/migrations/repositories;
- añadir dependencia;
- fetch whole-message;
- fetch attachment body;
- abrir red real;
- tocar main.

## 15. Completion protocol

Commit:
`Implement phase 3B2 IMAP retrieval and MIME normalization`

Push solo a `origin/codex-work`.

No tocar `main`.
