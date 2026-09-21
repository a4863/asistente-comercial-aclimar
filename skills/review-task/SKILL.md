# Review Task

## Purpose

Revisar una implementación terminada frente al plan aprobado, el Scope Lock y la documentación oficial del proyecto.

El objetivo es determinar si la implementación puede aceptarse o requiere correcciones.

Review detecta problemas.

Review NO los corrige.

---

## CRITICAL RESTRICTION

Este Skill es READ-ONLY.

ESTÁ PROHIBIDO:

- modificar archivos;
- crear archivos;
- eliminar archivos;
- mover o renombrar archivos;
- corregir código;
- modificar tests;
- instalar dependencias;
- modificar dependencias;
- ejecutar migraciones que alteren datos;
- modificar bases de datos;
- modificar buzones;
- mover, copiar o eliminar correos;
- crear borradores reales;
- enviar correos;
- modificar Google Calendar;
- modificar datos del CRM;
- realizar commits;
- realizar push;
- realizar merges;
- ejecutar acciones que modifiquen el estado local o externo.

La revisión puede:

- inspeccionar el repositorio;
- leer archivos;
- revisar diffs;
- ejecutar tests no destructivos;
- ejecutar comandos de diagnóstico;
- inspeccionar contratos e interfaces;
- revisar logs sanitizados;
- utilizar mocks, fixtures o entornos de prueba.

Ante cualquier duda sobre si una operación puede modificar estado:

STOP.

No ejecutar la operación.

---

## Preconditions

Antes de comenzar debe existir:

1. implementación terminada;
2. plan aprobado;
3. Scope Lock;
4. documentación relevante disponible.

Si falta cualquiera:

STOP.

Indicar qué elemento falta.

---

## Documentation

Consultar cuando corresponda:

```text
docs/functional-spec.md
docs/data-model.md
docs/architecture.md
docs/security.md
docs/testing-strategy.md
```

También:

- plan aprobado;
- Scope Lock.

La documentación aprobada constituye el contrato de revisión.

No asumir que una decisión tomada durante implementación es válida si contradice la documentación.

---

## Review Areas

Comprobar, cuando sean aplicables:

- cumplimiento funcional;
- cumplimiento del plan;
- cumplimiento del Scope Lock;
- modelo de datos;
- arquitectura;
- seguridad;
- reglas de aprobación;
- trazabilidad;
- procedencia;
- separación entre hechos, inferencias y propuestas;
- correo IMAP;
- reconstrucción de hilos;
- archivado;
- borradores;
- Google Calendar;
- CRM API;
- notas manuales;
- WhatsApp manual;
- seguimiento y prioridades;
- idempotencia;
- concurrencia y revalidación;
- tests;
- regresiones;
- dependencias;
- calidad de código;
- documentación;
- ausencia de cambios no autorizados.

No todas las áreas son aplicables a todas las tareas.

---

## Functional Compliance

Comprobar que la implementación realiza exactamente lo definido.

Verificar especialmente:

- flujos;
- estados;
- transiciones;
- validaciones;
- permisos;
- aprobaciones;
- relaciones entre entidades;
- criterios de aceptación;
- comportamiento ante ambigüedad;
- comportamiento ante errores.

No es suficiente que "funcione".

Debe funcionar de acuerdo con la especificación aprobada.

---

## Data Model Compliance

Cuando la tarea afecte a datos, comprobar:

- entidades;
- campos;
- relaciones;
- claves;
- restricciones;
- estados;
- integridad;
- procedencia;
- trazabilidad;
- historial;
- idempotencia;
- mecanismo de evolución estructural definido por arquitectura.

No aceptar cambios estructurales no autorizados.

---

## Architecture Compliance

Comprobar que la implementación respeta:

```text
docs/architecture.md
```

Verificar:

- separación de responsabilidades;
- límites entre componentes;
- acceso al CRM exclusivamente mediante API;
- ausencia de acceso directo a la base de datos interna del CRM;
- uso correcto de almacenamiento local;
- uso correcto de integraciones externas;
- ausencia de infraestructura no aprobada;
- ausencia de patrones o frameworks introducidos fuera del plan.

No asumir ninguna arquitectura procedente del CRM anterior.

---

## Security Compliance

Comprobar:

- ausencia de credenciales en código;
- ausencia de secretos en Git;
- ausencia de contraseñas en texto plano;
- ausencia de tokens en logs;
- almacenamiento seguro de credenciales;
- permisos mínimos necesarios;
- validación de entradas;
- tratamiento de datos externos como no confiables;
- protección frente a instrucciones embebidas en emails, notas, WhatsApp, Calendar o CRM;
- exposición innecesaria de información comercial;
- operaciones destructivas;
- rutas de archivos;
- errores que puedan filtrar secretos.

Cualquier exposición de secretos debe considerarse al menos Major y, si implica riesgo real, Critical.

---

## Approval Compliance

Comprobar que cualquier operación que modifique estado externo requiera aprobación cuando así lo establece el MVP.

Especialmente:

- mover correo;
- crear borrador;
- crear evento;
- modificar evento;
- actualizar CRM.

Verificar que:

- la aprobación corresponde a una acción concreta;
- no existe autoaprobación persistente no autorizada;
- una acción rechazada no se ejecuta;
- una acción aprobada no se reutiliza indebidamente para otra operación;
- el sistema revalida el objetivo cuando el estado externo puede haber cambiado.

---

## Mailbox Compliance

Cuando la tarea afecte a correo, comprobar:

- uso correcto de IMAP;
- reconstrucción de hilos según evidencia definida;
- ausencia de fusiones ambiguas;
- conservación de procedencia;
- propuestas de carpeta solo sobre carpetas existentes;
- no creación automática de carpetas;
- movimiento solo tras aprobación;
- ausencia de envío automático;
- creación de borradores solo tras aprobación;
- prevención de borradores duplicados;
- manejo seguro de errores IMAP;
- recuperación ante cambios del buzón;
- tests sin modificar correo real salvo autorización explícita.

---

## Thread Reconstruction

Cuando corresponda, revisar que la agrupación prioriza:

- Message-ID;
- In-Reply-To;
- References.

El asunto normalizado y contexto solo pueden actuar como evidencia auxiliar.

Si la implementación fusiona conversaciones con evidencia insuficiente, registrar hallazgo.

---

## Draft Safety

Comprobar:

- destino correcto en Drafts/Borradores;
- aprobación previa;
- no envío;
- idempotencia;
- asociación con la propuesta correspondiente;
- ausencia de duplicados;
- manejo de fallos parciales.

---

## Calendar Compliance

Cuando la tarea afecte a Google Calendar:

- lectura conforme a permisos;
- creación solo con aprobación;
- modificación solo con aprobación;
- eliminación fuera del MVP;
- ausencia de cambios reales en tests salvo autorización;
- revalidación del evento antes de modificarlo cuando corresponda.

---

## CRM Compliance

Comprobar:

- acceso únicamente vía API;
- CRM como fuente maestra de empresas, contactos, obras, oportunidades y ofertas;
- ausencia de acceso directo a `crm.db`;
- escrituras solo con aprobación;
- ausencia de borrado automático;
- ausencia de modificación automática de importes;
- ausencia de modificación automática de identidad/master data;
- manejo de conflictos;
- respeto de fuente de verdad.

---

## Facts, Inferences and Proposals

Comprobar que el sistema distingue correctamente:

- hecho extraído;
- inferencia;
- propuesta.

Un hecho debe conservar evidencia.

Una inferencia no debe almacenarse o propagarse como hecho sin confirmación o evidencia posterior.

Una propuesta no debe tratarse como acción ya aprobada.

Cualquier actualización factual basada únicamente en una inferencia debe registrarse como hallazgo.

---

## Provenance and Auditability

Comprobar que puede reconstruirse:

```text
source
-> extraction
-> inference
-> proposal
-> approval/rejection
-> execution result
```

Verificar:

- identificadores de origen;
- timestamps;
- relación entre fuente y extracción;
- relación entre propuesta y aprobación;
- relación entre aprobación y ejecución;
- historial de correcciones;
- ausencia de sobrescritura silenciosa de eventos ejecutados.

---

## Identity Matching

Cuando corresponda, comprobar:

- preferencia por email exacto;
- uso de IDs del CRM;
- uso de relaciones confirmadas;
- manejo de múltiples coincidencias;
- ausencia de resolución silenciosa de identidades ambiguas.

Una asociación incorrecta entre cliente/contacto/obra debe clasificarse según impacto.

---

## Follow-up Rules

Comprobar:

- umbrales configurables;
- precedencia de overrides;
- respeto de fechas futuras acordadas;
- generación de alertas/propuestas;
- ausencia de acciones externas automáticas no autorizadas;
- consistencia con la especificación.

---

## Idempotency

Revisar operaciones repetibles.

Especial atención a:

- sincronización IMAP;
- creación de borradores;
- creación de tareas;
- registro de actividades;
- propuestas CRM;
- eventos Calendar;
- importación manual de WhatsApp;
- procesamiento repetido de notas.

Repetir una operación no debe crear duplicados injustificados.

---

## Concurrency and Revalidation

Comprobar comportamiento cuando el estado cambia entre:

- análisis;
- aprobación;
- ejecución.

Verificar que las operaciones externas revalidan cuando corresponde.

Si una implementación ejecuta sobre estado obsoleto sin comprobarlo, registrar hallazgo.

---

## Testing

Ejecutar los tests relevantes definidos por:

```text
docs/testing-strategy.md
```

Comprobar, cuando corresponda:

- tests unitarios;
- tests de integración;
- tests de contrato;
- tests de API;
- tests de persistencia;
- tests de seguridad;
- tests de idempotencia;
- tests de regresión;
- casos límite;
- errores esperados.

No considerar suficiente que existan tests.

Deben ejecutarse y registrarse los resultados.

---

## External-System Test Safety

Los tests no deben modificar accidentalmente:

- buzón real;
- Calendar real;
- CRM real;
- archivos reales no destinados a test.

Preferir:

- mocks;
- fixtures;
- dobles de prueba;
- entornos aislados.

Si una prueba real está autorizada, revisar que el alcance coincida exactamente con la aprobación.

---

## Regression Check

Comprobar que los cambios no rompen funcionalidades existentes.

Ejecutar la suite completa cuando la estrategia de testing así lo requiera.

---

## Scope Lock

Comparar cambios reales con el Scope Lock.

Detectar:

- archivos fuera del alcance;
- funcionalidades añadidas;
- refactorizaciones no autorizadas;
- cambios de arquitectura;
- cambios de modelo;
- dependencias añadidas;
- cambios de permisos;
- cambios de documentación no previstos;
- interacciones externas no autorizadas.

Cualquier desviación debe registrarse.

---

## Out-of-Scope Changes

Si existe un cambio fuera del plan:

- no corregirlo;
- no revertirlo;
- no ocultarlo.

Registrarlo como hallazgo.

Review no tiene autoridad para modificar implementación.

---

## Documentation Discrepancy

Si existe discrepancia entre documentación e implementación:

NO asumir que implementación es correcta.

Si la discrepancia requiere decisión funcional, arquitectónica, de seguridad o modelo:

STOP.

Presentar:

- discrepancia;
- alternativas;
- consecuencias;
- decisión necesaria.

---

## Dependencies

Comprobar cualquier dependencia nueva.

Detectar:

- dependencias no autorizadas;
- dependencias innecesarias;
- duplicación;
- cambios de versión oportunistas;
- impacto arquitectónico;
- impacto de seguridad/licencia cuando sea relevante.

---

## Code Quality

Evaluar:

- claridad;
- simplicidad;
- separación de responsabilidades;
- duplicación;
- complejidad innecesaria;
- nombres;
- mantenibilidad;
- coherencia con arquitectura.

No exigir cambios puramente estéticos como bloqueo si no afectan cumplimiento, seguridad o mantenibilidad significativa.

---

## Review Classification

Clasificar cada hallazgo:

### Critical

Impide aceptar.

Ejemplos:

- pérdida o corrupción de datos;
- envío de correo no autorizado;
- modificación externa sin aprobación;
- exposición de credenciales;
- acceso directo no autorizado al CRM DB;
- asociación grave de datos con cliente equivocado;
- vulnerabilidad relevante;
- funcionalidad principal incorrecta;
- tests críticos fallando.

### Major

Debe corregirse antes de aceptar.

Ejemplos:

- incumplimiento funcional;
- aprobación insuficiente;
- regla de negocio incorrecta;
- regresión;
- arquitectura incorrecta;
- idempotencia defectuosa;
- trazabilidad incompleta relevante;
- test importante fallando;
- cambio importante fuera del Scope Lock.

### Minor

No bloquea aceptación.

Ejemplos:

- defecto menor;
- inconsistencia secundaria;
- mejora de mantenibilidad;
- problema no crítico de UX.

### Observation

No requiere corrección inmediata.

Puede incluir:

- mejora futura;
- deuda técnica menor;
- oportunidad de optimización;
- hallazgo fuera de alcance sin impacto actual.

---

## Acceptance Criteria

La implementación solo puede aceptarse si:

- [ ] cumple especificación;
- [ ] cumple plan;
- [ ] respeta Scope Lock;
- [ ] respeta modelo de datos;
- [ ] respeta arquitectura;
- [ ] respeta seguridad;
- [ ] respeta reglas de aprobación;
- [ ] mantiene trazabilidad;
- [ ] distingue hechos/inferencias/propuestas;
- [ ] tests relevantes GREEN;
- [ ] no existen regresiones críticas;
- [ ] no existen acciones externas no autorizadas;
- [ ] no existen hallazgos Critical;
- [ ] no existen hallazgos Major pendientes.

---

## Review Decision

Resultado final:

### ACCEPT

Cumple criterios y no existen hallazgos bloqueantes.

### CHANGES REQUIRED

Existen hallazgos Critical o Major.

### BLOCKED

No puede completarse revisión debido a:

- documentación contradictoria;
- falta de plan;
- falta de Scope Lock;
- falta de información;
- decisión funcional pendiente;
- decisión arquitectónica pendiente;
- decisión de seguridad pendiente;
- imposibilidad de ejecutar tests no destructivos necesarios.

---

## Output

El resultado debe contener:

### 1. Resumen

- objetivo revisado;
- resultado general.

### 2. Documentación consultada

Documentos utilizados.

### 3. Plan y Scope Lock

Indicar si se han respetado.

### 4. Implementación revisada

- archivos;
- componentes;
- integraciones;
- áreas afectadas.

### 5. Tests

- tests ejecutados;
- resultado;
- fallos.

### 6. Sistemas externos

Indicar si la implementación interactúa con:

- IMAP/SMTP;
- Google Calendar;
- CRM API;
- otros.

Indicar si cualquier interacción real fue autorizada.

### 7. Hallazgos

Clasificar:

- Critical;
- Major;
- Minor;
- Observation.

Para cada hallazgo indicar:

- descripción;
- archivo/componente;
- impacto;
- referencia a especificación cuando corresponda.

### 8. Decisiones pendientes

Cualquier decisión del usuario.

### 9. Resultado final

Uno de:

```text
ACCEPT
CHANGES REQUIRED
BLOCKED
```

---

## Final Rule

Review detecta problemas.

Review NO los corrige.

Review NO modifica código.

Review NO modifica tests.

Review NO modifica documentación.

Review NO modifica datos.

Review NO modifica sistemas externos.

Review NO toma decisiones funcionales, arquitectónicas, de seguridad o modelo de datos.

Si encuentra una ambigüedad que requiere decisión:

STOP.

Presentar el problema.