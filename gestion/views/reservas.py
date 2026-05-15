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
    if request.method == 'POST':
        form = ReservaAlPasoForm(request.POST)
        if form.is_valid():
            telefono_ingresado = form.cleaned_data['telefono']
            
            # 1. Buscar si el cliente ya existe por su teléfono, o crearlo si es nuevo
            cliente, creado = Cliente.objects.get_or_create(
                telefono=telefono_ingresado,
                defaults={
                    'nombre': form.cleaned_data['nombre'],
                    'apellido': form.cleaned_data['apellido']
                }
            )

            # 2. CONTROL DE SATURACIÓN: Contar cuántos turnos futuros tiene este cliente
            turnos_pendientes = Turno.objects.filter(
                cliente=cliente, 
                fecha_hora__gte=timezone.now() # Busca turnos de hoy en adelante
            ).count()
            
            if turnos_pendientes >= 2: # Límite de 2 turnos
                messages.error(request, "Ya tenés 2 turnos reservados. Por favor, asistí o cancelá uno antes de sacar otro.")
                return redirect('reservar_publico')

            # 3. Asignación automática de Estación y cálculo de fin
            servicio_elegido = form.cleaned_data['servicio']
            profesional_elegido = form.cleaned_data['profesional']
            
            # Validación de habilidad del profesional
            if not profesional_elegido.habilidades.filter(id=servicio_elegido.id).exists():
                messages.error(request, f"{profesional_elegido.nombre} no realiza el servicio seleccionado.")
                return redirect('reservar_publico')

            fecha_hora = form.cleaned_data['fecha_hora']
            hora_fin_estimada = fecha_hora + timedelta(minutes=servicio_elegido.duracion_estimada)
            
            estaciones_activas = Estacion.objects.filter(activa=True)
            estacion_disponible = None
            for est in estaciones_activas:
                superposicion = Turno.objects.filter(
                    estacion=est,
                    fecha_hora__lt=hora_fin_estimada,
                    hora_fin_estimada__gt=fecha_hora
                ).exclude(estado__in=["cancelado", "completado"]).exists()
                
                if not superposicion:
                    estacion_disponible = est
                    break
                    
            if not estacion_disponible:
                messages.error(request, "Lo sentimos, no hay estaciones de trabajo disponibles en ese horario.")
                return redirect('reservar_publico')

            # 4. Crear el Turno principal y Validar
            nuevo_turno = Turno(
                cliente=cliente,
                profesional=form.cleaned_data['profesional'],
                estacion=estacion_disponible,
                fecha_hora=fecha_hora,
                hora_fin_estimada=hora_fin_estimada
            )
            
            try:
                nuevo_turno.clean() # Ejecuta nuestras validaciones de negocio
                nuevo_turno.save()
            except ValidationError as e:
                for err in e.messages:
                    messages.error(request, err)
                return redirect('reservar_publico')

            # 5. Crear el DetalleTurno
            DetalleTurno.objects.create(
                turno=nuevo_turno,
                servicio=servicio_elegido,
                precio_real=servicio_elegido.precio_sugerido
            )
            
            messages.success(request, f"¡Reserva confirmada para el {form.cleaned_data['fecha_hora'].strftime('%d/%m/%Y %H:%M')}!")
            return redirect('reservar_publico')
            
    else:
        form = ReservaAlPasoForm()

    return render(request, 'gestion/reserva_publica.html', {'form': form})


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
