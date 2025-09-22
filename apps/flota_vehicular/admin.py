from django.contrib import admin
from .models import Vehiculo, AsignacionVehiculo, TransferenciaVehicular, RegistroUso


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ['placas', 'marca', 'modelo', 'año', 'tipo', 'estado', 'kilometraje_actual']
    list_filter = ['marca', 'tipo', 'estado', 'año']
    search_fields = ['placas', 'marca', 'modelo', 'numero_serie']
    readonly_fields = ['fecha_adquisicion']
    list_editable = ['estado']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('marca', 'modelo', 'año', 'color', 'tipo')
        }),
        ('Identificación', {
            'fields': ('placas', 'numero_serie')
        }),
        ('Estado y Kilometraje', {
            'fields': ('estado', 'kilometraje_actual', 'observaciones')
        }),
        ('Información Financiera', {
            'fields': ('fecha_adquisicion', 'costo')
        }),
        ('Documentación', {
            'fields': ('tarjeta_circulacion', 'tenencia', 'verificacion_vehicular', 'seguro'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(AsignacionVehiculo)
class AsignacionVehiculoAdmin(admin.ModelAdmin):
    list_display = ['vehiculo', 'empleado', 'fecha_asignacion', 'fecha_finalizacion', 'estado']
    list_filter = ['estado', 'fecha_asignacion']
    search_fields = ['vehiculo__placas', 'empleado__nombre', 'empleado__apellidos']
    date_hierarchy = 'fecha_asignacion'
    
    fieldsets = (
        (None, {
            'fields': ('vehiculo', 'empleado')
        }),
        ('Fechas', {
            'fields': ('fecha_asignacion', 'fecha_finalizacion', 'estado')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehiculo', 'empleado')


@admin.register(TransferenciaVehicular)
class TransferenciaVehicularAdmin(admin.ModelAdmin):
    list_display = ['vehiculo', 'empleado_origen', 'empleado_destino', 'fecha_solicitud', 'estado']
    list_filter = ['estado', 'fecha_solicitud']
    search_fields = ['vehiculo__placas', 'empleado_origen__nombre', 'empleado_destino__nombre']
    date_hierarchy = 'fecha_solicitud'
    readonly_fields = ['fecha_solicitud']
    
    fieldsets = (
        ('Información de la Transferencia', {
            'fields': ('vehiculo', 'empleado_origen', 'empleado_destino')
        }),
        ('Estado y Fechas', {
            'fields': ('estado', 'fecha_solicitud', 'fecha_transferencia', 'kilometraje_transferencia')
        }),
        ('Observaciones', {
            'fields': ('observaciones_solicitud', 'observaciones_inspeccion')
        }),
        ('Aprobación', {
            'fields': ('aprobado_por',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'vehiculo', 'empleado_origen', 'empleado_destino', 'aprobado_por'
        )
    
    actions = ['aprobar_transferencias', 'rechazar_transferencias']
    
    def aprobar_transferencias(self, request, queryset):
        updated = queryset.filter(estado='solicitada').update(estado='aprobada')
        self.message_user(request, f'{updated} transferencias aprobadas.')
    aprobar_transferencias.short_description = "Aprobar transferencias seleccionadas"
    
    def rechazar_transferencias(self, request, queryset):
        updated = queryset.filter(estado='solicitada').update(estado='rechazada')
        self.message_user(request, f'{updated} transferencias rechazadas.')
    rechazar_transferencias.short_description = "Rechazar transferencias seleccionadas"


@admin.register(RegistroUso)
class RegistroUsoAdmin(admin.ModelAdmin):
    list_display = ['vehiculo', 'empleado', 'fecha', 'destino', 'kilometraje_inicio', 'kilometraje_fin']
    list_filter = ['fecha', 'vehiculo__marca']
    search_fields = ['vehiculo__placas', 'empleado__nombre', 'destino', 'proposito']
    date_hierarchy = 'fecha'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('vehiculo', 'empleado', 'fecha')
        }),
        ('Viaje', {
            'fields': ('destino', 'proposito', 'kilometraje_inicio', 'kilometraje_fin')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehiculo', 'empleado')