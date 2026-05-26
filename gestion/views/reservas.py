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
    Cliente, Turno, DetalleTurno, Estacion, Profesional,
    Servicio, HorarioAtencion, Reserva
)
from ..forms import ReservaAlPasoForm
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
            reserva = Reserva.objects.get(token=token_str)
            turno = Turno.objects.get(id=repro_id, reserva=reserva)
            if turno.estado in ['pendiente', 'por_reprogramar']:
                pre_load = {
                    'cliente_id': turno.cliente.id,
                    'nombre': turno.cliente.nombre,
                    'apellido': turno.cliente.apellido,
                    'telefono': turno.cliente.telefono,
                    'servicios_ids': list(turno.servicios.values_list('id', flat=True)),
                    'repro_id': turno.id,
                    'msg': f"Reprogramando tu Turno de {turno.cliente.nombre}"
                }
        except (Reserva.DoesNotExist, Turno.DoesNotExist, ValueError):
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
            telefono = data.get('telefono', '').strip()
            if not all([nombre, apellido, telefono]):
                return JsonResponse({'error': 'Datos del cliente incompletos.'}, status=400)
            cliente, _ = Cliente.objects.get_or_create(
                telefono=telefono,
                defaults={'nombre': nombre, 'apellido': apellido}
            )

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

        # Crear Reserva + Turnos dentro de una transacción atómica
        try:
            with transaction.atomic():
                # Bloqueamos el cliente para actualizaciones seguras de reservas
                cliente = Cliente.objects.select_for_update().get(id=cliente.id)

                # 1. Obtener y ordenar los IDs únicos de profesionales y estaciones para evitar interbloqueos (deadlocks)
                prof_ids = sorted(list(set(int(bloque['profesional_id']) for bloque in opcion['bloques'])))
                est_ids = sorted(list(set(int(bloque['estacion_id']) for bloque in opcion['bloques'])))

                # 2. Adquirir bloqueos pesimistas sobre los recursos en orden consistente de menor a mayor ID
                _ = list(Profesional.objects.select_for_update().filter(id__in=prof_ids).order_by('id'))
                _ = list(Estacion.objects.select_for_update().filter(id__in=est_ids).order_by('id'))

                # Si estamos reprogramando, cancelamos el turno viejo para liberar espacio
                repro_id = data.get('repro_id')
                if repro_id:
                    old_turno = Turno.objects.filter(id=repro_id).first()
                    if old_turno:
                        old_turno.estado = 'cancelado'
                        old_obs = old_turno.observaciones or ''
                        old_turno.observaciones = old_obs + f"\n[Cancelado por reprogramación el {timezone.now().strftime('%d/%m %H:%M')}]"
                        old_turno.save()

                reserva = Reserva.objects.create(cliente=cliente, observaciones=observaciones)

                turnos_creados = 0

                for idx, bloque in enumerate(opcion['bloques']):
                    servicio = Servicio.objects.get(id=bloque['servicio_id'])
                    profesional = Profesional.objects.get(id=bloque['profesional_id'])
                    estacion = Estacion.objects.get(id=bloque['estacion_id'])

                    hora_inicio = datetime.strptime(bloque['inicio'], '%H:%M').time()
                    hora_fin = datetime.strptime(bloque['fin'], '%H:%M').time()

                    fecha_hora = timezone.make_aware(datetime.combine(fecha, hora_inicio))
                    hora_fin_estimada = timezone.make_aware(datetime.combine(fecha, hora_fin))

                    nuevo_turno = Turno(
                        cliente=cliente,
                        profesional=profesional,
                        estacion=estacion,
                        fecha_hora=fecha_hora,
                        hora_fin_estimada=hora_fin_estimada,
                        reserva=reserva,
                        orden=idx,
                        observaciones=observaciones,
                    )
                    nuevo_turno.clean()
                    nuevo_turno.save()

                    DetalleTurno.objects.create(
                        turno=nuevo_turno,
                        servicio=servicio,
                        precio_real=servicio.precio_sugerido
                    )
                    turnos_creados += 1

            # Generar URL de WhatsApp para enviar el comprobante y token de autogestión al cliente
            import urllib.parse
            import re
            
            turnos_activos = reserva.turnos_reserva.exclude(estado='cancelado').order_by('orden')
            detalles_texto = ""
            for t in turnos_activos:
                servicios_nombres = ", ".join([s.nombre for s in t.servicios.all()])
                fecha_local = timezone.localtime(t.fecha_hora)
                detalles_texto += f"\n- {fecha_local.strftime('%d/%m a las %H:%M')}hs: {servicios_nombres} con {t.profesional.nombre}"
            
            url_gestion = request.build_absolute_uri(f'/reservas/publica/gestion/{reserva.token}/')
            mensaje_wa = f"¡Hola {cliente.nombre}! Registramos tu turno en Studio Salta:{detalles_texto}\n\nPodés gestionar, reprogramar o cancelar tu reserva desde acá: {url_gestion}"
            mensaje_wa_encoded = urllib.parse.quote(mensaje_wa)
            
            # Limpiar el número de teléfono del cliente para wa.me (solo dígitos, agregar 549 si tiene 10 dígitos)
            telefono_limpio = re.sub(r'\D', '', cliente.telefono)
            if not telefono_limpio.startswith('54') and len(telefono_limpio) == 10:
                telefono_limpio = '549' + telefono_limpio
            
            whatsapp_url = f"https://wa.me/{telefono_limpio}?text={mensaje_wa_encoded}"

            return JsonResponse({
                'success': True,
                'message': f'Se registraron {turnos_creados} turno(s) para {cliente}.',
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
    telefono = data.get('telefono', '').strip()

    if not fecha_str or not servicios_req:
        return JsonResponse({'error': 'Faltan fecha o servicios.'}, status=400)

    if not telefono:
        return JsonResponse({'error': 'Por favor, ingresá tu teléfono.'}, status=400)

    # Control de saturación preventivo (máximo 2 turnos a futuro)
    cliente = Cliente.objects.filter(telefono=telefono).first()
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
    telefono = data.get('telefono', '').strip()
    observaciones = data.get('observaciones', '').strip()

    if not all([nombre, apellido, telefono]):
        return JsonResponse({'error': 'Datos de contacto incompletos.'}, status=400)

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
            # 1. Buscar o crear el cliente por teléfono de manera segura
            cliente, creado = Cliente.objects.get_or_create(
                telefono=telefono,
                defaults={'nombre': nombre, 'apellido': apellido}
            )

            # 2. Bloqueamos el cliente para actualizaciones seguras de reservas
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

            # 4. Obtener y ordenar los IDs únicos de profesionales y estaciones para evitar interbloqueos
            prof_ids = sorted(list(set(int(bloque['profesional_id']) for bloque in opcion['bloques'])))
            est_ids = sorted(list(set(int(bloque['estacion_id']) for bloque in opcion['bloques'])))

            # 5. Adquirir bloqueos pesimistas sobre los recursos en orden consistente de menor a mayor ID
            _ = list(Profesional.objects.select_for_update().filter(id__in=prof_ids).order_by('id'))
            _ = list(Estacion.objects.select_for_update().filter(id__in=est_ids).order_by('id'))

            reserva = Reserva.objects.create(cliente=cliente, observaciones=observaciones)
            turnos_creados = 0

            for idx, bloque in enumerate(opcion['bloques']):
                servicio = Servicio.objects.get(id=bloque['servicio_id'])
                profesional = Profesional.objects.get(id=bloque['profesional_id'])
                estacion = Estacion.objects.get(id=bloque['estacion_id'])

                hora_inicio = datetime.strptime(bloque['inicio'], '%H:%M').time()
                hora_fin = datetime.strptime(bloque['fin'], '%H:%M').time()

                fecha_hora = timezone.make_aware(datetime.combine(fecha, hora_inicio))
                hora_fin_estimada = timezone.make_aware(datetime.combine(fecha, hora_fin))

                nuevo_turno = Turno(
                    cliente=cliente,
                    profesional=profesional,
                    estacion=estacion,
                    fecha_hora=fecha_hora,
                    hora_fin_estimada=hora_fin_estimada,
                    reserva=reserva,
                    orden=idx,
                    observaciones=observaciones,
                )
                nuevo_turno.clean()
                nuevo_turno.save()

                DetalleTurno.objects.create(
                    turno=nuevo_turno,
                    servicio=servicio,
                    precio_real=servicio.precio_sugerido
                )
                turnos_creados += 1

        return JsonResponse({
            'success': True,
            'message': f'¡Se reservaron con éxito tus {turnos_creados} servicio(s) en Studio Salta!',
            'redirect': f'/reservas/publica/confirmacion/{reserva.token}/'
        })

    except ValidationError as e:
        return JsonResponse({'error': '; '.join(e.messages)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def confirmacion_reserva_publica(request, token):
    """Muestra la pantalla de éxito con botones dinámicos para WhatsApp, calendario y copiado."""
    from django.conf import settings
    reserva = get_object_or_404(Reserva, token=token)
    turnos = reserva.turnos_reserva.exclude(estado='cancelado').order_by('orden')
    
    # Armar texto para WhatsApp
    detalles_texto = ""
    for t in turnos:
        servicios_nombres = ", ".join([s.nombre for s in t.servicios.all()])
        fecha_local = timezone.localtime(t.fecha_hora)
        detalles_texto += f"\n- {fecha_local.strftime('%d/%m a las %H:%M')}hs: {servicios_nombres} con {t.profesional.nombre}"
    
    # Enlace de autogestión
    url_gestion = request.build_absolute_uri(f'/reservas/publica/gestion/{token}/')
    
    mensaje_wa = f"¡Hola! Agendé mi turno en Studio Salta:{detalles_texto}\n\nLink para gestionar o reprogramar mi turno: {url_gestion}"
    import urllib.parse
    mensaje_wa_encoded = urllib.parse.quote(mensaje_wa)
    
    # Obtener el teléfono del salón configurado en settings
    salon_telefono = getattr(settings, 'SALON_WHATSAPP', '5493875551234')
    whatsapp_url = f"https://wa.me/{salon_telefono}?text={mensaje_wa_encoded}"
    
    # Google Calendar link para el primer turno
    google_calendar_url = None
    if turnos.exists():
        primer_turno = turnos.first()
        start_time = primer_turno.fecha_hora.strftime('%Y%m%dT%H%M%SZ')
        end_time = primer_turno.hora_fin_estimada.strftime('%Y%m%dT%H%M%SZ') if primer_turno.hora_fin_estimada else start_time
        title = "Turno en Studio Salta"
        details = f"Gestionar tu turno aquí: {url_gestion}"
        google_calendar_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={urllib.parse.quote(title)}&dates={start_time}/{end_time}&details={urllib.parse.quote(details)}&sf=true&output=xml"

    contexto = {
        'reserva': reserva,
        'turnos': turnos,
        'url_gestion': url_gestion,
        'whatsapp_url': whatsapp_url,
        'google_calendar_url': google_calendar_url,
    }
    return render(request, 'gestion/confirmacion_publica.html', contexto)


def gestion_reserva_publica(request, token):
    """Portal de autogestión pública para el cliente ver, reprogramar o cancelar sus turnos."""
    reserva = get_object_or_404(Reserva, token=token)
    turnos = reserva.turnos_reserva.order_by('orden')
    
    # Si todos están cancelados, se informa adecuadamente en la plantilla
    turnos_activos = turnos.exclude(estado='cancelado')
    
    contexto = {
        'reserva': reserva,
        'turnos': turnos,
        'tiene_activos': turnos_activos.exists(),
    }
    return render(request, 'gestion/gestion_publica.html', contexto)


def cancelar_reserva_publica(request, token):
    """Permite al cliente cancelar todos los turnos de su reserva de forma segura con confirmación."""
    reserva = get_object_or_404(Reserva, token=token)
    turnos_activos = reserva.turnos_reserva.exclude(estado__in=['cancelado', 'completado'])
    
    if not turnos_activos.exists():
        messages.warning(request, "No tenés turnos activos para cancelar en esta reserva.")
        return redirect('gestion_reserva_publica', token=token)
        
    if request.method == 'POST':
        with transaction.atomic():
            for t in turnos_activos:
                t.estado = 'cancelado'
                old_obs = t.observaciones or ''
                t.observaciones = old_obs + f"\n[Cancelado por el cliente desde la web el {timezone.now().strftime('%d/%m %H:%M')}]"
                t.save()
            messages.success(request, "Tus turnos han sido cancelados con éxito.")
        return redirect('gestion_reserva_publica', token=token)
        
    contexto = {
        'reserva': reserva,
        'turnos': turnos_activos,
    }
    return render(request, 'gestion/cancelar_publica.html', contexto)
