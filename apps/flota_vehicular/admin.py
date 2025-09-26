from django.contrib import admin
from .models import (
    Vehiculo, AsignacionVehiculo, TransferenciaVehicular, 
    RegistroUso, TenenciaVehicular, VerificacionVehicular
)


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ['placas', 'marca', 'modelo', 'año', 'tipo', 'estado', 'kilometraje_actual']
    list_filter = ['marca', 'tipo', 'estado', 'año']
    search_fields = ['placas', 'marca', 'modelo', 'numero_serie']
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
        ('Seguro', {
            'fields': ('aseguradora', 'contacto_aseguradora', 'numero_seguro')
        }),
        ('Documentación', {
            'fields': ('tarjeta_circulacion',),
            'classes': ('collapse',)
        }),
    )


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


@admin.register(TenenciaVehicular)
class TenenciaVehicularAdmin(admin.ModelAdmin):
    list_display = ['vehiculo', 'año_fiscal', 'fecha_vencimiento', 'estado', 'monto', 'fecha_pago']
    list_filter = ['estado', 'año_fiscal', 'fecha_vencimiento']
    search_fields = ['vehiculo__placas', 'vehiculo__marca', 'folio']
    date_hierarchy = 'fecha_vencimiento'
    list_editable = ['estado']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('vehiculo', 'año_fiscal', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_vencimiento', 'fecha_pago')
        }),
        ('Información Financiera', {
            'fields': ('monto', 'folio')
        }),
        ('Documentación', {
            'fields': ('comprobante_pago', 'observaciones'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['marcar_como_pagada', 'marcar_como_vencida']
    
    def marcar_como_pagada(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(estado='pendiente').update(
            estado='vigente',
            fecha_pago=timezone.now().date()
        )
        self.message_user(request, f'{updated} tenencias marcadas como pagadas.')
    marcar_como_pagada.short_description = "Marcar como pagadas"
    
    def marcar_como_vencida(self, request, queryset):
        updated = queryset.exclude(estado='vigente').update(estado='vencida')
        self.message_user(request, f'{updated} tenencias marcadas como vencidas.')
    marcar_como_vencida.short_description = "Marcar como vencidas"


@admin.register(VerificacionVehicular)
class VerificacionVehicularAdmin(admin.ModelAdmin):
    list_display = ['vehiculo', 'tipo_verificacion', 'fecha_verificacion', 'fecha_vencimiento', 'estado', 'centro_verificacion']
    list_filter = ['tipo_verificacion', 'estado', 'fecha_verificacion', 'centro_verificacion']
    search_fields = ['vehiculo__placas', 'vehiculo__marca', 'numero_certificado', 'centro_verificacion']
    date_hierarchy = 'fecha_verificacion'
    list_editable = ['estado']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('vehiculo', 'tipo_verificacion', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_verificacion', 'fecha_vencimiento')
        }),
        ('Detalles de Verificación', {
            'fields': ('numero_certificado', 'centro_verificacion', 'costo')
        }),
        ('Documentación', {
            'fields': ('certificado', 'observaciones'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['marcar_como_aprobada', 'marcar_como_vencida']
    
    def marcar_como_aprobada(self, request, queryset):
        updated = queryset.filter(estado='pendiente').update(estado='aprobada')
        self.message_user(request, f'{updated} verificaciones marcadas como aprobadas.')
    marcar_como_aprobada.short_description = "Marcar como aprobadas"
    
    def marcar_como_vencida(self, request, queryset):
        updated = queryset.exclude(estado='aprobada').update(estado='vencida')
        self.message_user(request, f'{updated} verificaciones marcadas como vencidas.')
    marcar_como_vencida.short_description = "Marcar como vencidas"