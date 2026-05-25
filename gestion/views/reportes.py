import json
from datetime import date, timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import TruncMonth, TruncDay

from ..models import Venta, Profesional, Turno, DetalleTurno, Servicio


def es_admin(user):
    return user.is_superuser


@user_passes_test(es_admin)
def facturacion(request):
    hoy = date.today()
    inicio = request.GET.get('desde', hoy.replace(day=1).isoformat())
    fin = request.GET.get('hasta', hoy.isoformat())
    profesional_id = request.GET.get('profesional', '')

    try:
        desde = date.fromisoformat(inicio)
        hasta = date.fromisoformat(fin)
    except ValueError:
        desde = hoy.replace(day=1)
        hasta = hoy

    # ─── Base: ventas en el período ───────────────────────────────
    ventas_qs = Venta.objects.filter(
        fecha_venta__date__gte=desde,
        fecha_venta__date__lte=hasta,
    )

    if profesional_id:
        ventas_qs = ventas_qs.filter(turno__profesional_id=profesional_id)

    ventas = list(ventas_qs.select_related('turno__profesional'))

    # ─── Totales globales ─────────────────────────────────────────
    total_facturado = sum(v.total for v in ventas)
    total_comisiones = sum(v.comision for v in ventas)
    cantidad_ventas = len(ventas)
    ticket_promedio = round(total_facturado / cantidad_ventas, 2) if cantidad_ventas else 0

    # ─── Por método de pago ────────────────────────────────────────
    metodos_agrupado = {}
    for v in ventas:
        metodo = v.get_metodo_pago_display()
        metodos_agrupado.setdefault(metodo, {'cantidad': 0, 'total': 0})
        metodos_agrupado[metodo]['cantidad'] += 1
        metodos_agrupado[metodo]['total'] += v.total

    metodos_pago = [
        {'metodo': m, 'cantidad': d['cantidad'], 'total': round(d['total'], 2)}
        for m, d in metodos_agrupado.items()
    ]

    # ─── Por profesional ──────────────────────────────────────────
    profesionales_data = []
    profesionales = Profesional.objects.filter(activo=True).order_by('apellido', 'nombre')

    for prof in profesionales:
        # Ventas de turnos de este profesional
        ventas_prof = [v for v in ventas if v.turno and v.turno.profesional_id == prof.id]
        if not ventas_prof:
            continue

        total_venta = sum(v.total for v in ventas_prof)
        total_comision = sum(v.comision for v in ventas_prof)
        turnos_count = len(ventas_prof)

        profesionales_data.append({
            'profesional': prof,
            'turnos': turnos_count,
            'total_venta': round(total_venta, 2),
            'comision': round(total_comision, 2),
            'porcentaje': round(total_venta / total_facturado * 100, 1) if total_facturado else 0,
        })

    profesionales_data.sort(key=lambda x: x['total_venta'], reverse=True)

    # ─── Servicios más vendidos ───────────────────────────────────
    servicios_qs = DetalleTurno.objects.filter(
        turno__fecha_hora__date__gte=desde,
        turno__fecha_hora__date__lte=hasta,
        turno__venta__isnull=False,
    ).values(
        'servicio__nombre'
    ).annotate(
        cantidad=Count('id'),
        total=Sum('precio_real'),
    ).order_by('-cantidad')[:15]

    servicios_top = [
        {
            'nombre': s['servicio__nombre'],
            'cantidad': s['cantidad'],
            'total': round(s['total'], 2),
        }
        for s in servicios_qs
    ]

    # ─── Evolución mensual ────────────────────────────────────────
    mensual = Venta.objects.filter(
        fecha_venta__date__gte=desde,
        fecha_venta__date__lte=hasta,
    ).annotate(
        mes=TruncMonth('fecha_venta'),
    ).values('mes').annotate(
        total=Sum('total'),
        cantidad=Count('id'),
    ).order_by('mes')

    evolucion = [
        {
            'mes': m['mes'].strftime('%b %Y') if m['mes'] else '',
            'total': round(m['total'], 2),
            'cantidad': m['cantidad'],
        }
        for m in mensual
    ]

    # ─── Detalle de ventas (para tabla de datos) ───────────────────
    detalle_ventas = Venta.objects.filter(
        fecha_venta__date__gte=desde,
        fecha_venta__date__lte=hasta,
    ).select_related(
        'turno__profesional',
        'turno__cliente',
        'cliente',
    ).prefetch_related(
        'detalles_productos__producto',
        'turno__detalleturno_set__servicio',
    ).order_by('-fecha_venta')

    if profesional_id:
        detalle_ventas = detalle_ventas.filter(turno__profesional_id=profesional_id)

    # ─── Datos para Chart.js (JSON) ───────────────────────────────
    def to_float(v):
        return float(v) if v is not None else 0

    chart_metodos_labels = json.dumps([m['metodo'] for m in metodos_pago])
    chart_metodos_data = json.dumps([to_float(m['total']) for m in metodos_pago])
    chart_metodos_colors = json.dumps([
        '#198754', '#0d6efd', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14'
    ][:len(metodos_pago)])

    chart_evolucion_labels = json.dumps([e['mes'] for e in evolucion])
    chart_evolucion_total = json.dumps([to_float(e['total']) for e in evolucion])
    chart_evolucion_cantidad = json.dumps([e['cantidad'] for e in evolucion])

    chart_prof_labels = json.dumps([p['profesional'].nombre for p in profesionales_data])
    chart_prof_total = json.dumps([to_float(p['total_venta']) for p in profesionales_data])
    chart_prof_comision = json.dumps([to_float(p['comision']) for p in profesionales_data])

    chart_servicios_labels = json.dumps([s['nombre'][:20] for s in servicios_top])
    chart_servicios_data = json.dumps([to_float(s['total']) for s in servicios_top])

    contexto = {
        'desde': desde.isoformat(),
        'hasta': hasta.isoformat(),
        'profesional_id': profesional_id,
        'total_facturado': round(total_facturado, 2),
        'total_comisiones': round(total_comisiones, 2),
        'cantidad_ventas': cantidad_ventas,
        'ticket_promedio': ticket_promedio,
        'metodos_pago': metodos_pago,
        'profesionales_data': profesionales_data,
        'servicios_top': servicios_top,
        'evolucion': evolucion,
        'profesionales': profesionales,
        # Chart.js data
        'chart_metodos_labels': chart_metodos_labels,
        'chart_metodos_data': chart_metodos_data,
        'chart_metodos_colors': chart_metodos_colors,
        'chart_evolucion_labels': chart_evolucion_labels,
        'chart_evolucion_total': chart_evolucion_total,
        'chart_evolucion_cantidad': chart_evolucion_cantidad,
        'chart_prof_labels': chart_prof_labels,
        'chart_prof_total': chart_prof_total,
        'chart_prof_comision': chart_prof_comision,
        'chart_servicios_labels': chart_servicios_labels,
        'chart_servicios_data': chart_servicios_data,
        'detalle_ventas': detalle_ventas,
    }
    return render(request, 'gestion/reportes/facturacion.html', contexto)
