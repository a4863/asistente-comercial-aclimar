# AGENTS.md

## 1. Proyecto

CRM local monousuario para la prospección comercial de Aclimar en la Comunitat Valenciana.

Stack definido:

- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- SQLite
- Jinja2
- HTML/CSS
- JavaScript vanilla
- pytest

La aplicación funciona localmente.

---

## 2. Fuente de verdad

Antes de modificar el proyecto, consultar los documentos relevantes:

```text
docs/functional-spec.md
docs/data-model.md
docs/testing-strategy.md
docs/architecture.md

Jerarquía:

functional-spec.md
        ↓
data-model.md
        ↓
testing-strategy.md
        ↓
architecture.md
        ↓
código

No inventar reglas de negocio que no estén definidas en estos documentos.

3. Regla STOP — OBLIGATORIA

"Si la tarea admite dos o más interpretaciones razonables, o requiere asunciones sobre el modelo de datos/negocio, está PROHIBIDO escribir código. Detén el flujo, presenta las alternativas y solicita confirmación."

Esta regla tiene prioridad sobre la velocidad de implementación.

Si existe una contradicción entre documentos, NO decidir por cuenta propia.

Detenerse, explicar la contradicción y solicitar confirmación.

4. Analizar antes de modificar

Antes de escribir o modificar código:

inspeccionar la estructura relevante;
consultar la documentación necesaria;
identificar archivos afectados;
identificar dependencias;
detectar posibles conflictos;
proponer el plan.

No modificar archivos durante una fase de análisis si la tarea solicitada es únicamente de análisis.

5. Cambios de modelo de datos

Está PROHIBIDO modificar el modelo de datos por iniciativa propia.

Cualquier cambio en:

tablas;
campos;
relaciones;
constraints;
estados;
enums;
reglas de persistencia;

requiere detenerse y solicitar confirmación si no está explícitamente definido en docs/data-model.md.

Un cambio aprobado debe actualizar:

docs/data-model.md

y la migración correspondiente.

6. Migraciones

Todo cambio estructural de base de datos debe realizarse mediante Alembic.

NO modificar manualmente crm.db para introducir cambios estructurales.

Después de una migración:

ejecutar los tests;
comprobar que la migración funciona desde una base limpia;
comprobar que no rompe los tests existentes.
7. Reglas de negocio

Las reglas de negocio deben implementarse en la capa de servicios.

No duplicar reglas importantes entre:

routes;
templates;
JavaScript;
services;
repositories.

Los repositories gestionan acceso a datos.

Los services gestionan lógica de negocio.

8. Homologación

La homologación tiene diferentes ámbitos:

GLOBAL
PROVINCIAL
OBRA

No asumir que:

documentación completa = homologación

La homologación requiere confirmación explícita cuando así lo establezca la especificación.

Debe mantenerse la diferencia entre:

estado actual

e

histórico de eventos

No eliminar el histórico para simplificar el estado actual.

9. Oportunidades y ofertas

La estructura comercial es:

Oportunidad
    ↓
Oferta
    ↓
Oferta_Versiones

No sustituir esta estructura por una solución simplificada sin autorización.

Una oportunidad y una oferta no son conceptos equivalentes.

Una oferta puede tener múltiples versiones.

La versión adjudicada puede ser diferente de la última versión o versión vigente.

10. Testing

Después de cualquier modificación funcional:

pytest

debe ejecutarse.

No considerar una tarea terminada si los tests relevantes fallan.

Los tests nunca deben utilizar accidentalmente la base de datos de producción/local:

crm.db
11. Cambios controlados

No realizar cambios no relacionados con la tarea.

Está prohibido introducir sin autorización:

nuevos frameworks;
nuevas dependencias importantes;
nuevas funcionalidades;
cambios de arquitectura;
cambios de modelo;
refactorizaciones amplias;
integraciones externas.

Si un cambio adicional parece necesario, explicarlo antes de ejecutarlo.

12. Planes

Para tareas complejas utilizar:

docs/plans/

Las plantillas, cuando correspondan, estarán en:

docs/plans/templates/

Un plan debe indicar como mínimo:

objetivo;
archivos afectados;
pasos;
riesgos;
tests;
criterios de aceptación.
13. Comunicación

Antes de una modificación relevante, informar brevemente:

Qué se va a hacer
Qué archivos se modificarán
Por qué
Qué tests se ejecutarán

Después:

Qué se ha hecho
Tests ejecutados
Resultado
Problemas pendientes

No ocultar errores ni declarar una tarea terminada si existen fallos conocidos.

14. Regla de documentación

La documentación de docs/ no debe modificarse para hacer que el código existente "encaje".

Si el código contradice la especificación:

detectar la contradicción;
detenerse;
explicar el problema;
solicitar decisión.

La documentación aprobada es la referencia.

15. Regla de simplicidad

Implementar la solución más sencilla que cumpla la especificación.

No introducir abstracciones, patrones o infraestructura innecesarios.

El proyecto es un CRM local monousuario.

No convertirlo en una arquitectura empresarial si la especificación no lo requiere.

16. Regla de seguridad

Nunca:

ejecutar comandos destructivos sin autorización;
borrar datos de producción;
sobrescribir crm.db sin necesidad explícita;
almacenar credenciales en el código;
introducir secretos en Git;
ejecutar código recibido desde datos del usuario.
17. Criterio de finalización

Una tarea se considera terminada únicamente cuando:

implementación
+
tests relevantes GREEN
+
documentación actualizada si corresponde

Si no se puede cumplir alguno de estos puntos, indicarlo explícitamente.

18. Orden de trabajo

Utilizar este flujo:

ANALYZE
   ↓
PLAN
   ↓
STOP / CONFIRM si existe ambigüedad
   ↓
IMPLEMENT
   ↓
TEST
   ↓
REPORT

Nunca saltar directamente de:

PROMPT → CÓDIGO

cuando la tarea requiera decisiones.

19. Prioridad

Prioridad de decisión:

instrucciones explícitas del usuario;
docs/functional-spec.md;
docs/data-model.md;
docs/testing-strategy.md;
docs/architecture.md;
este AGENTS.md;
convenciones técnicas del proyecto.

Si dos instrucciones del mismo nivel entran en conflicto, detenerse y preguntar.