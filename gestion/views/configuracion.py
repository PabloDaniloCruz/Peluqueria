from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from ..models import HorarioAtencion, CierreExcepcional
from ..forms import HorarioAtencionForm, CierreExcepcionalForm

def es_admin(user):
    return user.is_superuser

@user_passes_test(es_admin)
def panel_configuracion(request):
    horarios = HorarioAtencion.objects.all().order_by('dia_semana', 'hora_apertura')
    cierres = CierreExcepcional.objects.all().order_by('-fecha')
    
    # Agrupar horarios por día para facilitar la visualización
    dias_semana = {i: nombre for i, nombre in HorarioAtencion.DIA_CHOICES}
    horarios_agrupados = {i: [] for i in range(7)}
    for h in horarios:
        horarios_agrupados[h.dia_semana].append(h)
    
    context = {
        'horarios_agrupados': horarios_agrupados,
        'dias_semana': dias_semana,
        'cierres': cierres,
    }
    return render(request, 'gestion/configuracion/panel.html', context)

@user_passes_test(es_admin)
def gestionar_horario(request, pk=None):
    if pk:
        horario = get_object_or_404(HorarioAtencion, pk=pk)
        titulo = "Editar Horario"
    else:
        horario = None
        titulo = "Nuevo Horario"

    if request.method == 'POST':
        form = HorarioAtencionForm(request.POST, instance=horario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Horario guardado correctamente.')
            return redirect('panel_configuracion')
    else:
        form = HorarioAtencionForm(instance=horario)
    
    return render(request, 'gestion/configuracion/horario_form.html', {'form': form, 'titulo': titulo})

@user_passes_test(es_admin)
def eliminar_horario(request, pk):
    horario = get_object_or_404(HorarioAtencion, pk=pk)
    horario.delete()
    messages.success(request, 'Horario eliminado.')
    return redirect('panel_configuracion')

from django.apps import apps
from urllib.parse import quote
import datetime

@user_passes_test(es_admin)
def gestionar_cierre(request, pk=None):
    if pk:
        cierre = get_object_or_404(CierreExcepcional, pk=pk)
        titulo = "Editar Cierre"
    else:
        cierre = None
        titulo = "Nuevo Cierre"

    form = CierreExcepcionalForm(request.POST or None, instance=cierre)
    afectados = []
    conflictos_detectados = False

    if request.method == 'POST':
        # Primero validamos el form. Si falla por el clean() de conflictos, 
        # capturamos esos turnos para mostrarlos.
        if form.is_valid():
            form.save()
            messages.success(request, 'Cierre guardado correctamente.')
            return redirect('panel_configuracion')
        else:
            # Si el error es por el conflicto de turnos, buscamos quiénes son
            # Nota: Esto es manual porque queremos mostrarlos en el template.
            fecha = form.data.get('fecha')
            if fecha:
                fecha_dt = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
                es_completo = form.data.get('es_dia_completo') == 'on'
                
                Turno = apps.get_model('gestion', 'Turno')
                qs = Turno.objects.filter(fecha_hora__date=fecha_dt, estado='pendiente')
                
                if not es_completo:
                    h_ini = form.data.get('hora_inicio')
                    h_fin = form.data.get('hora_fin')
                    if h_ini and h_fin:
                        t_ini = datetime.time.fromisoformat(h_ini)
                        t_fin = datetime.time.fromisoformat(h_fin)
                        dt_ini = datetime.datetime.combine(fecha_dt, t_ini)
                        dt_fin = datetime.datetime.combine(fecha_dt, t_fin)
                        qs = qs.filter(fecha_hora__lt=dt_fin, hora_fin_estimada__gt=dt_ini)
                
                afectados = qs.select_related('cliente')
                if afectados.exists():
                    conflictos_detectados = True
                    
                    # Si el usuario mandó "forzar", procedemos
                    if request.POST.get('confirmar_forzado') == 'true':
                        # Usamos la instancia del form directamente. 
                        # Al llamar a instancia.save() salteamos la validación del ModelForm
                        # que es la que dispara el clean() y bloquea el guardado.
                        instancia = form.instance
                        instancia.save()
                        
                        # Actualizamos turnos masivamente
                        afectados.update(estado='por_reprogramar')

                        
                        messages.warning(request, f'Cierre forzado. {afectados.count()} turnos pasaron a "Por Reprogramar".')
                        return redirect('panel_configuracion')

    # Preparar links de WhatsApp para los afectados
    turnos_repro = []
    for t in afectados:
        msg = (
            f"Hola {t.cliente.nombre}, te contactamos de Studio Salta para avisarte que por "
            f"{request.POST.get('descripcion') or 'motivos de fuerza mayor'}, el salón estará cerrado "
            f"el {t.fecha_hora.strftime('%d/%m')}. Tu turno de las {t.fecha_hora.strftime('%H:%M')} "
            f"debe ser reprogramado. ¿Qué otro horario te queda cómodo?"
        )
        t.wa_link = f"https://wa.me/{t.cliente.telefono}?text={quote(msg)}"
        turnos_repro.append(t)

    return render(request, 'gestion/configuracion/cierre_form.html', {
        'form': form, 
        'titulo': titulo,
        'afectados': turnos_repro,
        'conflictos_detectados': conflictos_detectados
    })


@user_passes_test(es_admin)
def eliminar_cierre(request, pk):
    cierre = get_object_or_404(CierreExcepcional, pk=pk)
    cierre.delete()
    messages.success(request, 'Cierre eliminado.')
    return redirect('panel_configuracion')
