from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from ..models import Estacion
from django import forms

class EstacionForm(forms.ModelForm):
    class Meta:
        model = Estacion
        fields = ['nombre', 'tipo', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Estación 1'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

def es_admin(user):
    return user.is_superuser

@login_required
@login_required
@user_passes_test(es_admin)
def lista_estaciones(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', 'activos')
    
    estaciones = Estacion.objects.all().order_by('nombre')
    
    if estado == 'activos':
        estaciones = estaciones.filter(activa=True)
    elif estado == 'inactivos':
        estaciones = estaciones.filter(activa=False)
    
    if query:
        from django.db.models import Q
        estaciones = estaciones.filter(
            Q(nombre__icontains=query) |
            Q(tipo__icontains=query)
        )
        
    return render(request, 'gestion/estaciones.html', {
        'estaciones': estaciones,
        'query': query,
        'estado': estado,
    })


@login_required
@user_passes_test(es_admin)
def gestionar_estacion(request, pk=None):
    if pk:
        estacion = get_object_or_404(Estacion, pk=pk)
        titulo = "Editar Estación"
    else:
        estacion = None
        titulo = "Nueva Estación"

    if request.method == 'POST':
        form = EstacionForm(request.POST, instance=estacion)
        if form.is_valid():
            form.save()
            messages.success(request, f"Estación '{form.cleaned_data['nombre']}' guardada correctamente.")
            return redirect('lista_estaciones')
    else:
        form = EstacionForm(instance=estacion)

    return render(request, 'gestion/estacion_form.html', {
        'form': form,
        'titulo': titulo,
        'estacion': estacion
    })

@login_required
@user_passes_test(es_admin)
def eliminar_estacion(request, pk):
    estacion = get_object_or_404(Estacion, pk=pk)
    estacion.activa = False
    estacion.save()
    messages.success(request, f'Estación {estacion.nombre} dada de baja.')
    return redirect('lista_estaciones')


@login_required
@user_passes_test(es_admin)
def reactivar_estacion(request, pk):
    estacion = get_object_or_404(Estacion, pk=pk)
    estacion.activa = True
    estacion.save()
    messages.success(request, f'Estación {estacion.nombre} reactivada.')
    return redirect('lista_estaciones')
