# Review Task

## Purpose

Revisar una implementación terminada frente al plan aprobado, el Scope Lock y la documentación oficial del proyecto.

Este Skill tiene como objetivo determinar si la implementación puede ser aceptada o si requiere correcciones.

---

## CRITICAL RESTRICTION

Este Skill es READ-ONLY.

ESTÁ PROHIBIDO:

- modificar archivos;
- crear archivos;
- eliminar archivos;
- corregir código;
- modificar tests;
- instalar dependencias;
- realizar migraciones;
- modificar bases de datos;
- realizar commits;
- realizar push;
- realizar merges;
- ejecutar acciones que modifiquen el estado del repositorio.

La revisión puede inspeccionar el repositorio y ejecutar comandos de diagnóstico o tests no destructivos cuando sean necesarios.

Review detecta problemas.

Review NO los corrige.

---

## Preconditions

Antes de comenzar la revisión debe existir:

1. implementación terminada;
2. plan aprobado;
3. Scope Lock;
4. documentación relevante disponible.

Si falta cualquiera de estos elementos:

STOP.

Informar de qué elemento falta y solicitarlo antes de continuar.

---

## Documentation

La revisión debe consultar, cuando sean relevantes:

```text
docs/functional-spec.md
docs/data-model.md
docs/testing-strategy.md
docs/architecture.md

También debe consultar:

plan aprobado
Scope Lock

La documentación aprobada constituye la referencia para evaluar la implementación.

No asumir que una decisión tomada durante la implementación es correcta si contradice la documentación aprobada.

Review

Comprobar:

cumplimiento funcional;
cumplimiento del Scope Lock;
cumplimiento del plan aprobado;
modelo de datos;
arquitectura;
reglas de negocio;
homologación;
oportunidades;
ofertas y versiones;
dashboard cuando corresponda;
tests;
regresiones;
seguridad;
dependencias;
calidad del código;
documentación;
ausencia de cambios no autorizados.

No todas las comprobaciones serán aplicables a todas las tareas.

Functional Compliance

Comprobar que la implementación realiza exactamente la funcionalidad definida.

Verificar especialmente:

flujos;
estados;
transiciones;
validaciones;
reglas de negocio;
relaciones entre entidades;
criterios de aceptación.

No considerar suficiente que:

"el código funciona"

Debe funcionar de acuerdo con la especificación aprobada.

Data Model Compliance

Cuando la tarea afecte a datos, comprobar:

tablas;
campos;
relaciones;
claves;
restricciones;
estados;
integridad referencial;
migraciones.

No aceptar cambios estructurales que no estén contemplados en el modelo de datos aprobado.

Si se detecta una modificación del modelo no autorizada:

Clasificarla como hallazgo.

Architecture Compliance

Comprobar que la implementación respeta:

routes
   ↓
services
   ↓
repositories
   ↓
models

cuando corresponda.

Comprobar también:

separación de responsabilidades;
ausencia de lógica de negocio innecesaria en routes;
ausencia de acceso directo a base de datos desde templates;
ausencia de acceso directo a SQLite desde JavaScript;
uso correcto de migraciones;
dependencias autorizadas.

No aceptar cambios arquitectónicos no incluidos en el plan o autorizados explícitamente.

Business Rules

Comprobar las reglas de negocio definidas en la documentación.

Prestar especial atención a:

Oportunidades
Oportunidad

no debe confundirse con:

Oferta
Ofertas

La estructura debe mantenerse:

Oportunidad
    ↓
Oferta
    ↓
Oferta_Versiones

Debe respetarse la lógica de versiones definida en el modelo.

Homologación

Debe mantenerse la diferencia entre:

estado actual

e:

histórico de eventos

Y no debe asumirse:

documentación completa = homologación

cuando la especificación requiera confirmación explícita.

Testing

Ejecutar los tests relevantes definidos por:

docs/testing-strategy.md

Comprobar:

tests unitarios;
tests de integración;
tests de API cuando correspondan;
tests de regresión;
casos límite;
errores esperados.

No considerar suficiente que exista código de test.

Los tests deben ejecutarse y su resultado debe quedar registrado.

Regression Check

Comprobar que los cambios no rompen funcionalidades existentes.

Cuando corresponda:

pytest

debe ejecutarse sobre el conjunto completo de tests.

Si el proyecto tiene tests específicos relacionados con la tarea, deben ejecutarse además de los tests generales.

Scope Lock

Comparar los cambios reales del repositorio con el Scope Lock aprobado.

Detectar:

archivos modificados fuera del alcance;
funcionalidades añadidas;
refactorizaciones no autorizadas;
cambios de arquitectura;
cambios de modelo;
dependencias añadidas;
modificaciones de documentación no previstas.

Cualquier cambio fuera del Scope Lock debe registrarse como hallazgo.

Out-of-Scope Changes

Detectar cualquier cambio fuera del plan aprobado.

Si existe:

no corregirlo;
no revertirlo;
no modificarlo;
no ocultarlo.

Registrarlo como hallazgo.

La revisión no tiene autoridad para modificar la implementación.

Documentation Discrepancy

Si existe una discrepancia entre:

documentación aprobada

y:

implementación

NO asumir automáticamente que la implementación es correcta.

Determinar si la discrepancia puede resolverse claramente según la documentación.

Si no puede resolverse sin tomar una decisión funcional o arquitectónica:

STOP.

Presentar:

la discrepancia;
las alternativas;
las consecuencias;
la decisión necesaria.

No modificar documentación ni código.

Security

Comprobar, cuando sea relevante:

validación de entradas;
consultas seguras;
ausencia de credenciales en código;
ausencia de secretos en Git;
control de rutas de archivos;
operaciones destructivas;
exposición innecesaria de información;
dependencias introducidas.
Dependencies

Comprobar cualquier dependencia nueva.

Debe existir autorización previa cuando la dependencia no esté contemplada en la arquitectura.

Detectar:

dependencias innecesarias;
duplicación de librerías;
cambios de versiones no autorizados;
dependencias con impacto arquitectónico.
Code Quality

Evaluar:

claridad;
simplicidad;
separación de responsabilidades;
duplicación;
complejidad innecesaria;
nombres;
mantenibilidad;
coherencia con la arquitectura.

No solicitar refactorizaciones puramente estéticas como condición para aceptar una implementación si no afectan a la calidad o al cumplimiento de la arquitectura.

Database Safety

Cuando la tarea afecte a la base de datos comprobar:

migraciones;
integridad referencial;
constraints;
transacciones;
compatibilidad con SQLite;
ausencia de modificaciones manuales no justificadas.

No ejecutar operaciones destructivas durante la revisión.

Review Classification

Clasificar cada hallazgo en una de las siguientes categorías.

Critical

Impide aceptar la implementación.

Ejemplos:

pérdida o corrupción de datos;
incumplimiento grave del modelo de datos;
vulnerabilidad relevante;
funcionalidad principal incorrecta;
modificación grave fuera del alcance;
tests críticos fallando.
Major

Debe corregirse antes de aceptar.

Ejemplos:

incumplimiento funcional;
regla de negocio incorrecta;
regresión;
arquitectura incorrecta;
migración defectuosa;
test relevante fallando;
cambio importante fuera del Scope Lock.
Minor

No bloquea la aceptación.

Ejemplos:

defecto menor;
mejora de mantenibilidad;
pequeña inconsistencia;
problema no crítico de UX.
Observation

No requiere corrección inmediata.

Puede incluir:

mejora futura;
deuda técnica menor;
oportunidad de optimización;
hallazgo fuera del alcance que no afecta a la aceptación.
Acceptance Criteria

La implementación solo puede considerarse aceptable si:

[ ] cumple la especificación
[ ] cumple el plan
[ ] respeta el Scope Lock
[ ] respeta el modelo de datos
[ ] respeta la arquitectura
[ ] respeta las reglas de negocio
[ ] tests relevantes GREEN
[ ] no existen regresiones críticas
[ ] no existen cambios no autorizados críticos
[ ] no existen hallazgos Critical
[ ] no existen hallazgos Major pendientes
Review Decision

El resultado final debe clasificarse como uno de:

ACCEPT

La implementación cumple los criterios y no existen hallazgos bloqueantes.

CHANGES REQUIRED

Existen hallazgos Critical o Major que deben corregirse.

BLOCKED

No es posible completar la revisión debido a:

documentación contradictoria;
falta de plan;
falta de Scope Lock;
falta de información;
decisión funcional pendiente;
decisión arquitectónica pendiente.
Output

El resultado debe contener:

1. Resumen
objetivo revisado;
resultado general.
2. Documentación consultada

Indicar los documentos utilizados.

3. Plan y Scope Lock

Indicar si se han respetado.

4. Implementación revisada

Indicar:

archivos revisados;
componentes revisados;
áreas afectadas.
5. Tests

Indicar:

tests ejecutados;
resultado;
posibles fallos.
6. Hallazgos

Clasificar cada uno como:

Critical
Major
Minor
Observation

Para cada hallazgo indicar:

descripción;
archivo;
impacto;
referencia a la especificación cuando corresponda.
7. Decisiones pendientes

Indicar cualquier decisión que deba tomar el usuario.

8. Resultado final

Uno de:

ACCEPT
CHANGES REQUIRED
BLOCKED
Final Rule

Review detecta problemas.

Review NO los corrige.

Review NO modifica código.

Review NO modifica tests.

Review NO modifica documentación.

Review NO modifica el modelo de datos.

Review NO toma decisiones funcionales o arquitectónicas.

Si la revisión encuentra una ambigüedad que requiere una decisión:

STOP.

Presentar el problema y solicitar confirmación.