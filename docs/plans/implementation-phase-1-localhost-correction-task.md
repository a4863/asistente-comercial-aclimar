# Phase 1 Final Localhost Startup Correction Task

**Estado:** Approved for Implement
**Fecha:** 2026-09-21
**Baseline:** `bf1b252cea8a40bdf368b21b63b291efe21d8b03`
**Review:** `docs/plans/implementation-phase-1-final-review.md`

## 1. Objetivo

Corregir únicamente el último hallazgo Major abierto de Fase 1:

> El arranque real con Uvicorn puede saltarse la política localhost-only mediante `--host 0.0.0.0`.

La corrección debe introducir una vía de arranque controlada que use la configuración validada y lance Uvicorn exclusivamente sobre `127.0.0.1`.

---

## 2. Requisito funcional

Crear una función/entry point controlado que:

- cargue `Settings` mediante `load_settings()` o reciba `Settings` validado;
- use `settings.host` y `settings.port`;
- rechace cualquier host distinto de `127.0.0.1`;
- invoque Uvicorn programáticamente;
- use el FastAPI app ya construido por `create_app(settings)`;
- no permita un override normal de host por CLI dentro del flujo aprobado;
- sea la vía operativa/documentada de arranque de la aplicación.

No añadir todavía Windows Task Scheduler.

---

## 3. Archivos autorizados

Solo pueden modificarse:

```text
app/main.py
pyproject.toml
test/test_startup.py
```

No crear archivos nuevos.

Si fuese materialmente necesario otro archivo: STOP.

---

## 4. Implementación esperada

Una solución válida puede ser, conceptualmente:

- `run()` o `main()` en `app/main.py`;
- carga Settings;
- crea app con esos Settings;
- llama `uvicorn.run(app, host=settings.host, port=settings.port, ...)`;
- expone un script en `pyproject.toml`, por ejemplo:
  `asistente-aclimar = "app.main:run"`

El nombre concreto puede variar, pero debe ser simple y coherente.

No usar shell wrappers ni introducir otra tecnología.

---

## 5. Tests obligatorios

Añadir tests no-network que:

1. monkeypatch/mock `uvicorn.run`;
2. ejecuten el launcher controlado;
3. verifiquen que se llama exactamente con:
   - host `127.0.0.1`;
   - el port de Settings;
   - la app creada;
4. verifiquen que Settings no-loopback sigue rechazado;
5. no abran sockets reales.

Ejecutar:

`python -m pytest`

La suite debe quedar completamente verde.

---

## 6. Prohibiciones

- no tocar docs aprobados;
- no añadir funcionalidades de negocio;
- no añadir integraciones;
- no modificar `main` branch;
- no crear scripts externos;
- no relajar la validación de host;
- no aceptar `0.0.0.0`, LAN IPs, `::`, ni valores configurables externos para bind;
- no eliminar tests existentes.

---

## 7. Acceptance criteria

- existe una vía de arranque controlada y testeada;
- dicha vía usa exclusivamente Settings validados;
- Uvicorn recibe `127.0.0.1`;
- el flujo aprobado no depende de recordar manualmente `--host 127.0.0.1`;
- todos los tests pasan;
- solo cambian los tres archivos autorizados;
- no aparecen nuevas dependencias fuera del stack aprobado.

---

## 8. Completion protocol

Implementar con `Implement Task`.

Commit:

`Enforce controlled localhost startup`

Push a `origin/codex-work`.

No merge a `main`.
