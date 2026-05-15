from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from ..models import FichaTecnica
from ..forms import FichaTecnicaForm


@login_required
def crear_ficha_desde_turno(request, turno_id):
    from ..models import Turno
    turno = get_object_or_404(Turno, id=turno_id)
    cliente = turno.cliente
    
    if request.method == 'POST':
        form = FichaTecnicaForm(request.POST)
        if form.is_valid():
            ficha = form.save(commit=False)
            ficha.cliente = cliente
            ficha.turno = turno
            ficha.save()
            messages.success(request, f"Ficha técnica creada para {cliente.nombre} {cliente.apellido}.")
            return redirect('dashboard')
    else:
        form = FichaTecnicaForm()
        
    contexto = {
        'form': form,
        'cliente': cliente,
        'turno': turno
    }
    return render(request, 'gestion/nueva_ficha.html', contexto)
