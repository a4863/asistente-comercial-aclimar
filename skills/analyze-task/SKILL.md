# Analyze Task

## Purpose

Analizar una tarea antes de cualquier implementación.

Este Skill tiene como objetivo comprender la tarea, consultar la documentación relevante, inspeccionar el estado actual del proyecto, detectar riesgos y ambigüedades y producir un plan de implementación controlado.

Este Skill NO implementa cambios.

---

## CRITICAL RESTRICTION

Este Skill es READ-ONLY.

ESTÁ PROHIBIDO:

- crear archivos;
- modificar archivos;
- eliminar archivos;
- mover archivos;
- renombrar archivos;
- instalar dependencias;
- modificar dependencias;
- ejecutar migraciones;
- modificar bases de datos;
- modificar configuraciones;
- realizar commits;
- realizar push;
- realizar merges;
- realizar operaciones destructivas de Git;
- ejecutar herramientas o scripts que puedan modificar indirectamente el sistema de archivos, la base de datos, las dependencias o el entorno.

El análisis puede:

- inspeccionar el repositorio;
- leer archivos;
- consultar documentación;
- inspeccionar configuraciones;
- ejecutar comandos de diagnóstico no destructivos cuando sean necesarios;
- ejecutar herramientas de consulta que no modifiquen el estado del proyecto.

Ante cualquier duda sobre si una operación puede modificar el estado del proyecto:

STOP.

No ejecutar la operación.

---

## Workflow

Seguir obligatoriamente este flujo:

### 1. Leer `AGENTS.md`

Antes de analizar la tarea, leer:

```text
AGENTS.md

Respetar todas sus reglas.

2. Identificar la documentación relevante

Determinar qué documentación del proyecto afecta a la tarea.

Consultar, cuando corresponda:

docs/functional-spec.md
docs/data-model.md
docs/testing-strategy.md
docs/architecture.md

No asumir que toda la documentación es relevante para todas las tareas.

3. Leer la especificación funcional relacionada

Identificar las funcionalidades, flujos y reglas de negocio afectadas.

Determinar:

comportamiento esperado;
estados;
transiciones;
validaciones;
criterios de aceptación;
entidades implicadas.
4. Inspeccionar la implementación existente

Inspeccionar únicamente lo necesario para comprender el estado actual.

Revisar:

estructura de archivos;
código relevante;
modelos;
servicios;
repositories;
routes;
templates;
JavaScript;
tests;
migraciones;
configuración.

No modificar ningún elemento durante este proceso.

5. Identificar archivos afectados

Determinar:

archivos que probablemente deberán modificarse;
archivos que deberán crearse;
archivos que podrían necesitar eliminación o movimiento, si estuviera explícitamente contemplado.

Distinguir entre:

IN SCOPE

y:

OUT OF SCOPE

No asumir que un archivo debe modificarse simplemente porque esté relacionado indirectamente.

6. Identificar dependencias

Determinar:

dependencias internas;
dependencias entre módulos;
dependencias de datos;
dependencias con otras funcionalidades;
dependencias externas.

Si la tarea parece requerir una nueva dependencia no contemplada:

STOP.

Presentar la necesidad y solicitar autorización.

7. Identificar riesgos

Analizar riesgos relacionados con:

datos;
base de datos;
migraciones;
arquitectura;
reglas de negocio;
regresiones;
seguridad;
rendimiento;
compatibilidad;
integridad de información.

Clasificar los riesgos cuando sea útil.

8. Buscar ambigüedades

Buscar activamente:

requisitos incompletos;
decisiones no tomadas;
términos ambiguos;
contradicciones entre documentos;
múltiples interpretaciones razonables;
decisiones funcionales pendientes;
decisiones arquitectónicas pendientes;
decisiones de modelo de datos pendientes.

No resolver ambigüedades por iniciativa propia.

9. Determinar si la tarea requiere una decisión funcional o arquitectónica

Determinar explícitamente si la tarea:

puede implementarse directamente según la documentación existente; o
requiere una decisión adicional.

Si requiere una decisión:

STOP.

No escribir código.

Presentar las alternativas y solicitar confirmación.

Ambiguity Rule

Si la tarea admite dos o más interpretaciones razonables, o requiere asunciones sobre el modelo de datos/negocio:

STOP.

No escribir código.

Presentar las alternativas.

Explicar brevemente las consecuencias relevantes.

Solicitar confirmación.

Esta regla también se aplica cuando la ambigüedad aparece durante el análisis.

No elegir automáticamente la alternativa que parezca más sencilla.

Contradiction Rule

Si existe una contradicción entre:

functional-spec.md
data-model.md
testing-strategy.md
architecture.md

o entre cualquiera de estos documentos y la implementación existente:

STOP.

No modificar código.

No modificar documentación.

No decidir qué fuente es correcta por iniciativa propia.

Presentar:

la contradicción;
los elementos afectados;
las alternativas posibles;
las consecuencias;
la decisión necesaria.
Plan

Cuando la tarea pueda continuar, producir un plan de implementación.

El plan debe indicar como mínimo:

objetivo;
contexto;
interpretación de la tarea;
documentación consultada;
archivos afectados;
cambios propuestos;
orden de implementación;
dependencias;
riesgos;
tests;
criterios de aceptación.

El plan debe ser suficientemente concreto para que implement-task pueda ejecutarlo sin tomar nuevas decisiones de negocio o arquitectura.

Scope Lock

Toda tarea que vaya a implementación debe definir un Scope Lock.

El Scope Lock debe indicar:

IN SCOPE

Qué se puede modificar.

OUT OF SCOPE

Qué queda explícitamente fuera de la tarea.

RESTRICTIONS

Qué cambios están prohibidos aunque parezcan necesarios.

Ejemplo:

IN SCOPE
- app/services/oportunidades.py
- app/routes/oportunidades.py
- tests/test_oportunidades.py


OUT OF SCOPE
- modelo de homologación
- dashboard
- importación Excel


RESTRICTIONS
- no cambiar el modelo de datos
- no añadir dependencias
- no modificar arquitectura

El Scope Lock debe ser claro y verificable.

Test Definition

Antes de finalizar el análisis, definir los tests necesarios.

Indicar:

tests unitarios;
tests de integración;
tests de API;
tests de regresión;
casos límite;
criterios de aceptación verificables.

Consultar:

docs/testing-strategy.md

cuando corresponda.

Out-of-Scope Discovery

Durante el análisis, si se detecta un problema aparentemente relacionado pero fuera del alcance:

No incluirlo silenciosamente en el plan.

Registrarlo como:

OUT-OF-SCOPE DISCOVERY

Indicar:

problema;
ubicación;
impacto;
motivo por el que queda fuera;
posible actuación futura.

No modificarlo.

Read-Only Enforcement

Durante todo el análisis:

NO CODE CHANGES
NO FILE CHANGES
NO DATABASE CHANGES
NO DEPENDENCY CHANGES
NO GIT CHANGES

El análisis debe terminar sin modificaciones en el repositorio.

Output

El resultado del análisis debe contener obligatoriamente:

1. Objetivo

Qué se pretende conseguir.

2. Contexto

Situación actual y motivo de la tarea.

3. Interpretación

Qué se entiende exactamente que debe hacerse.

Si existen varias interpretaciones:

STOP

y presentarlas.

4. Documentación consultada

Enumerar los documentos revisados.

5. Estado actual

Resumen de la implementación relevante encontrada.

6. Archivos afectados

Separar:

IN SCOPE
OUT OF SCOPE
7. Cambios propuestos

Descripción concreta de la implementación prevista.

8. Dependencias

Dependencias internas o externas relevantes.

9. Riesgos

Riesgos identificados.

10. Ambigüedades

Indicar:

None

si no existen.

Si existen:

STOP

y solicitar decisión.

11. Tests

Tests que deberán ejecutarse.

12. Scope Lock

Definir explícitamente:

IN SCOPE
OUT OF SCOPE
RESTRICTIONS
13. Decisiones pendientes

Enumerar cualquier decisión necesaria antes de implementar.

14. Resultado del análisis

Clasificar como:

READY FOR APPROVAL

o:

BLOCKED
Approval Gate

El análisis nunca autoriza automáticamente la implementación.

El resultado:

READY FOR APPROVAL

significa únicamente que existe un plan que puede ser revisado.

Antes de utilizar implement-task debe existir:

análisis
+
plan
+
Scope Lock
+
aprobación explícita

Sin aprobación:

STOP.

Final Rule

Analyze Task analiza.

Analyze Task NO implementa.

Analyze Task NO modifica archivos.

Analyze Task NO modifica código.

Analyze Task NO modifica tests.

Analyze Task NO modifica documentación.

Analyze Task NO modifica la base de datos.

Analyze Task NO instala dependencias.

Analyze Task NO realiza commits.

Analyze Task NO toma decisiones funcionales o arquitectónicas no aprobadas.

Si existe ambigüedad:

STOP.

Si existe contradicción:

STOP.

Si falta información:

STOP.

Si una operación puede modificar el estado del proyecto:

NO EJECUTARLA.