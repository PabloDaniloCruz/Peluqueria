from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import F, Q
from django.contrib.auth.decorators import login_required
from datetime import date as date_type, timedelta as td

from ..models import Turno, Profesional, Servicio, Estacion, Producto


@login_required
def dashboard_recepcion(request):
    hoy = timezone.now().date()
    ahora = timezone.now()

    # --- Lógica de Auto-inicio ---
    turnos_atrasados = Turno.objects.filter(
        fecha_hora__date=hoy,
        fecha_hora__lt=ahora,
        estado='pendiente'
    )
    if turnos_atrasados.exists():
        count_atrasados = turnos_atrasados.count()
        turnos_atrasados.update(estado='en_curso')
        messages.info(request, f"Se han iniciado automáticamente {count_atrasados} turno(s) atrasado(s).")

    # --- Parámetros de fecha y vista ---
    fecha_str   = request.GET.get('fecha', hoy.isoformat())
    vista       = request.GET.get('vista', 'dia')   # 'dia' | 'semana'

    try:
        fecha_filtro = date_type.fromisoformat(fecha_str)
    except ValueError:
        fecha_filtro = hoy

    # Navegación día
    fecha_anterior = (fecha_filtro - td(days=1)).isoformat()
    fecha_siguiente = (fecha_filtro + td(days=1)).isoformat()

    # Semana (lunes→domingo de la semana de fecha_filtro)
    lunes = fecha_filtro - td(days=fecha_filtro.weekday())
    domingo = lunes + td(days=6)
    dias_semana = [lunes + td(days=i) for i in range(7)]
    semana_anterior = (lunes - td(weeks=1)).isoformat()
    semana_siguiente = (lunes + td(weeks=1)).isoformat()

    # --- Filtros ---
    estado_filtro      = request.GET.get('estado', '')
    profesional_filtro = request.GET.get('profesional', '')
    servicio_filtro    = request.GET.get('servicio', '')
    estacion_filtro    = request.GET.get('estacion', '')
    reserva_filtro     = request.GET.get('reserva', '')
    cliente_q          = request.GET.get('q', '').strip()
    sin_facturar       = request.GET.get('sin_facturar', '')

    def aplicar_filtros(qs):
        if estado_filtro:
            qs = qs.filter(estado=estado_filtro)
        if profesional_filtro:
            qs = qs.filter(profesional_id=profesional_filtro)
        if servicio_filtro:
            qs = qs.filter(servicios__id=servicio_filtro)
        if estacion_filtro:
            qs = qs.filter(estacion_id=estacion_filtro)
        if reserva_filtro:
            qs = qs.filter(reserva_id=reserva_filtro)
        if cliente_q:
            qs = qs.filter(
                Q(cliente__nombre__icontains=cliente_q) |
                Q(cliente__apellido__icontains=cliente_q) |
                Q(cliente__telefono__icontains=cliente_q)
            )
        if sin_facturar:
            qs = qs.filter(venta__isnull=True).exclude(estado__in=['completado', 'cancelado'])
        return qs

    # --- Queryset vista diaria ---
    base_dia = (
        Turno.objects
        .filter(fecha_hora__date=fecha_filtro)
        .select_related('cliente', 'profesional', 'estacion', 'reserva')
        .prefetch_related('servicios')
        .order_by('fecha_hora')
    )
    turnos = aplicar_filtros(base_dia)

    # --- Contadores del día (sin filtros de contenido) ---
    todos_del_dia = Turno.objects.filter(fecha_hora__date=fecha_filtro)
    contadores = {
        'total':      todos_del_dia.count(),
        'pendiente':  todos_del_dia.filter(estado='pendiente').count(),
        'en_curso':   todos_del_dia.filter(estado='en_curso').count(),
        'completado': todos_del_dia.filter(estado='completado').count(),
        'cancelado':  todos_del_dia.filter(estado='cancelado').count(),
    }

    # --- Datos para vista semanal ---
    turnos_semana_raw = (
        Turno.objects
        .filter(fecha_hora__date__gte=lunes, fecha_hora__date__lte=domingo)
        .select_related('cliente', 'profesional', 'estacion', 'reserva')
        .prefetch_related('servicios')
        .order_by('fecha_hora')
    )
    turnos_semana_raw = aplicar_filtros(turnos_semana_raw)

    # Agrupar por día para el template: {date: [turno, ...]}
    turnos_por_dia = {d: [] for d in dias_semana}
    for t in turnos_semana_raw:
        dia = timezone.localtime(t.fecha_hora).date()
        if dia in turnos_por_dia:
            turnos_por_dia[dia].append(t)

    # Convertir a lista ordenada [(fecha, [turnos]), ...]
    semana_data = [(d, turnos_por_dia[d]) for d in dias_semana]

    # --- Stock bajo ---
    base_bajo_stock = Producto.objects.filter(
        activo=True,
        stock_actual__lte=F('stock_minimo')
    )
    total_productos = Producto.objects.filter(activo=True).count()
    stock_critico = base_bajo_stock.filter(stock_actual__lte=0).count()
    stock_alerta = base_bajo_stock.filter(stock_actual__gt=0).count()
    stock_normal = total_productos - (stock_critico + stock_alerta)
    productos_bajo_stock = base_bajo_stock.order_by('stock_actual')[:10]

    contexto = {
        'turnos':              turnos,
        'hoy':                 hoy,
        'fecha_filtro':        fecha_filtro,
        'fecha_anterior':      fecha_anterior,
        'fecha_siguiente':     fecha_siguiente,
        'es_hoy':              fecha_filtro == hoy,
        # Vista
        'vista':               vista,
        # Semana
        'semana_data':         semana_data,
        'lunes':               lunes,
        'domingo':             domingo,
        'semana_anterior':     semana_anterior,
        'semana_siguiente':    semana_siguiente,
        # Filtros activos
        'estado_filtro':       estado_filtro,
        'profesional_filtro':  profesional_filtro,
        'servicio_filtro':     servicio_filtro,
        'estacion_filtro':     estacion_filtro,
        'reserva_filtro':      reserva_filtro,
        'cliente_q':           cliente_q,
        'sin_facturar':        sin_facturar,
        # Opciones dropdowns
        'profesionales':       Profesional.objects.filter(activo=True).order_by('nombre'),
        'servicios':           Servicio.objects.filter(activo=True).order_by('nombre'),
        'estaciones':          Estacion.objects.filter(activa=True).order_by('nombre'),
        'estados':             Turno.ESTADO_CHOICES,
        # Contadores
        'contadores':          contadores,
        # Stock bajo
        'productos_bajo_stock': productos_bajo_stock,
        'stock_critico':       stock_critico,
        'stock_alerta':        stock_alerta,
        'stock_normal':        stock_normal,
    }
    return render(request, 'gestion/dashboard.html', contexto)
