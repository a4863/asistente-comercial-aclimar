# Implement Task

## Purpose

Implementar exclusivamente un plan previamente analizado y aprobado.

Este Skill solo puede ejecutar cambios definidos mediante:

1. análisis;
2. plan;
3. Scope Lock;
4. aprobación explícita.

Este Skill NO realiza análisis funcional autónomo ni toma decisiones de negocio, arquitectura, seguridad o modelo de datos.

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

Informar de qué elemento falta.

---

## CRITICAL RULE

La implementación debe limitarse estrictamente al plan aprobado y al Scope Lock.

No ampliar el alcance.

No resolver problemas no incluidos en el plan.

No tomar decisiones funcionales, arquitectónicas, de seguridad o modelo de datos no aprobadas.

Si durante la implementación aparece una decisión no contemplada:

STOP.

Presentar:

- problema;
- alternativas;
- consecuencias;
- decisión necesaria.

No continuar hasta recibir aprobación.

---

## Rules

Antes de modificar código:

1. Leer `AGENTS.md`.
2. Leer el plan aprobado.
3. Leer el Scope Lock.
4. Leer la documentación relevante.
5. Inspeccionar los elementos afectados.
6. Confirmar que la implementación coincide con el plan.
7. Implementar únicamente los cambios aprobados.

---

## Documentation as Contract

La documentación aprobada constituye la referencia funcional, arquitectónica, de datos, seguridad y testing.

Consultar cuando