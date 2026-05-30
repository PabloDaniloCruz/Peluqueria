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
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', 'activos')
    
    clientes_bd = Cliente.objects.all().order_by('apellido', 'nombre')
    
    if estado == 'activos':
        clientes_bd = clientes_bd.filter(activo=True)
    elif estado == 'inactivos':
        clientes_bd = clientes_bd.filter(activo=False)
    
    if query:
        clientes_bd = clientes_bd.filter(
            Q(dni__icontains=query) |
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(telefono__icontains=query) |
            Q(email__icontains=query)
        )
    
    contexto = {
        'clientes': clientes_bd,
        'query': query,
        'estado': estado,
    }
    return render(request, 'gestion/clientes.html', contexto)


@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos del cliente actualizados.')
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'gestion/nuevo_cliente.html', {
        'form': form, 
        'editando': True, 
        'cliente': cliente
    })


@login_required
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    cliente.activo = False
    cliente.save()
    messages.success(request, f'Cliente {cliente.nombre} {cliente.apellido} dado de baja.')
    return redirect('lista_clientes')


@login_required
def reactivar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    cliente.activo = True
    cliente.save()
    messages.success(request, f'Cliente {cliente.nombre} {cliente.apellido} reactivado.')
    return redirect('lista_clientes')


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
        Q(dni__icontains=q) | 
        Q(nombre__icontains=q) | 
        Q(apellido__icontains=q) | 
        Q(telefono__icontains=q),
        activo=True
    )[:10]
    
    results = []
    for c in clientes:
        results.append({
            'id': c.id,
            'dni': c.dni,
            'nombre': c.nombre,
            'apellido': c.apellido,
            'telefono': c.telefono,
            'text': f"{c.nombre} {c.apellido}" + (f" — DNI: {c.dni}" if c.dni else f" ({c.telefono})")
        })
    
    return JsonResponse({'results': results})
