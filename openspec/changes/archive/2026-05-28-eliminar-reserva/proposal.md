# Proposal: Eliminar Tabla Reserva

## Intent
Eliminar deuda técnica de la jerarquía Reserva+Turno. Simplificar a 1 Turno = 1 visita con N DetalleTurno, moviendo profesional/estación a DetalleTurno.

## Scope

### In Scope
- Modelos: DetalleTurno (+profesional, +estacion, +hora_inicio, +hora_fin); Turno (+token, -profesional, -estacion, -reserva, -orden); eliminar modelo Reserva
- Migración de datos: poblar DetalleTurno desde Turno, poblar tokens, migrar observaciones
- Vistas creación: refactor reservar_turno_interno y confirmar_reserva_publica a 1 Turno + N DetalleTurno
- Portal público: rutas y vistas de reserva.token → turno.token
- Dashboard: filtros profesional/estacion via DetalleTurno, eliminar reserva_filtro
- Facturación: comisiones multi-profesional desde DetalleTurno
- API disponibilidad: bitmasks usar DetalleTurno (sin cambio estructural)
- API legada api.py: actualizar t.profesional_id / t.estacion_id a DetalleTurno lookup
- Tests: test_public_reserva.py, test_concurrencia.py, test_dashboard.py
- 8 templates: gestion_publica, cancelar_publica, confirmacion_publica, _modal_cancelacion, _turno_card_diaria, _turno_card_semanal, dashboard, facturar
- URLs: 5 rutas renombradas de reserva → turno

### Out of Scope
- Algoritmo de disponibilidad (F3) — solo documentación
- Nuevo modelo ComisionDetalle (split de comisión multi-profesional) — se calcula en vista, no se crea modelo nuevo
- UX/UI rediseño de pantallas existentes

## Capabilities

### New Capabilities
None — refactor puro, sin nuevas capacidades para el usuario.

### Modified Capabilities
- `booking-flow`: creación de visitas sin Reserva, directo 1 Turno + N DetalleTurno
- `public-booking`: portal público usa turno.token en vez de reserva.token
- `billing`: comisiones calculadas por DetalleTurno.profesional

## Approach
9 fases secuenciales: F1 (modelos + schema migration) → F2 (data migration) → F4 (vistas creación) → F5 (portal público + URLs + templates) → F7 (dashboard) → F6 (facturación + comisiones) → F3 (documentación API disp.) → F8 (limpieza modelo) → F9 (tests). Cada fase reversible hasta F8.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| models/turnos.py | Modified | DetalleTurno +4 fields, Turno +token -4 fields, -Reserva |
| models/ventas.py | None | Cálculo cambia en vista, modelo no se modifica |
| views/reservas.py | Modified | Creación 1 Turno + N DetalleTurno |
| views/turnos.py | Modified | Comisión multi-profesional, cancelación url por turno.token |
| views/dashboard.py | Modified | Filtros via DetalleTurno, -reserva_filtro, prefetch anidado |
| views/api.py | Modified | t.profesional_id → DetalleTurno lookup |
| views/reportes.py | Modified | turno__profesional → detalleturno__profesional |
| urls.py | Modified | 5 rutas: reserva/publica/* → turnos/publica/* |
| 8 templates | Modified | reserva → turno, profesional/estacion via DetalleTurno |
| tests/ (3 files) | Modified | Sin Reserva, Turno sin profesional/estacion directos |
| forms.py | Modified | Eliminar ReservaAlPasoForm |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| UniqueConstraint (turno+servicio) rompe si mismo servicio aparece 2 veces con distinto profesional | Med | Extender a (turno+servicio+profesional) o eliminar constraint |
| Venta.comision con multi-profesional subestima si usa un solo profesional | High | Opción A desde F6: iterar DetalleTurno, sumar comisiones individuales |
| API legada api.py omite bloqueo prof/estacion por DetalleTurno | High | Incluir en alcance, actualizar lookup a DetalleTurno |
| Tests crean Reserva.objects.create() directamente | Med | Actualizar todos los tests, crear Turno sin Reserva |
| Data loss en migración (observaciones, tokens) | Med | F2 en staging, backup BD antes de F8 (drop columns) |

## Open Questions

1. **UniqueConstraint DetalleTurno**: ¿Extender a (turno, servicio, profesional) o eliminar constraint? Riesgo: mismo servicio dos veces con distinto profesional en un mismo turno.
2. **Comisiones multi-profesional**: Opción A (iterar DetalleTurno, sumar comisión individual por profesional, mantener Venta.comision como agregado) vs Opción B (usar solo primer profesional).
3. **Turno.clean()**: ¿Simplificar solo horario de atención (plan original F4) o mantener validación de solapamiento de cliente?

## Rollback Plan
Mantener modelo Reserva y campos viejos (profesional, estacion, reserva, orden) hasta F8. Cada fase F1-F7 es reversible. Rollback completo: restaurar migración anterior + código pre-cambio.

## Dependencies
- F1 → F2 → F4 → F5 → F7 → F6 → F3 → F8 → F9 (orden estricto)
- F7 (dashboard) depende de F4 (vistas creación) para datos consistentes
- F6 (facturación) requiere respuesta a Open Question #2 antes de implementar

## Success Criteria
- [ ] Migración ejecutada sin pérdida de datos en staging
- [ ] Tests existentes pasan con assertions actualizadas (sin Reserva)
- [ ] Portal público funcional con turno.token (crear, gestionar, cancelar)
- [ ] Filtros dashboard por profesional/estación via DetalleTurno
- [ ] Facturación calcula comisiones correctas con múltiples profesionales
- [ ] API legada api.py devuelve horarios correctos
