import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from gestion.models import HorarioAtencion, Estacion, Profesional, Servicio, Turno
from django.utils import timezone
import datetime

print("DEBUGGING HORARIOS API")
print("======================")

fecha_str = str(datetime.date.today())
print(f"Fecha: {fecha_str}")

profesional = Profesional.objects.first()
servicio = Servicio.objects.first()

if not profesional or not servicio:
    print("Faltan profesionales o servicios")
    exit()

print(f"Profesional: {profesional.id}")
print(f"Servicio: {servicio.id}, duracion: {servicio.duracion_estimada}")

fecha = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()
duracion = servicio.duracion_estimada

dia_semana = fecha.weekday()
print(f"Dia semana: {dia_semana}")
horario = HorarioAtencion.objects.filter(dia_semana=dia_semana, abierto=True).first()
if not horario:
    print("NO HAY HORARIO PARA ESTE DIA")
    exit()

print(f"Horario: {horario.hora_apertura} - {horario.hora_cierre}")

inicio_comercial = datetime.datetime.combine(fecha, horario.hora_apertura)
fin_comercial = datetime.datetime.combine(fecha, horario.hora_cierre)

ahora_utc = timezone.now()
ahora_local = timezone.localtime(ahora_utc)
ahora = ahora_local.replace(tzinfo=None)

print(f"Ahora UTC: {ahora_utc}")
print(f"Ahora Local: {ahora_local}")
print(f"Ahora Naive: {ahora}")

actual = inicio_comercial
if fecha == ahora.date():
    if ahora > actual:
        minutos_faltantes = (5 - (ahora.minute % 5)) % 5
        actual = ahora + datetime.timedelta(minutes=minutos_faltantes)
        actual = actual.replace(second=0, microsecond=0)

print(f"Actual (start of search): {actual}")
print(f"Fin comercial: {fin_comercial}")
print(f"Condition actual + duracion <= fin_comercial: {actual + datetime.timedelta(minutes=duracion) <= fin_comercial}")

turnos_del_dia = list(Turno.objects.filter(
    fecha_hora__date=fecha
).exclude(estado__in=['cancelado', 'completado']).select_related('profesional', 'estacion'))
print(f"Turnos del dia: {len(turnos_del_dia)}")

estaciones_activas = list(Estacion.objects.filter(activa=True))
print(f"Estaciones activas: {len(estaciones_activas)}")

slots = []
while actual + datetime.timedelta(minutes=duracion) <= fin_comercial:
    slot_inicio_naive = actual
    slot_fin_naive = actual + datetime.timedelta(minutes=duracion)
    
    prof_libre = True
    for t in turnos_del_dia:
        if t.profesional_id == profesional.id:
            t_inicio = timezone.localtime(t.fecha_hora).replace(tzinfo=None)
            t_fin = timezone.localtime(t.hora_fin_estimada).replace(tzinfo=None)
            if slot_inicio_naive < t_fin and slot_fin_naive > t_inicio:
                prof_libre = False
                break
    
    if prof_libre:
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

    actual += datetime.timedelta(minutes=5)

print(f"Slots found: {len(slots)}")
if slots:
    print(slots)
