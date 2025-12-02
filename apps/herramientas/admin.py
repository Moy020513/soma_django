from django.contrib import admin
from django.shortcuts import redirect
from django.utils.html import format_html
from django.urls import reverse
from .models import Herramienta, AsignacionHerramienta, TransferenciaHerramienta
from .models import CombustibleRequest, CombustibleComprobante


@admin.register(Herramienta)
class HerramientaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'tipo', 'marca', 'codigo', 'estado']
    list_filter = ['categoria', 'tipo', 'estado']
    search_fields = ['nombre', 'marca', 'codigo']
    # list_editable removed: do not allow inline edits from changelist

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'categoria', 'lugar_pertenencia', 'tipo', 'marca', 'codigo')
        }),
        ('Consumo', {
            'fields': ('uso_energia',),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
    )

    readonly_fields = ('codigo',)

    class Media:
        js = ('js/herramienta_tipo.js',)

    def save_model(self, request, obj, form, change):
        # Asegura generación del código si no existe
        if not obj.codigo:
            # llamar super().save_model para respetar hooks y signals
            super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)


@admin.register(AsignacionHerramienta)
class AsignacionHerramientaAdmin(admin.ModelAdmin):
    list_display = ['herramienta', 'empleado', 'fecha_asignacion', 'fecha_devolucion', 'estado_herramienta', 'es_activa']
    list_filter = ['fecha_asignacion', 'fecha_devolucion', 'herramienta__categoria', 'herramienta__estado']
    search_fields = ['herramienta__nombre', 'empleado__nombre', 'empleado__apellidos']
    date_hierarchy = 'fecha_asignacion'
    
    fieldsets = (
        ('Asignación', {
            'fields': ('herramienta', 'empleado')
        }),
        ('Fechas', {
            'fields': ('fecha_asignacion', 'fecha_devolucion')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        # 'categoria' ya no es FK, no usar select_related sobre ella
        return super().get_queryset(request).select_related('herramienta', 'empleado')
    
    actions = ['marcar_como_devueltas']
    
    def estado_herramienta(self, obj):
        return obj.herramienta.get_estado_display()
    estado_herramienta.short_description = 'Estado de la herramienta'
    
    def es_activa(self, obj):
        return obj.fecha_devolucion is None
    es_activa.boolean = True
    es_activa.short_description = 'Asignación activa'
    
    def marcar_como_devueltas(self, request, queryset):
        from django.utils import timezone
        today = timezone.now().date()
        updated = queryset.filter(fecha_devolucion__isnull=True).update(fecha_devolucion=today)
        self.message_user(request, f'{updated} herramientas marcadas como devueltas.')
    marcar_como_devueltas.short_description = "Marcar como devueltas (fecha actual)"


@admin.register(TransferenciaHerramienta)
class TransferenciaHerramientaAdmin(admin.ModelAdmin):
    list_display = ['herramienta', 'empleado_origen', 'empleado_destino', 'estado', 'fecha_solicitud']
    list_filter = ['estado', 'fecha_solicitud']
    search_fields = ['herramienta__codigo', 'empleado_origen__usuario__username', 'empleado_destino__usuario__username']
    date_hierarchy = 'fecha_solicitud'
    readonly_fields = ['fecha_solicitud', 'fecha_respuesta', 'fecha_transferencia']


@admin.register(CombustibleRequest)
class CombustibleRequestAdmin(admin.ModelAdmin):
    list_display = ['empleado', 'herramienta', 'precio', 'fecha', 'estado', 'comprobante_link']
    list_filter = ['estado', 'fecha']
    search_fields = ['empleado__usuario__username', 'empleado__usuario__first_name', 'empleado__usuario__last_name']
    readonly_fields = ['fecha', 'comprobante_link']
    change_form_template = 'admin/herramientas/combustiblerequest_change_form.html'

    def comprobante_link(self, obj):
        if obj.comprobante:
            return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', obj.comprobante.url, obj.comprobante.name.split('/')[-1])
        return ''
    comprobante_link.short_description = 'Comprobante'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('<path:object_id>/aprobar/', self.admin_site.admin_view(self.aprobar_view), name='herramientas_combustiblerequest_aprobar'),
            path('<path:object_id>/rechazar/', self.admin_site.admin_view(self.rechazar_view), name='herramientas_combustiblerequest_rechazar'),
            path('<path:object_id>/comprobar/', self.admin_site.admin_view(self.comprobar_view), name='herramientas_combustiblerequest_comprobar'),
        ]
        return custom + urls

    def aprobar_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj and obj.estado == 'pendiente':
            obj.estado = 'revisado'
            obj.save()
            try:
                from apps.notificaciones.models import Notificacion
                try:
                    url = reverse('herramientas:subir_comprobante_combustible', args=[obj.pk])
                except Exception:
                    url = ''
                titulo = '✅ Solicitud de combustible aprobada'
                if not Notificacion.objects.filter(usuario=obj.empleado.usuario, titulo=titulo, url=url).exists():
                    Notificacion.objects.create(usuario=obj.empleado.usuario, titulo=titulo, mensaje=f'Tu solicitud de combustible del {obj.fecha.date()} por ${obj.precio} ha sido aprobada. Ahora puedes subir el comprobante para completar el proceso.', tipo='success', url=url)
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
                try:
                    url = reverse('herramientas:subir_comprobante_combustible', args=[obj.pk])
                except Exception:
                    url = ''
                titulo = '❌ Solicitud de combustible rechazada'
                if not Notificacion.objects.filter(usuario=obj.empleado.usuario, titulo=titulo, url=url).exists():
                    Notificacion.objects.create(usuario=obj.empleado.usuario, titulo=titulo, mensaje=f'Tu solicitud de combustible del {obj.fecha.date()} por ${obj.precio} ha sido revisada y fue rechazada. Si corresponde, sube el comprobante o revisa las observaciones.', tipo='danger', url=url)
            except Exception:
                pass
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

    def comprobar_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if not obj:
            return redirect(request.META.get('HTTP_REFERER', '/admin/'))
        if request.method == 'POST':
            from decimal import Decimal
            try:
                accion = request.POST.get('accion')
                monto_str = request.POST.get('monto_comprobado')
                monto = None
                if monto_str:
                    monto = Decimal(monto_str.replace(',', '').strip())
                if accion == 'cubre_todo' or (monto is not None and monto >= obj.precio):
                    obj.monto_comprobado = obj.precio
                    obj.estado = 'comprobado'
                    obj.save()
                    try:
                        from apps.notificaciones.models import Notificacion
                        titulo = '✅ Comprobante comprobado (completo)'
                        mensaje = f'Se ha comprobado el comprobante de tu solicitud del {obj.fecha.date()} por ${obj.precio}. El comprobante cubre el monto solicitado. Ya puedes realizar una nueva solicitud si lo deseas.'
                        noti = Notificacion.objects.create(usuario=obj.empleado.usuario, titulo=titulo, mensaje=mensaje, tipo='success', url='')
                        try:
                            noti.url = reverse('notificaciones:detalle_usuario', args=[noti.pk]) + f'?combustible_id={obj.pk}'
                            noti.save()
                        except Exception:
                            pass
                    except Exception:
                        pass
                else:
                    if monto is None:
                        return redirect(request.META.get('HTTP_REFERER', '/admin/'))
                    if monto > obj.precio:
                        monto = obj.precio
                    obj.monto_comprobado = monto
                    obj.estado = 'parcial'
                    obj.save()
                    try:
                        from apps.notificaciones.models import Notificacion
                        faltante = obj.precio - monto
                        mensaje = f'Se ha comprobado ${monto} de tu solicitud del {obj.fecha.date()} por ${obj.precio}. Falta por comprobar ${faltante}. Por favor sube el comprobante adicional o consulta con administración.'
                        try:
                            base_url = reverse('herramientas:subir_comprobante_combustible', args=[obj.pk])
                        except Exception:
                            base_url = ''
                        Notificacion.objects.create(usuario=obj.empleado.usuario, titulo='ℹ️ Comprobante parcialmente comprobado', mensaje=mensaje, tipo='warning', url=base_url)
                    except Exception:
                        pass
            except Exception:
                pass
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))


@admin.register(CombustibleComprobante)
class CombustibleComprobanteAdmin(admin.ModelAdmin):
    list_display = ['combustible_request', 'archivo_link', 'uploaded_at']
    readonly_fields = ['archivo_link', 'uploaded_at']
    search_fields = ['combustible_request__empleado__usuario__username']

    def archivo_link(self, obj):
        if obj and obj.archivo:
            return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', obj.archivo.url, obj.archivo.name.split('/')[-1])
        return ''
    archivo_link.short_description = 'Archivo'