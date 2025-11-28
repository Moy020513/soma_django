from django.contrib import admin
from .models import (
    Vehiculo, AsignacionVehiculo, TransferenciaVehicular, 
    RegistroUso, TenenciaVehicular, VerificacionVehicular
)
from .models import VehiculoExterno, AsignacionVehiculoExterno
from .models import GasolinaRequest
from django.utils.html import format_html
from django.shortcuts import redirect


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

@admin.register(VehiculoExterno)
class VehiculoExternoAdmin(admin.ModelAdmin):
    list_display = ['placas', 'modelo', 'numero_seguro', 'estado']
    list_filter = ['estado']
    search_fields = ['placas', 'modelo', 'numero_seguro']
    fieldsets = (
        ('Información Básica', {
            'fields': ('placas', 'modelo', 'numero_seguro')
        }),
        ('Estado', {
            'fields': ('estado', 'observaciones')
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
    list_display = ['vehiculo', 'empleado', 'fecha', 'proposito', 'kilometraje_inicio', 'kilometraje_fin']
    list_filter = ['fecha', 'vehiculo__marca']
    search_fields = ['vehiculo__placas', 'empleado__nombre', 'proposito']
    date_hierarchy = 'fecha'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('vehiculo', 'empleado', 'fecha')
        }),
        ('Viaje', {
            'fields': ('proposito', 'kilometraje_inicio', 'kilometraje_fin')
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
    list_display = ['vehiculo', 'tipo_verificacion', 'fecha_verificacion', 'fecha_vencimiento', 'estado', 'documento_link']
    list_filter = ['tipo_verificacion', 'estado', 'fecha_verificacion']
    search_fields = ['vehiculo__placas', 'vehiculo__marca']
    date_hierarchy = 'fecha_verificacion'
    # list_editable removed: do not allow inline edits from changelist
    fieldsets = (
        ('Información Básica', {
            'fields': ('vehiculo', 'tipo_verificacion', 'numero_verificacion', 'estado', 'documento_verificacion')
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

    def documento_link(self, obj):
        if obj.documento_verificacion:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                obj.documento_verificacion.url,
                obj.documento_verificacion.name.split('/')[-1]
            )
        return ''
    documento_link.short_description = 'Documento'
    documento_link.allow_tags = True

@admin.register(AsignacionVehiculoExterno)
class AsignacionVehiculoExternoAdmin(admin.ModelAdmin):
    list_display = ['vehiculo_externo', 'empleado', 'fecha_asignacion', 'fecha_finalizacion', 'estado']
    list_filter = ['estado', 'fecha_asignacion']
    search_fields = ['vehiculo_externo__placas', 'empleado__usuario__username']
    date_hierarchy = 'fecha_asignacion'

    fieldsets = (
        (None, {
            'fields': ('vehiculo_externo', 'empleado')
        }),
        ('Fechas', {
            'fields': ('fecha_asignacion', 'fecha_finalizacion', 'estado')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Actualizar estado del vehículo externo según asignación
        if obj.estado == 'activa':
            obj.vehiculo_externo.estado = 'asignado'
            obj.vehiculo_externo.save()
        elif obj.estado == 'finalizada':
            otras = AsignacionVehiculoExterno.objects.filter(
                vehiculo_externo=obj.vehiculo_externo,
                estado='activa'
            ).exclude(id=obj.id).exists()
            if not otras:
                obj.vehiculo_externo.estado = 'disponible'
                obj.vehiculo_externo.save()


@admin.register(GasolinaRequest)
class GasolinaRequestAdmin(admin.ModelAdmin):
    list_display = ['empleado', 'get_vehiculo_display', 'precio', 'fecha', 'estado', 'comprobante_link']
    list_filter = ['estado', 'fecha']
    search_fields = ['empleado__usuario__username', 'empleado__usuario__first_name', 'empleado__usuario__last_name']
    readonly_fields = ['fecha', 'comprobante_link']
    actions = ['aprobar_solicitudes', 'rechazar_solicitudes']
    change_form_template = 'admin/flota_vehicular/gasolinarequest_change_form.html'

    def get_vehiculo_display(self, obj):
        return obj.vehiculo or obj.vehiculo_externo
    get_vehiculo_display.short_description = 'Vehículo'

    def comprobante_link(self, obj):
        if obj.comprobante:
            return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', obj.comprobante.url, obj.comprobante.name.split('/')[-1])
        return ''
    comprobante_link.short_description = 'Comprobante'

    def aprobar_solicitudes(self, request, queryset):
        updated = queryset.filter(estado='pendiente').update(estado='revisado')
        # Notificar a empleados
        for req in queryset:
            try:
                from apps.notificaciones.models import Notificacion
                from django.urls import reverse
                noti = Notificacion.objects.create(
                    usuario=req.empleado.usuario,
                    titulo='✅ Solicitud de gasolina aprobada',
                    mensaje=f'Tu solicitud de gasolina del {req.fecha.date()} por ${req.precio} ha sido aprobada. Ahora puedes subir el comprobante para completar el proceso.',
                    tipo='success',
                    leida=False,
                )
                try:
                    noti.url = reverse('flota:subir_comprobante_gasolina', args=[req.pk])
                    noti.save()
                except Exception:
                    pass
            except Exception:
                pass
        self.message_user(request, f'{updated} solicitudes marcadas como aprobadas.')
    aprobar_solicitudes.short_description = 'Marcar solicitudes seleccionadas como Aprobadas'

    def rechazar_solicitudes(self, request, queryset):
        updated = queryset.filter(estado='pendiente').update(estado='rechazado')
        for req in queryset:
            try:
                from apps.notificaciones.models import Notificacion
                from django.urls import reverse
                noti = Notificacion.objects.create(
                    usuario=req.empleado.usuario,
                    titulo='❌ Solicitud de gasolina rechazada',
                    mensaje=f'Tu solicitud de gasolina del {req.fecha.date()} por ${req.precio} ha sido revisada y fue rechazada. Si corresponde, sube el comprobante o revisa las observaciones.',
                    tipo='danger',
                    leida=False,
                )
                try:
                    noti.url = reverse('flota:subir_comprobante_gasolina', args=[req.pk])
                    noti.save()
                except Exception:
                    pass
            except Exception:
                pass
        self.message_user(request, f'{updated} solicitudes marcadas como rechazadas.')
    rechazar_solicitudes.short_description = 'Marcar solicitudes seleccionadas como Rechazadas'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('<path:object_id>/aprobar/', self.admin_site.admin_view(self.aprobar_view), name='flota_vehicular_gasolinarequest_aprobar'),
            path('<path:object_id>/rechazar/', self.admin_site.admin_view(self.rechazar_view), name='flota_vehicular_gasolinarequest_rechazar'),
            path('<path:object_id>/comprobar/', self.admin_site.admin_view(self.comprobar_view), name='flota_vehicular_gasolinarequest_comprobar'),
        ]
        return custom + urls

    def aprobar_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj and obj.estado == 'pendiente':
            obj.estado = 'revisado'
            obj.save()
            # Asegurar que el empleado reciba una notificación (evitar duplicados si ya existe)
            try:
                from apps.notificaciones.models import Notificacion
                from django.urls import reverse
                url = ''
                try:
                    url = reverse('flota:subir_comprobante_gasolina', args=[obj.pk])
                except Exception:
                    url = ''
                titulo = '✅ Solicitud de gasolina aprobada'
                if not Notificacion.objects.filter(usuario=obj.empleado.usuario, titulo=titulo, url=url).exists():
                    Notificacion.objects.create(
                        usuario=obj.empleado.usuario,
                        titulo=titulo,
                        mensaje=f'Tu solicitud de gasolina del {obj.fecha.date()} por ${obj.precio} ha sido aprobada. Ahora puedes subir el comprobante para completar el proceso.',
                        tipo='success',
                        url=url
                    )
            except Exception:
                pass
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

    def rechazar_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj and obj.estado == 'pendiente':
            obj.estado = 'rechazado'
            obj.save()
            try:
                from apps.notificaciones.models import Notificacion
                from django.urls import reverse
                url = ''
                try:
                    url = reverse('flota:subir_comprobante_gasolina', args=[obj.pk])
                except Exception:
                    url = ''
                titulo = '❌ Solicitud de gasolina rechazada'
                if not Notificacion.objects.filter(usuario=obj.empleado.usuario, titulo=titulo, url=url).exists():
                    Notificacion.objects.create(
                        usuario=obj.empleado.usuario,
                        titulo=titulo,
                        mensaje=f'Tu solicitud de gasolina del {obj.fecha.date()} por ${obj.precio} ha sido revisada y fue rechazada. Si corresponde, sube el comprobante o revisa las observaciones.',
                        tipo='danger',
                        url=url
                    )
            except Exception:
                pass
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

    def comprobar_view(self, request, object_id):
        """Vista admin para que el admin registre si el comprobante cubre todo o parte del monto."""
        obj = self.get_object(request, object_id)
        if not obj:
            return redirect(request.META.get('HTTP_REFERER', '/admin/'))

        # Solo procesar POST
        if request.method == 'POST':
            from decimal import Decimal, InvalidOperation
            try:
                accion = request.POST.get('accion')
                monto_str = request.POST.get('monto_comprobado')
                monto = None
                if monto_str:
                    monto = Decimal(monto_str.replace(',', '').strip())
                # Si se indica que cubre todo o monto == precio
                if accion == 'cubre_todo' or (monto is not None and monto >= obj.precio):
                    obj.monto_comprobado = obj.precio
                    obj.estado = 'comprobado'
                    obj.save()

                    # Notificar al empleado que todo fue comprobado
                    try:
                        from apps.notificaciones.models import Notificacion
                        from django.urls import reverse
                        titulo = '✅ Comprobante comprobado (completo)'
                        mensaje = f'Se ha comprobado el comprobante de tu solicitud del {obj.fecha.date()} por ${obj.precio}. El comprobante cubre el monto solicitado. Ya puedes realizar una nueva solicitud si lo deseas.'
                        # Para el caso completo, queremos enviar al usuario al detalle de la
                        # notificación (no a subir comprobante). Creamos la notificación y
                        # luego la actualizamos para apuntar a su propia pantalla de detalle
                        # con el parametro gasolina_id para que el detalle muestre el request.
                        try:
                            noti = Notificacion.objects.create(
                                usuario=obj.empleado.usuario,
                                titulo=titulo,
                                mensaje=mensaje,
                                tipo='success',
                                url=''
                            )
                            try:
                                noti.url = reverse('notificaciones:detalle_usuario', args=[noti.pk]) + f'?gasolina_id={obj.pk}'
                                noti.save()
                            except Exception:
                                # No bloquear si no se puede construir la URL
                                pass
                        except Exception:
                            pass
                    except Exception:
                        pass

                else:
                    # Parcial
                    if monto is None:
                        # Si no se entregó monto válido, redirigir sin cambios
                        return redirect(request.META.get('HTTP_REFERER', '/admin/'))
                    # Limitar monto a no mayor que el precio
                    if monto > obj.precio:
                        monto = obj.precio
                    obj.monto_comprobado = monto
                    obj.estado = 'parcial'
                    obj.save()

                    # Notificar al empleado del monto comprobado y lo que falta
                    try:
                        from apps.notificaciones.models import Notificacion
                        from django.urls import reverse
                        titulo = 'ℹ️ Comprobante parcialmente comprobado'
                        faltante = obj.precio - monto
                        mensaje = f'Se ha comprobado ${monto} de tu solicitud del {obj.fecha.date()} por ${obj.precio}. Falta por comprobar ${faltante}. Por favor sube el comprobante adicional o consulta con administración.'
                        try:
                            base_url = reverse('flota:subir_comprobante_gasolina', args=[obj.pk])
                        except Exception:
                            base_url = ''
                        noti = Notificacion.objects.create(
                            usuario=obj.empleado.usuario,
                            titulo=titulo,
                            mensaje=mensaje,
                            tipo='warning',
                            url=base_url
                        )
                    except Exception:
                        pass
            except Exception:
                # No bloquear al admin si hubo error parseando monto
                pass

        return redirect(request.META.get('HTTP_REFERER', '/admin/'))