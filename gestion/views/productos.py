from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from ..models import Producto
from ..forms import ProductoForm


def es_admin(user):
    return user.is_superuser


@user_passes_test(es_admin)
def lista_productos(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', 'activos')
    
    productos = Producto.objects.all().order_by('nombre')
    
    if estado == 'activos':
        productos = productos.filter(activo=True)
    elif estado == 'inactivos':
        productos = productos.filter(activo=False)
    
    if query:
        from django.db.models import Q
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(marca__icontains=query)
        )
        
    return render(request, 'gestion/productos.html', {
        'productos': productos,
        'query': query,
        'estado': estado,
    })



@user_passes_test(es_admin)
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto creado correctamente.')
            return redirect('lista_productos')
    else:
        form = ProductoForm()
    return render(request, 'gestion/producto_form.html', {'form': form, 'titulo': 'Nuevo Producto'})


@user_passes_test(es_admin)
def editar_producto(request, prod_id):
    producto = get_object_or_404(Producto, id=prod_id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado correctamente.')
            return redirect('lista_productos')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'gestion/producto_form.html', {'form': form, 'titulo': 'Editar Producto'})


@user_passes_test(es_admin)
def eliminar_producto(request, prod_id):
    producto = get_object_or_404(Producto, id=prod_id)
    producto.activo = False
    producto.save()
    messages.success(request, f'Producto {producto.nombre} dado de baja.')
    return redirect('lista_productos')


@user_passes_test(es_admin)
def reactivar_producto(request, prod_id):
    producto = get_object_or_404(Producto, id=prod_id)
    producto.activo = True
    producto.save()
    messages.success(request, f'Producto {producto.nombre} reactivado.')
    return redirect('lista_productos')


@user_passes_test(es_admin)
def actualizar_stock_rapido(request, prod_id, accion):
    producto = get_object_or_404(Producto, id=prod_id)
    if accion == 'sumar':
        producto.stock_actual += 1
        messages.success(request, f'Se sumó 1 a {producto.nombre}.')
    elif accion == 'restar' and producto.stock_actual > 0:
        producto.stock_actual -= 1
        messages.success(request, f'Se restó 1 a {producto.nombre}.')
    elif accion == 'restar' and producto.stock_actual <= 0:
        messages.error(request, 'El stock ya está en 0.')
    producto.save()
    return redirect('lista_productos')


@user_passes_test(es_admin)
def ajuste_masivo_precios(request):
    if request.method == 'POST':
        porcentaje_str = request.POST.get('porcentaje', '0')
        try:
            porcentaje = float(porcentaje_str)
            if porcentaje == 0:
                messages.warning(request, 'El porcentaje no puede ser 0.')
                return redirect('lista_productos')
            
            productos_venta = Producto.objects.filter(activo=True, es_para_venta=True)
            contador = 0
            for prod in productos_venta:
                if prod.precio:
                    incremento = prod.precio * (porcentaje / 100)
                    prod.precio += incremento
                    prod.save()
                    contador += 1
            
            messages.success(request, f'Se ajustaron los precios de {contador} productos en un {porcentaje}%.')
        except ValueError:
            messages.error(request, 'Porcentaje inválido.')
    
    return redirect('lista_productos')
