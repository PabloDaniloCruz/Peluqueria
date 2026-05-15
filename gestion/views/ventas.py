from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from ..models import Cliente, Venta, Producto, DetalleVentaProducto
from ..forms import FacturacionForm


@login_required
def venta_libre(request):
    productos_venta = Producto.objects.filter(activo=True, es_para_venta=True)
    
    if request.method == 'POST':
        form = FacturacionForm(request.POST)
        if form.is_valid():
            total_real = form.cleaned_data['total']
            metodo_pago = form.cleaned_data['metodo_pago']
            cliente_id = request.POST.get('cliente_id')
            
            cliente = None
            if cliente_id:
                cliente = get_object_or_404(Cliente, id=cliente_id)

            # Crear la Venta (sin turno)
            venta = Venta.objects.create(
                cliente=cliente,
                total=total_real,
                metodo_pago=metodo_pago,
                comision=0 # Venta libre no suele llevar comisión de profesional
            )

            # Procesar Productos
            prod_ids = request.POST.getlist('productos_ids[]')
            prod_cants = request.POST.getlist('productos_cantidades[]')
            for pid, cant in zip(prod_ids, prod_cants):
                if pid and cant:
                    prod = Producto.objects.get(id=pid)
                    cantidad = int(cant)
                    DetalleVentaProducto.objects.create(
                        venta=venta,
                        producto=prod,
                        cantidad=cantidad,
                        precio_unitario=prod.precio
                    )
                    prod.stock_actual -= cantidad
                    prod.save()

            messages.success(request, f"Venta de mostrador registrada por ${total_real}.")
            return redirect('dashboard')
    else:
        form = FacturacionForm(initial={'total': 0})

    contexto = {
        'form': form,
        'productos_venta': productos_venta,
        'clientes': Cliente.objects.all().order_by('nombre')
    }
    return render(request, 'gestion/venta_libre.html', contexto)
