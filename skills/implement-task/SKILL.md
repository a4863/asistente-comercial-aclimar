# Implement Task

## Purpose

Implementar exclusivamente un plan previamente analizado y aprobado.

Este Skill solo puede ejecutar cambios que hayan sido definidos previamente mediante:

1. análisis;
2. plan;
3. Scope Lock;
4. aprobación explícita.

Este Skill NO realiza análisis funcional autónomo ni toma decisiones de negocio o arquitectura.

---

## Preconditions

Antes de modificar cualquier archivo debe existir:

1. análisis;
2. plan aprobado;
3. Scope Lock;
4. aprobación explícita.

Si cualquiera de estos elementos falta:

STOP.

No escribir código.

No modificar archivos.

Informar de qué elemento falta y solicitarlo.

---

## CRITICAL RULE

La implementación debe limitarse estrictamente al plan aprobado y al Scope Lock.

No ampliar el alcance.

No resolver problemas no incluidos en el plan.

No tomar decisiones funcionales o arquitectónicas no aprobadas.

Si durante la implementación aparece una decisión no contemplada:

STOP.

Presentar el problema, las alternativas y solicitar confirmación.

---

## Rules

Antes de modificar código:

1. Leer `AGENTS.md`.
2. Leer el plan aprobado.
3. Leer el Scope Lock.
4. Leer la documentación relevante.
5. Inspeccionar los archivos afectados.
6. Confirmar que la implementación propuesta coincide con el plan.
7. Implementar únicamente los cambios aprobados.

---

## Documentation as Contract

La documentación aprobada constituye la referencia funcional y arquitectónica del proyecto.

Cuando sea relevante, consultar:

```text
docs/functional-spec.md
docs/data-model.md
docs/testing-strategy.md
docs/architecture.md

No modificar la documentación aprobada para adaptar la implementación.

Si la implementación requerida contradice la documentación:

STOP.

No decidir por cuenta propia si debe cambiarse el código o la documentación.

Presentar:

la contradicción;
las alternativas;
las consecuencias;
la decisión necesaria.

Esperar aprobación antes de continuar.

Scope Lock

El Scope Lock define los límites de la implementación.

Debe respetarse estrictamente.

No realizar:

funcionalidades adicionales;
refactorizaciones oportunistas;
mejoras no solicitadas;
cambios de arquitectura;
cambios de modelo de datos;
cambios de UX no incluidos;
nuevas integraciones;
nuevas dependencias;

aunque parezcan convenientes.

Minimum Change Principle

Implementar el cambio mínimo necesario para cumplir el plan aprobado.

No realizar refactorizaciones oportunistas.

No reorganizar código no relacionado con la tarea.

No cambiar nombres, estructuras o interfaces que no sean necesarios.

No introducir abstracciones innecesarias.

No convertir una tarea concreta en una refactorización general.

Business Rules

No modificar reglas de negocio durante la implementación.

Las reglas de negocio deben proceder de la documentación aprobada.

Si durante la implementación se descubre que una regla:

falta;
es ambigua;
es contradictoria;
requiere una nueva decisión;

STOP.

No inventar la regla.

Solicitar confirmación.

Data Model

No modificar el modelo de datos por iniciativa propia.

Cualquier cambio en:

tablas;
campos;
relaciones;
claves;
constraints;
estados;
enums;
índices;
reglas de persistencia;

que no esté incluido explícitamente en el plan aprobado requiere STOP.

Si el plan aprobado contempla un cambio de modelo:

comprobar docs/data-model.md;
implementar la modificación prevista;
crear o actualizar la migración correspondiente;
ejecutar los tests relevantes.
Database Migrations

Todo cambio estructural de base de datos debe realizarse mediante Alembic.

No modificar manualmente crm.db para introducir cambios estructurales.

Después de una migración:

comprobar que se ejecuta correctamente;
comprobar que funciona sobre una base de datos limpia;
ejecutar los tests relevantes;
verificar que no se han introducido regresiones.
Architecture

Respetar la arquitectura definida en:

docs/architecture.md

No introducir cambios arquitectónicos no incluidos en el plan.

Cuando corresponda, respetar la separación:

routes
   ↓
services
   ↓
repositories
   ↓
models

No trasladar lógica de negocio a templates o JavaScript cuando corresponda a la capa de servicios.

Dependencies

No introducir dependencias nuevas sin autorización.

Antes de añadir una dependencia:

comprobar si existe una solución utilizando las dependencias actuales;
comprobar si la dependencia está contemplada en la arquitectura;
si no está autorizada, STOP y solicitar aprobación.

No actualizar versiones de dependencias de forma oportunista.

Out-of-Scope Discovery

Si durante la implementación aparece un problema fuera del Scope Lock:

STOP.

No solucionarlo automáticamente.

No ampliar el alcance.

No modificar archivos adicionales para resolverlo.

Registrarlo como hallazgo fuera de alcance.

Informar de:

problema detectado;
archivo o componente afectado;
motivo por el que está fuera del alcance;
posible impacto;
posible solución futura.

Solicitar autorización antes de continuar con cualquier cambio adicional.

Ambiguity Rule

Si la tarea admite dos o más interpretaciones razonables, o requiere asunciones sobre el modelo de datos/negocio:

STOP.

No escribir código.

Presentar las alternativas.

Explicar las consecuencias relevantes.

Solicitar confirmación.

Esta regla también se aplica si la ambigüedad aparece durante la implementación aunque el plan original pareciera claro.

Git

Este Skill no debe realizar operaciones de Git que alteren el historial o integren cambios salvo autorización explícita.

Está prohibido realizar sin autorización:

commits;
push;
pull;
merge;
rebase;
reset destructivo;
checkout destructivo;
eliminación de ramas;
modificación destructiva del historial.

La implementación debe dejar los cambios disponibles para revisión.

File Safety

No eliminar archivos existentes salvo que la eliminación esté expresamente incluida en el plan aprobado.

No mover ni renombrar archivos salvo que esté expresamente incluido.

No sobrescribir archivos no relacionados con la tarea.

No crear archivos fuera del Scope Lock.

Testing

Después de implementar:

ejecutar tests relevantes;
comprobar errores;
ejecutar tests de regresión cuando corresponda;
revisar los cambios realizados;
verificar el Scope Lock;
comprobar que no existen modificaciones fuera del alcance.

Los tests deben corresponder a la estrategia definida en:

docs/testing-strategy.md
Test Failure

Si los tests relevantes fallan:

STOP.

No ocultar el fallo.

No eliminar o modificar tests únicamente para conseguir un resultado GREEN.

Determinar si el fallo:

está causado por la implementación;
corresponde a una regresión;
revela una contradicción;
pertenece a un problema fuera del Scope Lock.

Si resolverlo requiere una decisión no contemplada:

STOP y solicitar confirmación.

Test Integrity

No modificar tests existentes para hacer que una implementación incorrecta pase.

Los tests solo pueden modificarse cuando:

el plan aprobado contempla expresamente el cambio; o
existe una autorización explícita posterior.

Si la implementación y el test contradicen la especificación:

STOP.

No asumir cuál de los dos es correcto.

Review Before Completion

Antes de declarar la tarea terminada:

revisar los archivos modificados;
comprobar que todos están dentro del Scope Lock;
comprobar que no existen cambios accidentales;
revisar las diferencias relevantes;
comprobar las migraciones cuando existan;
ejecutar los tests requeridos;
verificar que no existen errores conocidos;
comprobar que la documentación sigue siendo coherente.
Completion Criteria

No declarar la tarea completada si:

faltan precondiciones;
fallan tests relevantes;
existe una modificación fuera del Scope Lock;
existe una incertidumbre funcional;
existe una incertidumbre arquitectónica;
existe una modificación no verificada;
existe una dependencia no autorizada;
existe una migración no comprobada;
existe una contradicción con la documentación;
existe un hallazgo crítico sin resolver.
Documentation Update

Si el plan aprobado contempla explícitamente actualizar documentación:

modificar únicamente la documentación incluida en el Scope Lock;
comprobar que refleja exactamente la implementación aprobada;
ejecutar los tests correspondientes cuando sea relevante.

Si la implementación requiere modificar documentación que no estaba incluida en el plan:

STOP.

Solicitar autorización.

Nunca modificar la documentación únicamente para hacer que una implementación no aprobada parezca coherente.

Output

Al finalizar, informar de forma estructurada:

1. Cambios realizados

Indicar qué se ha implementado.

2. Archivos modificados

Enumerar todos los archivos modificados, creados o eliminados.

3. Scope Lock

Indicar si se ha respetado completamente.

4. Tests ejecutados

Indicar:

tests ejecutados;
resultado;
posibles fallos.
5. Migraciones

Si corresponde:

migraciones creadas o modificadas;
resultado de su ejecución;
comprobación sobre base limpia.
6. Limitaciones

Indicar cualquier limitación conocida.

7. Hallazgos fuera de alcance

Indicar cualquier problema detectado que no haya sido solucionado.

8. Decisiones pendientes

Indicar cualquier decisión que deba tomar el usuario.

9. Resultado

Clasificar como:

IMPLEMENTED

o:

BLOCKED

si no ha sido posible completar la tarea por una decisión pendiente, error o condición no satisfecha.

Final Rule

Implement Task implementa.

Implement Task NO redefine la funcionalidad.

Implement Task NO modifica las reglas de negocio por iniciativa propia.

Implement Task NO amplía el Scope Lock.

Implement Task NO corrige problemas fuera del alcance.

Implement Task NO modifica documentación aprobada para adaptar el código.

Implement Task NO realiza refactorizaciones oportunistas.

Implement Task NO realiza operaciones destructivas de Git sin autorización.

Si aparece una ambigüedad:

STOP.

Si aparece una contradicción:

STOP.

Si aparece un problema fuera del Scope Lock:

STOP.

Si falta una precondición:

STOP.
