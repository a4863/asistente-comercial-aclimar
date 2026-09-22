# Phase 2B Decisions

**Fecha:** 2026-09-22
**Estado:** APPROVED

## D1. Follow-up scope mapping

**Decisión:** C — combinado.

- El CRM es la fuente principal para determinar la regla aplicable cuando exista contexto suficiente de oportunidad, oferta u obra.
- La clasificación manual del asistente solo se usa cuando no haya contexto CRM suficiente.
- Una clasificación manual no sobrescribe ni reemplaza silenciosamente un hecho CRM confirmado.

## D2. Automatic overdue timing

**Decisión:** B — evaluación periódica mediante scheduler.

- Phase 2B define y prueba la operación de evaluación de vencimiento.
- La integración concreta con APScheduler puede implementarse en una fase posterior.
- Una Commitment confirmada con due date vencida puede pasar automáticamente a overdue.
- Ninguna transición automática puede marcar fulfilled.

## D3. Alert lifecycle

**Decisión:** aprobado.

Lifecycle:

`active -> resolved | dismissed`

Reglas:

- creación automática cuando se cumple una condición;
- deduplicación por `alert_type + target_type + target_id + condition_key`;
- si la condición deja de cumplirse, la alerta puede pasar automáticamente a `resolved`;
- `dismissed` requiere acción explícita del usuario;
- si una condición ya resuelta vuelve a aparecer, se crea una nueva alerta;
- no reutilizar una alerta resuelta como si nunca hubiera existido;
- una Alert no sustituye Facts, Inferences, Tasks ni Commitments.
