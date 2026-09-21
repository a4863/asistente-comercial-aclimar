# Phase 1 Focused Correction Task

**Estado:** Approved for Implement
**Fecha:** 2026-09-21
**Baseline:** `58eb7b466dd675673da9a1b98ed53144e608bd68`
**Review:** `docs/plans/implementation-phase-1-review.md`

## 1. Objetivo

Corregir únicamente los hallazgos Major/Minor identificados en la revisión de Fase 1.

No añadir nueva funcionalidad de negocio ni integraciones externas.

---

## 2. Correcciones obligatorias

### A. Integrar Settings en el arranque real

Modificar el arranque para que:

- `create_app()` cargue o reciba `Settings`;
- la configuración validada forme parte del startup real;
- el host permitido siga siendo exclusivamente `127.0.0.1`;
- el test de startup verifique esta integración y no solo el título de la app.

No introducir LAN binding ni override inseguro.

### B. Session/CSRF groundwork funcional

Sustituir el stub actual por groundwork real y testeable apropiado para Phase 1.

Debe:

- generar/gestionar un token CSRF por sesión o mecanismo equivalente seguro;
- permitir validación para futuros POST/mutaciones;
- no introducir todavía endpoints de mutación externa;
- no requerir autenticación multiusuario;
- ser compatible con FastAPI/Jinja2 y localhost-only;
- incluir tests de generación/validación y rechazo de token inválido.

No implementar workflows comerciales.

### C. Audit/logging seguro

Sustituir `record(event: str)` por una interfaz restringida.

Debe:

- aceptar tipos/códigos de evento controlados;
- evitar loguear payload comercial arbitrario;
- evitar secretos;
- permitir campos estructurados seguros/minimizados si hacen falta;
- incluir tests que prueben que no se emiten valores sensibles arbitrarios.

No crear todavía el modelo completo de AuditEvent de negocio.

### D. Persistence/repository isolation

Añadir pruebas reales para:

- `make_session_factory()`;
- base SQLite temporal/aislada;
- sesiones independientes;
- repository boundary mínimo si aplica;
- ausencia de uso de la DB de usuario.

No implementar entidades comerciales.

### E. Test temp isolation y suite verde

Corregir los errores de `tmp_path` en Windows usando un directorio temporal controlado por el proyecto/test suite o una estrategia equivalente segura.

La suite debe terminar completamente verde.

### F. Declarar pytest

Declarar `pytest` en metadata de desarrollo/test apropiada dentro de `pyproject.toml`.

---

## 3. Archivos autorizados

Solo pueden modificarse archivos existentes dentro de este conjunto:

```text
app/main.py
app/config.py
app/audit.py
app/security/session.py
app/persistence/database.py
app/persistence/repositories.py
pyproject.toml
test/conftest.py
test/test_startup.py
test/test_config.py
test/test_migrations.py
test/test_status.py
```

Si para corregir correctamente un hallazgo fuese materialmente necesario tocar otro archivo o crear uno nuevo: **STOP** y reportar antes.

---

## 4. Prohibiciones

- no modificar `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`;
- no crear entidades comerciales;
- no añadir IMAP, Calendar, CRM, AI, keyring, APScheduler;
- no tocar `main`;
- no usar credenciales reales;
- no llamadas externas;
- no ampliar funcionalidades UI;
- no silenciar tests ni eliminar validaciones para conseguir verde.

---

## 5. Tests obligatorios

Tras corregir:

1. ejecutar `python -m pytest`;
2. todos los tests deben pasar;
3. verificar específicamente:
   - startup usa Settings;
   - host no-loopback rechazado;
   - CSRF token válido aceptado e inválido rechazado;
   - audit no registra payload sensible arbitrario;
   - session factory usa SQLite temporal aislado;
   - migration smoke usa DB temporal controlada;
   - status/health siguen funcionando.

---

## 6. Acceptance criteria

- todos los Major findings resueltos;
- Minor de pytest metadata resuelto;
- suite 100% verde;
- ningún archivo fuera de la lista autorizado;
- sin nuevas dependencias fuera del stack ya aprobado salvo dependencia directa estrictamente necesaria para CSRF/session; si surge esa necesidad y hay más de una alternativa razonable, STOP;
- sin cambios funcionales fuera de Foundation Phase 1.

---

## 7. Completion protocol

- Implementar con `Implement Task`.
- Verificar diff completo.
- Commit:
  `Fix phase 1 foundation review findings`
- Push a `origin/codex-work`.
- No merge a `main`.
