from django.contrib import admin
from .models import (
    Cliente, Servicio, Estacion, Profesional, 
    HabilidadProfesional, Turno, DetalleTurno, DetalleEtapa,
    Venta, FichaTecnica, Producto, HorarioAtencion,
    EtapaServicio
)

@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(admin.ModelAdmin):
    list_display = ('get_dia_semana_display', 'hora_apertura', 'hora_cierre', 'abierto')
    list_editable = ('hora_apertura', 'hora_cierre', 'abierto')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('dni', 'apellido', 'nombre', 'telefono', 'email', 'activo')
    search_fields = ('dni', 'apellido', 'nombre', 'telefono', 'email')

class EtapaServicioInline(admin.TabularInline):
    model = EtapaServicio
    extra = 1
    fields = ('orden', 'nombre', 'duracion', 'tipo_estacion', 'requiere_profesional')
    verbose_name = "Etapa del Servicio"
    verbose_name_plural = "Etapas (El servicio se ejecutará en este orden)"

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_sugerido', 'get_duracion_total', 'cantidad_etapas')
    inlines = [EtapaServicioInline]
    
    def get_duracion_total(self, obj):
        return f"{obj.duracion_estimada} min"
    get_duracion_total.short_description = 'Duración Total'

    def cantidad_etapas(self, obj):
        return obj.etapas.count()
    cantidad_etapas.short_description = 'Pasos'

@admin.register(Estacion)
class EstacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'activa')

@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ('dni', 'apellido', 'nombre', 'porcentaje_comision', 'activo')
    search_fields = ('dni', 'apellido', 'nombre', 'telefono')

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'stock_actual', 'stock_minimo', 'precio', 'activo')
    list_editable = ('stock_actual', 'precio')

class DetalleEtapaInline(admin.TabularInline):
    model = DetalleEtapa
    extra = 0
    readonly_fields = ('detalle', 'etapa_servicio', 'estacion', 'hora_inicio', 'hora_fin')
    can_delete = False
    verbose_name = "Etapa asignada"
    verbose_name_plural = "Etapas asignadas (estación por etapa)"

    def has_add_permission(self, request, obj=None):
        return False


class DetalleTurnoAdmin(admin.ModelAdmin):
    inlines = [DetalleEtapaInline]


admin.site.register(Turno)
admin.site.register(DetalleTurno, DetalleTurnoAdmin)
admin.site.register(Venta)
admin.site.register(FichaTecnica)
admin.site.register(HabilidadProfesional)
