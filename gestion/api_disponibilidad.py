"""
Algoritmo de disponibilidad combinada para reservas multi-servicio.

Dado un conjunto de servicios (con profesional fijo u opcional), una fecha,
y un cliente, calcula las secuencias contiguas válidas de turnos ordenadas
por score.

Usa bitmasks de disponibilidad (cada bit = SLOT_MINUTES minutos) para hacer
las verificaciones de colisión en O(1) por comparación.
"""
from datetime import datetime, timedelta
from django.utils import timezone
from .models import (
    Servicio, Profesional, Turno, Estacion, HorarioAtencion, HabilidadProfesional, CierreExcepcional
)

SLOT_MINUTES = 5
MAX_OPCIONES = 8


def _slots_en_rango(duracion_minutos):
    """Cuántos slots de SLOT_MINUTES caben en una duración."""
    return (duracion_minutos + SLOT_MINUTES - 1) // SLOT_MINUTES


def _time_to_slot(hora, hora_base):
    """Convierte un datetime/time a índice de slot relativo a hora_base."""
    if hasattr(hora, 'hour'):
        minutos = hora.hour * 60 + hora.minute
    else:
        minutos = hora
    base_min = hora_base.hour * 60 + hora_base.minute
    return (minutos - base_min) // SLOT_MINUTES


def _slot_to_time_str(slot_idx, hora_base):
    """Convierte un índice de slot a string HH:MM."""
    base_min = hora_base.hour * 60 + hora_base.minute
    total_min = base_min + slot_idx * SLOT_MINUTES
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def _build_bitmask(turnos_del_dia, fecha, hora_apertura, total_slots, key_fn):
    """
    Construye un dict de bitmasks {key: int} a partir de los turnos del día.
    key_fn extrae la clave de agrupación de cada turno (ej: profesional_id).
    Cada bit encendido = slot ocupado.
    """
    masks = {}
    for t in turnos_del_dia:
        key = key_fn(t)
        t_inicio = timezone.localtime(t.fecha_hora).replace(tzinfo=None)
        t_fin = timezone.localtime(t.hora_fin_estimada).replace(tzinfo=None)

        slot_ini = _time_to_slot(t_inicio.time(), hora_apertura)
        slot_fin = _time_to_slot(t_fin.time(), hora_apertura)

        slot_ini = max(0, slot_ini)
        slot_fin = min(total_slots, slot_fin)

        if slot_fin <= slot_ini:
            continue

        bits = ((1 << (slot_fin - slot_ini)) - 1) << slot_ini
        masks[key] = masks.get(key, 0) | bits

    return masks


def _is_range_free(mask, start_slot, n_slots):
    """Verifica si los slots [start_slot, start_slot+n_slots) están libres en el bitmask."""
    range_bits = ((1 << n_slots) - 1) << start_slot
    return (mask & range_bits) == 0


def _find_free_estacion(est_masks, estaciones_ids, start_slot, n_slots):
    """Busca la primera estación libre en el rango dado."""
    for est_id in estaciones_ids:
        mask = est_masks.get(est_id, 0)
        if _is_range_free(mask, start_slot, n_slots):
            return est_id
    return None


def calcular_disponibilidad(fecha, cliente_id, servicios_request, incluir_alternativas=True, hora_preferida=None):
    """
    Calcula secuencias contiguas válidas para un conjunto de servicios.

    Args:
        fecha: date
        cliente_id: int or None
        servicios_request: list of {
            "servicio_id": int,
            "profesional_id": int or None (None = cualquiera)
        }
        incluir_alternativas: bool - si True, también genera opciones ignorando
                                     las preferencias de profesional
        hora_preferida: str HH:MM or None
    """
    if not servicios_request:
        return {"opciones": [], "alternativas": []}

    # --- Pre-fetch ---
    dia_semana = fecha.weekday()
    horarios = list(HorarioAtencion.objects.filter(dia_semana=dia_semana, abierto=True))
    
    if not horarios:
        return {"opciones": [], "alternativas": [],
                "error": "El local está cerrado este día."}

    # Determinamos el rango total del día para la máscara
    hora_apertura = min(h.hora_apertura for h in horarios)
    hora_cierre = max(h.hora_cierre for h in horarios)
    total_slots = _time_to_slot(hora_cierre, hora_apertura)

    if total_slots <= 0:
        return {"opciones": [], "alternativas": []}

    # Máscara de "Cerrado por Horario" (todo ocupado por defecto)
    salon_mask = (1 << total_slots) - 1
    for h in horarios:
        s_ini = _time_to_slot(h.hora_apertura, hora_apertura)
        s_fin = _time_to_slot(h.hora_cierre, hora_apertura)
        range_bits = ((1 << (s_fin - s_ini)) - 1) << s_ini
        salon_mask &= ~range_bits

    # Máscara de "Cierres Excepcionales"
    cierres = CierreExcepcional.objects.filter(fecha=fecha)
    for c in cierres:
        if c.es_dia_completo:
            salon_mask = (1 << total_slots) - 1
            break
        else:
            s_ini = max(0, _time_to_slot(c.hora_inicio, hora_apertura))
            s_fin = min(total_slots, _time_to_slot(c.hora_fin, hora_apertura))
            if s_fin > s_ini:
                range_bits = ((1 << (s_fin - s_ini)) - 1) << s_ini
                salon_mask |= range_bits

    if salon_mask == (1 << total_slots) - 1:
        return {"opciones": [], "alternativas": [],
                "error": "El local está cerrado esta fecha."}

    # Turnos activos del día
    turnos_dia = list(
        Turno.objects.filter(fecha_hora__date=fecha)
        .exclude(estado__in=["cancelado", "completado"])
        .select_related("profesional", "estacion")
    )

    # Bitmasks
    prof_masks = _build_bitmask(turnos_dia, fecha, hora_apertura, total_slots,
                                lambda t: t.profesional_id)
    est_masks = _build_bitmask(turnos_dia, fecha, hora_apertura, total_slots,
                               lambda t: t.estacion_id)
    cliente_mask = salon_mask
    if cliente_id:
        cli_masks = _build_bitmask(turnos_dia, fecha, hora_apertura, total_slots,
                                   lambda t: t.cliente_id)
        cliente_mask |= cli_masks.get(int(cliente_id), 0)

    # Estaciones activas
    estaciones_ids = list(Estacion.objects.filter(activa=True).values_list("id", flat=True))

    # Resolver servicios y candidatos de profesional
    servicios_info = []
    for item in servicios_request:
        servicio = Servicio.objects.get(id=item["servicio_id"])
        prof_id = item.get("profesional_id")

        if prof_id:
            candidatos = [prof_id]
        else:
            candidatos = list(
                HabilidadProfesional.objects
                .filter(servicio_id=servicio.id, profesional__activo=True)
                .values_list("profesional_id", flat=True)
            )

        servicios_info.append({
            "servicio": servicio,
            "n_slots": _slots_en_rango(servicio.duracion_estimada),
            "candidatos": candidatos,
            "prof_fijo": prof_id,
        })

    # Calcular duración total en slots
    total_duracion_slots = sum(s["n_slots"] for s in servicios_info)

    # Filtrar por hora actual si la fecha es hoy
    ahora = timezone.localtime(timezone.now()).replace(tzinfo=None)
    min_slot = 0
    if fecha == ahora.date():
        minutos_faltantes = (SLOT_MINUTES - (ahora.minute % SLOT_MINUTES)) % SLOT_MINUTES
        proximo = ahora + timedelta(minutes=minutos_faltantes)
        proximo = proximo.replace(second=0, microsecond=0)
        min_slot = max(0, _time_to_slot(proximo.time(), hora_apertura))

    # Slot preferido
    pref_slot = None
    if hora_preferida:
        try:
            # Soportar HH:MM y HH:MM:SS
            h_str = hora_preferida[:5]
            h_pref = datetime.strptime(h_str, '%H:%M').time()
            pref_slot = _time_to_slot(h_pref, hora_apertura)
        except (ValueError, TypeError, IndexError):
            pass

    # --- Búsqueda de secuencias ---
    opciones = _buscar_secuencias(
        servicios_info, total_slots, total_duracion_slots, min_slot,
        prof_masks, est_masks, cliente_mask, estaciones_ids,
        hora_apertura, pref_slot=pref_slot
    )

    alternativas = []
    if incluir_alternativas:
        servicios_flex = []
        hay_algun_fijo = any(s["prof_fijo"] for s in servicios_info)

        if hay_algun_fijo:
            for s in servicios_info:
                candidatos_flex = list(
                    HabilidadProfesional.objects
                    .filter(servicio_id=s["servicio"].id, profesional__activo=True)
                    .values_list("profesional_id", flat=True)
                )
                servicios_flex.append({
                    "servicio": s["servicio"],
                    "n_slots": s["n_slots"],
                    "candidatos": candidatos_flex,
                    "prof_fijo": None,
                })

            alternativas = _buscar_secuencias(
                servicios_flex, total_slots, total_duracion_slots, min_slot,
                prof_masks, est_masks, cliente_mask, estaciones_ids,
                hora_apertura, pref_slot=pref_slot
            )

            # Eliminar alternativas que ya están en opciones por combinación de profesionales
            claves_opciones = {
                tuple(b["profesional_id"] for b in o["bloques"]) for o in opciones
            }
            alternativas = [
                a for a in alternativas
                if tuple(b["profesional_id"] for b in a["bloques"]) not in claves_opciones
            ]

    return {"opciones": opciones[:MAX_OPCIONES], "alternativas": alternativas[:MAX_OPCIONES]}


def _buscar_secuencias(servicios_info, total_slots, total_duracion_slots, min_slot,
                       prof_masks, est_masks, cliente_mask, estaciones_ids,
                       hora_apertura, pref_slot=None):
    """
    Para cada slot de inicio posible, enumera TODAS las combinaciones válidas
    de profesionales usando backtracking. Prioriza combinaciones en el horario
    más temprano (o cercano al preferido) antes de avanzar al siguiente slot.
    """
    max_start = total_slots - total_duracion_slots
    if max_start < min_slot:
        return []

    # Pre-fetch nombres de profesionales (evita N+1 dentro del backtracking)
    todos_candidatos = set()
    for s in servicios_info:
        todos_candidatos.update(s["candidatos"])
    profs_map = {
        p.id: f"{p.nombre} {p.apellido}"
        for p in Profesional.objects.filter(id__in=todos_candidatos)
    }

    resultados = []
    combinaciones_vistas = set()  # (start_slot, prof_tuple) para deduplicar

    if pref_slot is not None:
        # Prioridad absoluta: Buscar en una ventana de +/- 3 horas (36 slots de 5 min)
        ventana = 36 
        rango_ventana = range(max(min_slot, pref_slot - ventana), min(max_start + 1, pref_slot + ventana + 1))
        
        # Ordenar los slots dentro de la ventana por cercanía exacta
        cercanos = sorted(list(rango_ventana), key=lambda s: abs(s - pref_slot))
        
        # El resto del día queda como último recurso
        lejanos = [s for s in range(min_slot, max_start + 1) if s not in rango_ventana]
        slots_to_check = cercanos + lejanos
    else:
        slots_to_check = range(min_slot, max_start + 1)

    for start_slot in slots_to_check:
        nuevas = _enumerar_combinaciones(
            servicios_info, start_slot,
            prof_masks, est_masks, cliente_mask, estaciones_ids,
            hora_apertura, profs_map, MAX_OPCIONES, pref_slot=pref_slot
        )
        for sec in nuevas:
            clave = (start_slot, tuple(b["profesional_id"] for b in sec["bloques"]))
            if clave not in combinaciones_vistas:
                combinaciones_vistas.add(clave)
                resultados.append(sec)

        if len(resultados) >= MAX_OPCIONES * 4: # Más margen para tener de dónde elegir
            break

    # Si hay horario preferido, nos aseguramos de que el score sea dominado por la cercanía
    # y re-ordenamos para garantizar que la opción más cercana sea la primera.
    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados


def _enumerar_combinaciones(servicios_info, start_slot, prof_masks, est_masks,
                            cliente_mask, estaciones_ids, hora_apertura,
                            profs_map, max_resultados, pref_slot=None):
    """
    Backtracking recursivo: para un slot de inicio fijo, genera todas las
    asignaciones válidas de profesionales a los servicios.
    """
    resultados = []

    def backtrack(idx, slot_actual, bloques, prof_temp, est_temp, cli_temp,
                  prof_anterior, score):
        if len(resultados) >= max_resultados:
            return

        if idx == len(servicios_info):
            duracion_total = sum(b["duracion"] for b in bloques)
            
            # Cálculo de score base
            final_score = score
            
            if pref_slot is not None:
                # El score es dominado totalmente por la cercanía (10,000 puntos base)
                distancia = abs(start_slot - pref_slot)
                # Cada minuto de diferencia resta 1 punto. 10,000 es suficiente para 
                # cubrir todo el día y que la cercanía siempre gane.
                final_score = 10000 - (distancia * SLOT_MINUTES)
                # Agregamos el score de calidad (profesionales) como decimal para desempatar
                final_score += (score / 1000.0)
            else:
                # Si no hay preferencia, priorizar temprano
                final_score = score + max(0, 100 - start_slot // 2)

            resultados.append({
                "inicio": bloques[0]["inicio"],
                "fin": bloques[-1]["fin"],
                "duracion_total": duracion_total,
                "score": final_score,
                "bloques": [dict(b) for b in bloques],
            })
            return

        s_info = servicios_info[idx]
        n_slots = s_info["n_slots"]

        # Cliente libre en este rango
        if not _is_range_free(cliente_mask | cli_temp, slot_actual, n_slots):
            return

        range_bits = ((1 << n_slots) - 1) << slot_actual

        for prof_id in s_info["candidatos"]:
            if len(resultados) >= max_resultados:
                return

            # Profesional libre
            if not _is_range_free(
                prof_masks.get(prof_id, 0) | prof_temp.get(prof_id, 0),
                slot_actual, n_slots
            ):
                continue

            # Estación libre
            est_elegido = None
            for est_id in estaciones_ids:
                if _is_range_free(
                    est_masks.get(est_id, 0) | est_temp.get(est_id, 0),
                    slot_actual, n_slots
                ):
                    est_elegido = est_id
                    break

            if est_elegido is None:
                continue

            score_delta = 0
            if prof_anterior is not None:
                score_delta = 20 if prof_id == prof_anterior else -5

            bloque = {
                "servicio_id": s_info["servicio"].id,
                "servicio_nombre": s_info["servicio"].nombre,
                "profesional_id": prof_id,
                "profesional_nombre": profs_map.get(prof_id, "?"),
                "estacion_id": est_elegido,
                "inicio": _slot_to_time_str(slot_actual, hora_apertura),
                "fin": _slot_to_time_str(slot_actual + n_slots, hora_apertura),
                "duracion": s_info["servicio"].duracion_estimada,
            }

            new_prof = dict(prof_temp)
            new_prof[prof_id] = new_prof.get(prof_id, 0) | range_bits
            new_est = dict(est_temp)
            new_est[est_elegido] = new_est.get(est_elegido, 0) | range_bits

            backtrack(
                idx + 1, slot_actual + n_slots,
                bloques + [bloque],
                new_prof, new_est, cli_temp | range_bits,
                prof_id, score + score_delta
            )

    backtrack(0, start_slot, [], {}, {}, 0, None, 100)
    return resultados
