from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from ..models import Cliente, Turno, FichaTecnica
from ..forms import ClienteForm


@login_required
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente registrado correctamente.')
            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    
    return render(request, 'gestion/nuevo_cliente.html', {'form': form})


@login_required
def lista_clientes(request):
    clientes_bd = Cliente.objects.all()
    contexto = {
        'clientes': clientes_bd
    }
    return render(request, 'gestion/clientes.html', contexto)


@login_required
def perfil_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    turnos = Turno.objects.filter(cliente=cliente).order_by('-fecha_hora')
    fichas = FichaTecnica.objects.filter(cliente=cliente).order_by('-fecha_creacion')
    
    contexto = {
        'cliente': cliente,
        'turnos': turnos,
        'fichas': fichas
    }
    return render(request, 'gestion/perfil_cliente.html', contexto)


@login_required
def api_buscar_clientes(request):
    q = request.GET.get('q', '')
    if len(q) < 2:
        return JsonResponse({'results': []})
    
    clientes = Cliente.objects.filter(
        Q(nombre__icontains=q) | 
        Q(apellido__icontains=q) | 
        Q(telefono__icontains=q)
    )[:10]
    
    results = []
    for c in clientes:
        results.append({
            'id': c.id,
            'nombre': c.nombre,
            'apellido': c.apellido,
            'telefono': c.telefono,
            'text': f"{c.nombre} {c.apellido} ({c.telefono})"
        })
    
    return JsonResponse({'results': results})
