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
    servicios = list(Servicio.objects.filter(activo=True).values(
        'id', 'nombre', 'descripcion', 'precio_sugerido',
        'duracion_estimada', 'orden_sugerido'
    ))
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
    return render(request, 'gestion/reserva_publica_wizard.html', contexto)


@login_required
def reservar_turno_interno(request):
    """Vista wizard para reserva interna multi-servicio con agenda continua."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos inválidos.'}, status=400)

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
                        old_turno.observaciones += f"\n[Cancelado por reprogramación el {timezone.now().strftime('%d/%m %H:%M')}]"
                        old_turno.save()

                reserva = Reserva.objects.create(cliente=cliente)

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
                'message': f'Se registraron {turnos_creados} turno(s) para {cliente}.',
                'redirect': '/'
            })

        except ValidationError as e:
            return JsonResponse({'error': '; '.join(e.messages)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # GET — Renderizar wizard
    servicios = list(Servicio.objects.filter(activo=True).values(
        'id', 'nombre', 'descripcion', 'precio_sugerido',
        'duracion_estimada', 'orden_sugerido'
    ))
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
        'msg': f"Reprogramando Turno #{turno.id} de {turno.cliente}"
    }

    # Reutilizamos la lógica de cargar servicios y profesionales
    servicios = list(Servicio.objects.filter(activo=True).values(
        'id', 'nombre', 'descripcion', 'precio_sugerido',
        'duracion_estimada', 'orden_sugerido'
    ))
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

            reserva = Reserva.objects.create(cliente=cliente)
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
            'redirect': '/reservas/publica/'
        })

    except ValidationError as e:
        return JsonResponse({'error': '; '.join(e.messages)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
