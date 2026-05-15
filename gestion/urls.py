from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_recepcion, name='dashboard'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/nuevo/', views.crear_cliente, name='crear_cliente'),
    path('clientes/<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:pk>/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),

    path('reservas/nueva/', views.reservar_turno_interno, name='reservar_interno'),
    path('reservas/reprogramar/<int:pk>/', views.reprogramar_turno, name='reprogramar_turno'),
    path('reservas/publica/', views.reservar_turno_publico, name='reservar_publico'),

    path('turno/<int:turno_id>/cancelar/', views.cancelar_turno, name='cancelar_turno'),
    path('turno/<int:turno_id>/iniciar/', views.iniciar_turno, name='iniciar_turno'),
    path('turno/<int:turno_id>/facturar/', views.facturar_turno, name='facturar_turno'),
    path('ventas/nueva/', views.venta_libre, name='venta_libre'),
    path('api/clientes/buscar/', views.api_buscar_clientes, name='api_buscar_clientes'),
    path('api/horarios/', views.api_horarios_disponibles, name='api_horarios'),
    path('api/disponibilidad-combinada/', views.api_disponibilidad_combinada, name='api_disponibilidad'),
    
    # --- Fichas Técnicas ---
    path('clientes/<int:cliente_id>/', views.perfil_cliente, name='perfil_cliente'),
    path('turno/<int:turno_id>/ficha/nueva/', views.crear_ficha_desde_turno, name='nueva_ficha_turno'),
    
    # --- ABM Profesionales (Admin) ---
    path('profesionales/', views.lista_profesionales, name='lista_profesionales'),
    path('profesionales/nuevo/', views.crear_profesional, name='crear_profesional'),
    path('profesionales/<int:prof_id>/editar/', views.editar_profesional, name='editar_profesional'),
    path('profesionales/<int:prof_id>/eliminar/', views.eliminar_profesional, name='eliminar_profesional'),

    # --- ABM Servicios (Admin) ---
    path('servicios/', views.lista_servicios, name='lista_servicios'),
    path('servicios/nuevo/', views.crear_servicio, name='crear_servicio'),
    path('servicios/<int:serv_id>/editar/', views.editar_servicio, name='editar_servicio'),
    path('servicios/<int:serv_id>/eliminar/', views.eliminar_servicio, name='eliminar_servicio'),
    path('servicios/reordenar/', views.reordenar_servicios, name='reordenar_servicios'),

    # --- Inventario y Productos (Admin) ---
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/nuevo/', views.crear_producto, name='crear_producto'),
    path('productos/<int:prod_id>/editar/', views.editar_producto, name='editar_producto'),
    path('productos/<int:prod_id>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/<int:prod_id>/stock/<str:accion>/', views.actualizar_stock_rapido, name='actualizar_stock_rapido'),
    path('productos/ajuste_masivo/', views.ajuste_masivo_precios, name='ajuste_masivo_precios'),

    # --- ABM Estaciones (Admin) ---
    path('estaciones/', views.lista_estaciones, name='lista_estaciones'),
    path('estaciones/nueva/', views.gestionar_estacion, name='crear_estacion'),
    path('estaciones/<int:pk>/editar/', views.gestionar_estacion, name='editar_estacion'),
    path('estaciones/<int:pk>/eliminar/', views.eliminar_estacion, name='eliminar_estacion'),

    # --- Configuración del Salón (Admin) ---
    path('configuracion/', views.panel_configuracion, name='panel_configuracion'),
    path('configuracion/horarios/nuevo/', views.gestionar_horario, name='crear_horario'),
    path('configuracion/horarios/<int:pk>/editar/', views.gestionar_horario, name='editar_horario'),
    path('configuracion/horarios/<int:pk>/eliminar/', views.eliminar_horario, name='eliminar_horario'),
    path('configuracion/cierres/nuevo/', views.gestionar_cierre, name='crear_cierre'),
    path('configuracion/cierres/<int:pk>/editar/', views.gestionar_cierre, name='editar_cierre'),
    path('configuracion/cierres/<int:pk>/eliminar/', views.eliminar_cierre, name='eliminar_cierre'),
]