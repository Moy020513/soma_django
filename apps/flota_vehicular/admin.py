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
    # list_editable removed: do not allow inline edits from changelist
    
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
    search_fields = ['vehiculo__placas', 'empleado__usuario__username', 'empleado__usuario__first_name', 'empleado__usuario__last_name']
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
    
    def get_empleado_info(self, obj):
        """Muestra información más completa del empleado"""
        if obj.empleado:
            return f"{obj.empleado.numero_empleado} - {obj.empleado.usuario.get_full_name()}"
        return "Sin empleado"
    get_empleado_info.short_description = "Empleado"
    
    def save_model(self, request, obj, form, change):
        """
        Actualiza automáticamente el estado del vehículo cuando se asigna o finaliza la asignación
        """
        super().save_model(request, obj, form, change)
        
        # Si la asignación está activa, marcar el vehículo como asignado
        if obj.estado == 'activa':
            obj.vehiculo.estado = 'asignado'
            obj.vehiculo.save()
        
        # Si la asignación se finaliza, marcar el vehículo como disponible
        elif obj.estado == 'finalizada':
            # Verificar que no hay otras asignaciones activas para este vehículo
            otras_asignaciones_activas = AsignacionVehiculo.objects.filter(
                vehiculo=obj.vehiculo,
                estado='activa'
            ).exclude(id=obj.id).exists()
            
            if not otras_asignaciones_activas:
                obj.vehiculo.estado = 'disponible'
                obj.vehiculo.save()


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
    list_display = ['vehiculo', 'año_fiscal', 'fecha_vencimiento', 'estado', 'fecha_pago']
    list_filter = ['estado', 'año_fiscal', 'fecha_vencimiento']
    search_fields = ['vehiculo__placas', 'vehiculo__marca']
    date_hierarchy = 'fecha_vencimiento'
    # list_editable removed: do not allow inline edits from changelist
    fieldsets = (
        ('Información Básica', {
            'fields': ('vehiculo', 'año_fiscal', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_vencimiento', 'fecha_pago')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
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
    list_display = ['vehiculo', 'tipo_verificacion', 'fecha_verificacion', 'fecha_vencimiento', 'estado']
    list_filter = ['tipo_verificacion', 'estado', 'fecha_verificacion']
    search_fields = ['vehiculo__placas', 'vehiculo__marca']
    date_hierarchy = 'fecha_verificacion'
    # list_editable removed: do not allow inline edits from changelist
    fieldsets = (
        ('Información Básica', {
            'fields': ('vehiculo', 'tipo_verificacion', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_verificacion', 'fecha_vencimiento')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
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