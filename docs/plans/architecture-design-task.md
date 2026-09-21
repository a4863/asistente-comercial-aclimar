# Architecture Design Analysis Task

**Estado:** Approved for Analyze
**Fecha:** 2026-09-21
**Autor:** ChatGPT / project coordination

---

## 1. Objetivo

Analizar la arquitectura necesaria para el Asistente Comercial ACLIMAR a partir de la especificación funcional y del modelo de datos aprobados.

El resultado debe preparar una futura redacción de `docs/architecture.md`, pero NO debe crear todavía ese documento ni seleccionar tecnología sin justificarla y someterla a aprobación.

---

## 2. Documentación obligatoria

Leer:

- `AGENTS.md`
- `skills/analyze-task/SKILL.md`
- `docs/functional-spec.md`
- `docs/data-model.md`
- `docs/plans/functional-spec-readiness.md`
- `docs/plans/data-model-design-analysis.md`

---

## 3. Alcance del análisis

Analizar como mínimo:

- límites de componentes;
- flujo de datos local;
- sincronización IMAP;
- reconstrucción de hilos;
- análisis IA;
- UI local;
- persistencia del asistente;
- aprobaciones y ejecución de acciones;
- Google Calendar;
- CRM API;
- notas y WhatsApp manual;
- scheduler/background jobs;
- idempotencia;
- revalidación de estado externo;
- logs/audit;
- gestión de errores e integración degradada;
- configuración y secretos;
- separación entre dominio, integraciones y persistencia;
- estrategia para que el modelo de IA sea intercambiable;
- arranque local;
- testing boundaries;
- observabilidad local mínima.

---

## 4. Decisiones que deben evaluarse

El análisis puede proponer alternativas para:

- lenguaje/framework;
- interfaz local;
- mecanismo de persistencia;
- ORM o acceso a datos;
- migraciones;
- scheduler;
- librerías IMAP;
- Google Calendar API;
- HTTP client CRM;
- almacenamiento seguro de secretos;
- proveedor/modelo IA;
- estrategia de ejecución local.

Pero si existen dos o más alternativas razonables con consecuencias materiales:

STOP.

Presentar alternativas y pedir decisión.

No elegir por comodidad.

---

## 5. Restricciones obligatorias

La arquitectura debe respetar:

- local-only;
- single-user;
- no SaaS;
- no multi-tenant;
- CRM API-only;
- sin acceso directo a `crm.db`;
- sin envío automático de email;
- mutaciones externas con aprobación;
- datos externos tratados como no confiables;
- separación facts/inferences/proposals;
- trazabilidad completa;
- idempotencia;
- mínima exposición a IA remota;
- degradación por integración sin caída total de la aplicación.

---

## 6. Reutilización y simplicidad

Favorecer una arquitectura sencilla y mantenible.

No introducir microservicios, colas distribuidas, Kubernetes, brokers externos, event buses remotos ni infraestructura empresarial salvo necesidad demostrada.

El proyecto es local y monousuario.

---

## 7. Required output

Crear solo:

`docs/plans/architecture-design-analysis.md`

Debe contener:

1. objetivo;
2. contexto;
3. documentación consultada;
4. estado actual;
5. componentes propuestos;
6. límites y responsabilidades;
7. flujos principales;
8. integración IMAP;
9. Calendar;
10. CRM API;
11. AI boundary;
12. persistencia;
13. background/scheduling;
14. approvals/execution;
15. error isolation;
16. security implications;
17. testing implications;
18. alternativas arquitectónicas relevantes;
19. ambigüedades;
20. riesgos;
21. out-of-scope discoveries;
22. Scope Lock;
23. resultado:
   - READY FOR APPROVAL
   - BLOCKED

---

# SCOPE LOCK

## IN SCOPE

- Analizar arquitectura.
- Crear solo `docs/plans/architecture-design-analysis.md`.

## OUT OF SCOPE

- `docs/architecture.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- código
- dependencias
- bases de datos
- migraciones
- integración real
- cambios en CRM
- cambios en functional-spec o data-model

## RESTRICTIONS

- no implementación;
- no cambios en `main`;
- commit/push solo a `codex-work`;
- no seleccionar silenciosamente alternativas materiales.

---

## 8. Completion protocol

1. crear solo `docs/plans/architecture-design-analysis.md`;
2. commit:
   `Analyze commercial assistant architecture`
3. push a `origin/codex-work`;
4. no merge a `main`.
