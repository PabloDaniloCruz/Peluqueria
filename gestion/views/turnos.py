from decimal import Decimal

from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from ..models import Turno, Venta, Producto, DetalleVentaProducto, ConsumoInsumo
from ..forms import FacturacionForm


@login_required
def cancelar_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id)
    if turno.estado == 'completado':
        messages.error(request, "No se puede cancelar un turno ya completado.")
    else:
        turno.estado = 'cancelado'
        turno.save()
        messages.success(request, f"Turno #{turno.id} cancelado correctamente.")
    return redirect('dashboard')


@login_required
def iniciar_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id)
    if turno.estado == 'pendiente':
        turno.estado = 'en_curso'
        turno.save()
        messages.success(request, f"Turno #{turno.id} iniciado manualmente.")
    return redirect('dashboard')


@login_required
def facturar_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id)
    
    if turno.estado == 'completado':
        messages.warning(request, "Este turno ya fue facturado.")
        return redirect('dashboard')

    total_sugerido = turno.total_servicios

    if request.method == 'POST':
        form = FacturacionForm(request.POST)
        if form.is_valid():
            total_real = form.cleaned_data['total']
            metodo_pago = form.cleaned_data['metodo_pago']
            
            # Calcular comisión basada en el porcentaje del profesional
            porcentaje = turno.profesional.porcentaje_comision
            comision_calculada = (total_real * porcentaje) / 100

            # Crear la Venta
            venta = Venta.objects.create(
                turno=turno,
                total=total_real,
                metodo_pago=metodo_pago,
                comision=comision_calculada
            )

            # Procesar Productos Vendidos
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
                    # Descontar stock
                    prod.stock_actual -= cantidad
                    prod.save()

            # Procesar Insumos Consumidos
            insumo_ids = request.POST.getlist('insumos_ids[]')
            insumo_cants = request.POST.getlist('insumos_cantidades[]')
            for iid, cant in zip(insumo_ids, insumo_cants):
                if iid and cant:
                    prod = Producto.objects.get(id=iid)
                    cantidad = Decimal(cant)
                    ConsumoInsumo.objects.create(
                        turno=turno,
                        producto=prod,
                        cantidad_usada=cantidad
                    )
                    # Descontar stock (Decimal - Decimal funciona correctamente)
                    prod.stock_actual -= cantidad
                    prod.save()

            # Completar el turno
            turno.estado = 'completado'
            turno.save()

            messages.success(request, f"Venta registrada por ${total_real}. Se actualizó el inventario.")
            return redirect('dashboard')
    else:
        # Pre-cargar el formulario con el total sugerido
        form = FacturacionForm(initial={'total': total_sugerido})

    contexto = {
        'turno': turno,
        'form': form,
        'total_sugerido': total_sugerido,
        'productos_venta': Producto.objects.filter(activo=True, es_para_venta=True),
        'productos_insumo': Producto.objects.filter(activo=True, es_insumo=True),
    }
    return render(request, 'gestion/facturar.html', contexto)
