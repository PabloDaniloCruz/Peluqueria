import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from datetime import timedelta, datetime

from ..models import (
    Cliente, Turno, DetalleTurno, DetalleEtapa, Estacion, Profesional,
    Servicio, HorarioAtencion,
)

from ..api_disponibilidad import calcular_disponibilidad


def reservar_turno_publico(request):
    """GET — Renderizar wizard público multi-servicio."""
    servicios_qs = Servicio.objects.filter(activo=True).prefetch_related('etapas')
    servicios = [{
        'id': s.id,
        'nombre': s.nombre,
        'descripcion': s.descripcion,
        'precio_sugerido': s.precio_sugerido,
        'duracion_estimada': s.duracion_estimada,
        'orden_sugerido': s.orden_sugerido,
        'etapas': [{'nombre': e.nombre, 'duracion': e.duracion} for e in s.etapas.all()]
    } for s in servicios_qs]
    profesionales = [
        {
            'id': p.id,
            'nombre': f"{p.nombre} {p.apellido}",
            'habilidades': list(p.habilidades.values_list('id', flat=True))
        } for p in Profesional.objects.filter(activo=True)
    ]

    # Horarios de atención para el picker
    horarios = list(HorarioAtencion.objects.filter(abierto=True).values(
        'dia_semana', 'hora_apertura', 'hora_cierre'
    ))

    # Reprogramación pública
    repro_id = request.GET.get('repro_id')
    token_str = request.GET.get('token')
    pre_load = None
    if repro_id and token_str:
        try:
            turno = Turno.objects.get(id=repro_id, token=token_str)
            if turno.estado in ['pendiente', 'por_reprogramar']:
                pre_load = {
                    'cliente_id': turno.cliente.id,
                    'nombre': turno.cliente.nombre,
                    'apellido': turno.cliente.apellido,
                    'dni': turno.cliente.dni or '',
                    'telefono': turno.cliente.telefono,
                    'servicios_ids': list(turno.servicios.values_list('id', flat=True)),
                    'repro_id': turno.id,
                    'msg': f"Reprogramando tu Turno de {turno.cliente.nombre}"
                }
        except (Turno.DoesNotExist, ValueError):
            pass

    contexto = {
        'servicios_json': json.dumps(servicios, default=str),
        'profesionales_json': json.dumps(profesionales),
        'horarios_json': json.dumps(horarios, default=str),
        'fecha_hoy': timezone.now().date().isoformat(),
        'pre_load_json': json.dumps(pre_load) if pre_load else None,
    }
    return render(request, 'gestion/reserva_publica_wizard.html', contexto)


@login_required
def reservar_turno_interno(request):
    """Vista wizard para reserva interna multi-servicio con agenda continua."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos inválidos.'}, status=400)

        observaciones = data.get('observaciones', '').strip()

        # Resolver o crear cliente
        cliente_id = data.get('cliente_id')
        if cliente_id:
            cliente = get_object_or_404(Cliente, id=cliente_id)
        else:
            nombre = data.get('nombre', '').strip()
            apellido = data.get('apellido', '').strip()
            dni = data.get('dni', '').strip()
            telefono = data.get('telefono', '').strip()
            if not all([nombre, apellido, dni]):
                return JsonResponse({'error': 'Nombre, apellido y DNI son obligatorios.'}, status=400)
            cliente, creado = Cliente.objects.get_or_create(
                dni=dni,
                defaults={'nombre': nombre, 'apellido': apellido, 'telefono': telefono}
            )
            if not creado:
                # Actualizar datos de contacto si el cliente ya existía
                if cliente.nombre != nombre or cliente.apellido != apellido or cliente.telefono != telefono:
                    cliente.nombre = nombre
                    cliente.apellido = apellido
                    cliente.telefono = telefono
                    cliente.save(update_fields=['nombre', 'apellido', 'telefono'])

        opcion = data.get('opcion')
        if not opcion or not opcion.get('bloques'):
            return JsonResponse({'error': 'No se seleccionó una opción de horario.'}, status=400)

        fecha_str = data.get('fecha')
        if not fecha_str:
            return JsonResponse({'error': 'Fecha no especificada.'}, status=400)

        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha inválido.'}, status=400)

        # Crear Turno + Detalles dentro de una transacción atómica
        try:
            with transaction.atomic():
                # Bloqueamos el cliente para actualizaciones seguras
                cliente = Cliente.objects.select_for_update().get(id=cliente.id)

                # Si estamos reprogramando, cancelamos el turno viejo para liberar espacio
                repro_id = data.get('repro_id')
                if repro_id:
                    old_turno = Turno.objects.filter(id=repro_id).first()
                    if old_turno:
                        old_turno.estado = 'cancelado'
                        old_obs = old_turno.observaciones or ''
                        old_turno.observaciones = old_obs + f"\n[Cancelado por reprogramación el {timezone.now().strftime('%d/%m %H:%M')}]"
                        old_turno.save()

                # Calcular rango total del turno
                primer_inicio = datetime.strptime(opcion['bloques'][0]['inicio'], '%H:%M').time()
                ultimo_fin = datetime.strptime(opcion['bloques'][-1]['fin'], '%H:%M').time()
                fecha_hora = timezone.make_aware(datetime.combine(fecha, primer_inicio))
                hora_fin_estimada = timezone.make_aware(datetime.combine(fecha, ultimo_fin))

                turno = Turno(
                    cliente=cliente,
                    fecha_hora=fecha_hora,
                    hora_fin_estimada=hora_fin_estimada,
                    estado='pendiente',
                    observaciones=observaciones,
                )
                turno.clean()
                turno.save()

                turnos_creados = 0

                for bloque in opcion['bloques']:
                    servicio = Servicio.objects.get(id=bloque['servicio_id'])
                    profesional_obj = Profesional.objects.get(id=bloque['profesional_id'])
                    h_inicio = datetime.strptime(bloque['inicio'], '%H:%M').time()
                    h_fin = datetime.strptime(bloque['fin'], '%H:%M').time()

                    dt = DetalleTurno.objects.create(
                        turno=turno,
                        servicio=servicio,
                        profesional=profesional_obj,
                        precio_real=servicio.precio_sugerido,
                        hora_inicio=h_inicio,
                        hora_fin=h_fin,
                    )

                    # Crear DetalleEtapa por cada etapa del servicio
                    for etapa in bloque.get('estaciones_asignadas', []):
                        DetalleEtapa.objects.create(
                            detalle=dt,
                            etapa_servicio_id=etapa['etapa_servicio_id'],
                            estacion_id=etapa['estacion_id'] if etapa.get('estacion_id', -1) != -1 else None,
                            hora_inicio=etapa['hora_inicio'],
                            hora_fin=etapa['hora_fin'],
                        )
                    turnos_creados += 1

            # Generar URL de WhatsApp para enviar el comprobante y token de autogestión al cliente
            import urllib.parse
            import re

            detalles_texto = ""
            for dt in turno.detalleturno_set.all():
                fecha_local = timezone.localtime(turno.fecha_hora)
                detalles_texto += f"\n- {fecha_local.strftime('%d/%m a las %H:%M')}hs: {dt.servicio.nombre} con {dt.profesional.nombre}"

            url_gestion = request.build_absolute_uri(f'/turnos/publica/confirmacion/{turno.token}/')
            mensaje_wa = f"¡Hola {cliente.nombre}! Registramos tu turno en Studio Salta:{detalles_texto}\n\nPodés gestionar, reprogramar o cancelar tu reserva desde acá: {url_gestion}"
            mensaje_wa_encoded = urllib.parse.quote(mensaje_wa)

            # Limpiar el número de teléfono del cliente para wa.me (solo dígitos, agregar 549 si tiene 10 dígitos)
            telefono_limpio = re.sub(r'\D', '', cliente.telefono)
            if not telefono_limpio.startswith('54') and len(telefono_limpio) == 10:
                telefono_limpio = '549' + telefono_limpio

            whatsapp_url = f"https://wa.me/{telefono_limpio}?text={mensaje_wa_encoded}"

            return JsonResponse({
                'success': True,
                'message': f'Se registraron {turnos_creados} servicio(s) para {cliente}.',
                'redirect': '/',
                'whatsapp_url': whatsapp_url
            })

        except ValidationError as e:
            return JsonResponse({'error': '; '.join(e.messages)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # GET — Renderizar wizard
    servicios_qs = Servicio.objects.filter(activo=True).prefetch_related('etapas')
    servicios = [{
        'id': s.id,
        'nombre': s.nombre,
        'descripcion': s.descripcion,
        'precio_sugerido': s.precio_sugerido,
        'duracion_estimada': s.duracion_estimada,
        'orden_sugerido': s.orden_sugerido,
        'etapas': [{'nombre': e.nombre, 'duracion': e.duracion} for e in s.etapas.all()]
    } for s in servicios_qs]
    profesionales = [
        {
            'id': p.id,
            'nombre': f"{p.nombre} {p.apellido}",
            'habilidades': list(p.habilidades.values_list('id', flat=True))
        } for p in Profesional.objects.filter(activo=True)
    ]

    # Horarios de atención para el picker
    horarios = list(HorarioAtencion.objects.filter(abierto=True).values(
        'dia_semana', 'hora_apertura', 'hora_cierre'
    ))

    contexto = {
        'servicios_json': json.dumps(servicios, default=str),
        'profesionales_json': json.dumps(profesionales),
        'horarios_json': json.dumps(horarios, default=str),
        'fecha_hoy': timezone.now().date().isoformat(),
    }
    return render(request, 'gestion/reserva_interna.html', contexto)


@login_required
def reprogramar_turno(request, pk):
    """
    Pre-carga el wizard de reserva interna con los datos de un turno 
    que necesita ser movido (ej. por un cierre excepcional).
    """
    turno = get_object_or_404(Turno, id=pk)
    
    # Datos básicos del cliente
    pre_load = {
        'cliente_id': turno.cliente.id,
        'nombre': turno.cliente.nombre,
        'apellido': turno.cliente.apellido,
        'dni': turno.cliente.dni or '',
        'telefono': turno.cliente.telefono,
        'servicios_ids': list(turno.servicios.values_list('id', flat=True)),
        'repro_id': turno.id,
        'observaciones': turno.observaciones,
        'msg': f"Reprogramando Turno #{turno.id} de {turno.cliente}"
    }

    # Reutilizamos la lógica de cargar servicios y profesionales
    servicios_qs = Servicio.objects.filter(activo=True).prefetch_related('etapas')
    servicios = [{
        'id': s.id,
        'nombre': s.nombre,
        'descripcion': s.descripcion,
        'precio_sugerido': s.precio_sugerido,
        'duracion_estimada': s.duracion_estimada,
        'orden_sugerido': s.orden_sugerido,
        'etapas': [{'nombre': e.nombre, 'duracion': e.duracion} for e in s.etapas.all()]
    } for s in servicios_qs]
    profesionales = [
        {
            'id': p.id,
            'nombre': f"{p.nombre} {p.apellido}",
            'habilidades': list(p.habilidades.values_list('id', flat=True))
        } for p in Profesional.objects.filter(activo=True)
    ]
    horarios = list(HorarioAtencion.objects.filter(abierto=True).values(
        'dia_semana', 'hora_apertura', 'hora_cierre'
    ))

    contexto = {
        'servicios_json': json.dumps(servicios, default=str),
        'profesionales_json': json.dumps(profesionales),
        'horarios_json': json.dumps(horarios, default=str),
        'fecha_hoy': timezone.now().date().isoformat(),
        'pre_load_json': json.dumps(pre_load),
    }
    return render(request, 'gestion/reserva_interna.html', contexto)



@login_required
@require_POST
def api_disponibilidad_combinada(request):
    """API que calcula secuencias contiguas válidas para múltiples servicios."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    fecha_str = data.get('fecha')
    hora_preferida = data.get('hora_preferida')
    cliente_id = data.get('cliente_id')
    servicios_req = data.get('servicios', [])

    if not fecha_str or not servicios_req:
        return JsonResponse({'error': 'Faltan fecha o servicios.'}, status=400)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido.'}, status=400)

    try:
        resultado = calcular_disponibilidad(fecha, cliente_id, servicios_req, hora_preferida=hora_preferida)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse(resultado)


@require_POST
def api_disponibilidad_publica(request):
    """API pública que calcula secuencias de disponibilidad con control de saturación previo."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    fecha_str = data.get('fecha')
    hora_preferida = data.get('hora_preferida')
    servicios_req = data.get('servicios', [])
    dni = data.get('dni', '').strip()
    telefono = data.get('telefono', '').strip()

    if not fecha_str or not servicios_req:
        return JsonResponse({'error': 'Faltan fecha o servicios.'}, status=400)

    if not dni:
        return JsonResponse({'error': 'Por favor, ingresá tu DNI.'}, status=400)

    if not telefono:
        return JsonResponse({'error': 'Por favor, ingresá tu teléfono.'}, status=400)

    # Control de saturación preventivo (máximo 2 turnos a futuro)
    cliente = Cliente.objects.filter(dni=dni).first()
    if cliente:
        turnos_pendientes = Turno.objects.filter(
            cliente=cliente,
            fecha_hora__gte=timezone.now()
        ).exclude(estado='cancelado').count()
        if turnos_pendientes >= 2:
            return JsonResponse({
                'error': 'Ya tenés 2 turnos reservados a futuro. Por favor, asistí o cancelá uno antes de agendar más.'
            }, status=200)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido.'}, status=400)

    try:
        cliente_id = cliente.id if cliente else None
        resultado = calcular_disponibilidad(fecha, cliente_id, servicios_req, hora_preferida=hora_preferida)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse(resultado)


@require_POST
def confirmar_reserva_publica(request):
    """Confirma la reserva pública multi-servicio de forma atómica y segura contra condiciones de carrera."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)

    nombre = data.get('nombre', '').strip()
    apellido = data.get('apellido', '').strip()
    dni = data.get('dni', '').strip()
    telefono = data.get('telefono', '').strip()
    observaciones = data.get('observaciones', '').strip()

    if not all([nombre, apellido, dni]):
        return JsonResponse({'error': 'Nombre, apellido y DNI son obligatorios.'}, status=400)

    if not telefono:
        return JsonResponse({'error': 'El teléfono de WhatsApp es obligatorio.'}, status=400)

    opcion = data.get('opcion')
    if not opcion or not opcion.get('bloques'):
        return JsonResponse({'error': 'No se seleccionó una opción de horario.'}, status=400)

    fecha_str = data.get('fecha')
    if not fecha_str:
        return JsonResponse({'error': 'Fecha no especificada.'}, status=400)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido.'}, status=400)

    try:
        with transaction.atomic():
            # 1. Buscar o crear el cliente por DNI de manera segura
            cliente, creado = Cliente.objects.get_or_create(
                dni=dni,
                defaults={'nombre': nombre, 'apellido': apellido, 'telefono': telefono}
            )
            # Si el cliente ya existía, actualizar datos de contacto si cambió
            if not creado:
                if cliente.nombre != nombre or cliente.apellido != apellido or cliente.telefono != telefono:
                    cliente.nombre = nombre
                    cliente.apellido = apellido
                    cliente.telefono = telefono
                    cliente.save(update_fields=['nombre', 'apellido', 'telefono'])

            # 2. Bloqueamos el cliente para actualizaciones seguras
            cliente = Cliente.objects.select_for_update().get(id=cliente.id)

            # Si estamos reprogramando, cancelamos el turno viejo para liberar espacio
            repro_id = data.get('repro_id')
            if repro_id:
                old_turno = Turno.objects.filter(id=repro_id).first()
                if old_turno:
                    old_turno.estado = 'cancelado'
                    old_obs = old_turno.observaciones or ''
                    old_turno.observaciones = old_obs + f"\n[Cancelado por reprogramación del cliente el {timezone.now().strftime('%d/%m %H:%M')}]"
                    old_turno.save()

            # 3. CONTROL DE SATURACIÓN FINAL: Límite estricto de 2 turnos a futuro
            turnos_pendientes = Turno.objects.filter(
                cliente=cliente,
                fecha_hora__gte=timezone.now()
            ).exclude(estado='cancelado').count()
            
            if turnos_pendientes >= 2:
                return JsonResponse({
                    'error': 'Ya tenés 2 turnos reservados a futuro. Por favor, asistí o cancelá uno antes de agendar más.'
                }, status=400)

            # Calcular rango total del turno
            primer_inicio = datetime.strptime(opcion['bloques'][0]['inicio'], '%H:%M').time()
            ultimo_fin = datetime.strptime(opcion['bloques'][-1]['fin'], '%H:%M').time()
            fecha_hora = timezone.make_aware(datetime.combine(fecha, primer_inicio))
            hora_fin_estimada = timezone.make_aware(datetime.combine(fecha, ultimo_fin))

            turno = Turno(
                cliente=cliente,
                fecha_hora=fecha_hora,
                hora_fin_estimada=hora_fin_estimada,
                estado='pendiente',
                observaciones=observaciones,
            )
            turno.clean()
            turno.save()

            turnos_creados = 0

            for bloque in opcion['bloques']:
                servicio = Servicio.objects.get(id=bloque['servicio_id'])
                profesional_obj = Profesional.objects.get(id=bloque['profesional_id'])
                h_inicio = datetime.strptime(bloque['inicio'], '%H:%M').time()
                h_fin = datetime.strptime(bloque['fin'], '%H:%M').time()

                dt = DetalleTurno.objects.create(
                    turno=turno,
                    servicio=servicio,
                    profesional=profesional_obj,
                    precio_real=servicio.precio_sugerido,
                    hora_inicio=h_inicio,
                    hora_fin=h_fin,
                )

                # Crear DetalleEtapa por cada etapa del servicio
                for etapa in bloque.get('estaciones_asignadas', []):
                    DetalleEtapa.objects.create(
                        detalle=dt,
                        etapa_servicio_id=etapa['etapa_servicio_id'],
                        estacion_id=etapa['estacion_id'] if etapa.get('estacion_id', -1) != -1 else None,
                        hora_inicio=etapa['hora_inicio'],
                        hora_fin=etapa['hora_fin'],
                    )
                turnos_creados += 1

        return JsonResponse({
            'success': True,
            'message': f'¡Se reservaron con éxito tus {turnos_creados} servicio(s) en Studio Salta!',
            'redirect': f'/turnos/publica/confirmacion/{turno.token}/'
        })

    except ValidationError as e:
        return JsonResponse({'error': '; '.join(e.messages)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def confirmacion_turno_publico(request, token):
    """Muestra la pantalla de éxito con botones dinámicos para WhatsApp, calendario y copiado."""
    from django.conf import settings
    turno = get_object_or_404(Turno, token=token)
    detalles = turno.detalleturno_set.select_related('servicio', 'profesional').prefetch_related(
        'etapas_asignadas__estacion', 'etapas_asignadas__etapa_servicio'
    ).all()
    
    # Armar texto para WhatsApp
    detalles_texto = ""
    for dt in detalles:
        fecha_local = timezone.localtime(turno.fecha_hora)
        detalles_texto += f"\n- {fecha_local.strftime('%d/%m a las %H:%M')}hs: {dt.servicio.nombre} con {dt.profesional.nombre}"
    
    url_gestion = request.build_absolute_uri(f'/turnos/publica/gestion/{token}/')
    
    import urllib.parse
    mensaje_wa = f"¡Hola! Agendé mi turno en Studio Salta:{detalles_texto}\n\nLink para gestionar o reprogramar mi turno: {url_gestion}"
    mensaje_wa_encoded = urllib.parse.quote(mensaje_wa)
    
    salon_telefono = getattr(settings, 'SALON_WHATSAPP', '5493875551234')
    whatsapp_url = f"https://wa.me/{salon_telefono}?text={mensaje_wa_encoded}"
    
    google_calendar_url = None
    if turno.fecha_hora:
        start_time = turno.fecha_hora.strftime('%Y%m%dT%H%M%SZ')
        end_time = turno.hora_fin_estimada.strftime('%Y%m%dT%H%M%SZ') if turno.hora_fin_estimada else start_time
        title = "Turno en Studio Salta"
        details = f"Gestionar tu turno aquí: {url_gestion}"
        google_calendar_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={urllib.parse.quote(title)}&dates={start_time}/{end_time}&details={urllib.parse.quote(details)}&sf=true&output=xml"
    
    contexto = {
        'turno': turno,
        'detalles': detalles,
        'url_gestion': url_gestion,
        'whatsapp_url': whatsapp_url,
        'google_calendar_url': google_calendar_url,
    }
    return render(request, 'gestion/confirmacion_publica.html', contexto)


def gestion_turno_publico(request, token):
    """Portal de autogestión pública para el cliente ver, reprogramar o cancelar sus turnos."""
    turno = get_object_or_404(Turno, token=token)
    detalles = turno.detalleturno_set.select_related('servicio', 'profesional').prefetch_related(
        'etapas_asignadas__estacion', 'etapas_asignadas__etapa_servicio'
    ).all()
    
    contexto = {
        'turno': turno,
        'detalles': detalles,
        'tiene_activos': turno.estado not in ['cancelado', 'completado'],
    }
    return render(request, 'gestion/gestion_publica.html', contexto)


def cancelar_turno_publico(request, token):
    """Permite al cliente cancelar su turno de forma segura con confirmación."""
    turno = get_object_or_404(Turno, token=token)
    
    if turno.estado in ['cancelado', 'completado']:
        messages.warning(request, "Este turno ya no está activo.")
        return redirect('gestion_turno_publico', token=token)
        
    if request.method == 'POST':
        with transaction.atomic():
            turno.estado = 'cancelado'
            old_obs = turno.observaciones or ''
            turno.observaciones = old_obs + f"\n[Cancelado por el cliente desde la web el {timezone.now().strftime('%d/%m %H:%M')}]"
            turno.save()
        messages.success(request, "Tu turno ha sido cancelado con éxito.")
        return redirect('gestion_turno_publico', token=token)
        
    contexto = {
        'turno': turno,
    }
    return render(request, 'gestion/cancelar_publica.html', contexto)
