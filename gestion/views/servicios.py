import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST

from ..models import Servicio
from ..forms import ServicioForm


def es_admin(user):
    return user.is_superuser


@user_passes_test(es_admin)
def lista_servicios(request):
    servicios = Servicio.objects.filter(activo=True)
    return render(request, 'gestion/servicios.html', {'servicios': servicios})


@user_passes_test(es_admin)
@require_POST
def reordenar_servicios(request):
    """Recibe POST con pares id/orden y actualiza orden_sugerido en bulk."""
    try:
        data = json.loads(request.body)
        ordenes = data.get('ordenes', {})  # {str(id): int(orden)}
        if not ordenes:
            return JsonResponse({'error': 'No se recibieron datos.'}, status=400)

        servicios = Servicio.objects.filter(id__in=ordenes.keys())
        for servicio in servicios:
            nuevo_orden = ordenes.get(str(servicio.id))
            if nuevo_orden is not None:
                servicio.orden_sugerido = int(nuevo_orden)
        Servicio.objects.bulk_update(servicios, ['orden_sugerido'])
        return JsonResponse({'success': True, 'actualizados': len(servicios)})
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@user_passes_test(es_admin)
def crear_servicio(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio creado correctamente.')
            return redirect('lista_servicios')
    else:
        form = ServicioForm()
    return render(request, 'gestion/servicio_form.html', {'form': form, 'titulo': 'Nuevo Servicio'})


@user_passes_test(es_admin)
def editar_servicio(request, serv_id):
    servicio = get_object_or_404(Servicio, id=serv_id)
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio actualizado correctamente.')
            return redirect('lista_servicios')
    else:
        form = ServicioForm(instance=servicio)
    return render(request, 'gestion/servicio_form.html', {'form': form, 'titulo': 'Editar Servicio'})


@user_passes_test(es_admin)
def eliminar_servicio(request, serv_id):
    servicio = get_object_or_404(Servicio, id=serv_id)
    servicio.activo = False
    servicio.save()
    messages.success(request, f'Servicio {servicio.nombre} dado de baja.')
    return redirect('lista_servicios')
