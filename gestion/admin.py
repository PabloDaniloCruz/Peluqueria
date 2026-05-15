from django.contrib import admin
from .models import (
    Cliente, Servicio, Estacion, Profesional, 
    HabilidadProfesional, Turno, DetalleTurno, 
    Venta, FichaTecnica, Producto, HorarioAtencion
)

@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(admin.ModelAdmin):
    list_display = ('get_dia_semana_display', 'hora_apertura', 'hora_cierre', 'abierto')
    list_editable = ('hora_apertura', 'hora_cierre', 'abierto')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('apellido', 'nombre', 'telefono', 'email', 'activo')
    search_fields = ('apellido', 'nombre', 'email')

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_sugerido', 'duracion_estimada')

@admin.register(Estacion)
class EstacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'activa')

@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ('apellido', 'nombre', 'porcentaje_comision', 'activo')

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'stock_actual', 'stock_minimo', 'precio', 'activo')
    list_editable = ('stock_actual', 'precio')

admin.site.register(Turno)
admin.site.register(DetalleTurno)
admin.site.register(Venta)
admin.site.register(FichaTecnica)
admin.site.register(HabilidadProfesional)
