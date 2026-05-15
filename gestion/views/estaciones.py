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
@user_passes_test(es_admin)
def lista_estaciones(request):
    estaciones = Estacion.objects.all()
    return render(request, 'gestion/estaciones.html', {'estaciones': estaciones})

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
    if request.method == 'POST':
        nombre = estacion.nombre
        estacion.delete()
        messages.success(request, f"Estación '{nombre}' eliminada.")
        return redirect('lista_estaciones')
    return render(request, 'gestion/estacion_confirm_delete.html', {'estacion': estacion})
