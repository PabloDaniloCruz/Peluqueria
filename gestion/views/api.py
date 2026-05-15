from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta

from ..models import Profesional, Servicio, Turno, Estacion, HorarioAtencion


def api_horarios_disponibles(request):
    fecha_str = request.GET.get('fecha')
    profesional_id = request.GET.get('profesional')
    servicio_id = request.GET.get('servicio')
    cliente_id = request.GET.get('cliente')

    if not all([fecha_str, profesional_id, servicio_id]):
        return JsonResponse({'horarios': []})

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        profesional = get_object_or_404(Profesional, id=profesional_id)
        servicio = get_object_or_404(Servicio, id=servicio_id)
        duracion = servicio.duracion_estimada
    except (ValueError, Exception):
        return JsonResponse({'horarios': []})

    if not profesional.habilidades.filter(id=servicio.id).exists():
        return JsonResponse({'horarios': [], 'error': f'{profesional.nombre} no realiza este servicio.'})

    dia_semana = fecha.weekday()
    horario = HorarioAtencion.objects.filter(dia_semana=dia_semana, abierto=True).first()
    if not horario:
        return JsonResponse({'horarios': [], 'error': 'El local está cerrado o no tiene horario configurado para este día.'})

    slots = []
    inicio_comercial = datetime.combine(fecha, horario.hora_apertura)
    fin_comercial = datetime.combine(fecha, horario.hora_cierre)
    
    ahora = timezone.localtime(timezone.now()).replace(tzinfo=None)
    actual = inicio_comercial
    if fecha == ahora.date():
        if ahora > actual:
            minutos_faltantes = (5 - (ahora.minute % 5)) % 5
            actual = ahora + timedelta(minutes=minutos_faltantes)
            actual = actual.replace(second=0, microsecond=0)

    turnos_del_dia = list(Turno.objects.filter(
        fecha_hora__date=fecha
    ).exclude(estado__in=['cancelado', 'completado']).select_related('profesional', 'estacion'))
    
    estaciones_activas = list(Estacion.objects.filter(activa=True))

    while actual + timedelta(minutes=duracion) <= fin_comercial:
        slot_inicio_naive = actual
        slot_fin_naive = actual + timedelta(minutes=duracion)
        
        prof_libre = True
        for t in turnos_del_dia:
            if t.profesional_id == profesional.id:
                t_inicio = timezone.localtime(t.fecha_hora).replace(tzinfo=None)
                t_fin = timezone.localtime(t.hora_fin_estimada).replace(tzinfo=None)
                if slot_inicio_naive < t_fin and slot_fin_naive > t_inicio:
                    prof_libre = False
                    break
        
        cliente_libre = True
        if cliente_id:
            for t in turnos_del_dia:
                if t.cliente_id == int(cliente_id):
                    t_inicio = timezone.localtime(t.fecha_hora).replace(tzinfo=None)
                    t_fin = timezone.localtime(t.hora_fin_estimada).replace(tzinfo=None)
                    if slot_inicio_naive < t_fin and slot_fin_naive > t_inicio:
                        cliente_libre = False
                        break

        if prof_libre and cliente_libre:
            hay_estacion = False
            for est in estaciones_activas:
                est_ocupada = False
                for t in turnos_del_dia:
                    if t.estacion_id == est.id:
                        t_inicio = timezone.localtime(t.fecha_hora).replace(tzinfo=None)
                        t_fin = timezone.localtime(t.hora_fin_estimada).replace(tzinfo=None)
                        if slot_inicio_naive < t_fin and slot_fin_naive > t_inicio:
                            est_ocupada = True
                            break
                if not est_ocupada:
                    hay_estacion = True
                    break
            
            if hay_estacion:
                slots.append(actual.strftime('%H:%M'))

        actual += timedelta(minutes=5)

    return JsonResponse({'horarios': slots})
