from django.contrib import admin
from .models import Herramienta, AsignacionHerramienta, TransferenciaHerramienta


@admin.register(Herramienta)
class HerramientaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'marca', 'codigo', 'estado']
    list_filter = ['categoria', 'estado']
    search_fields = ['nombre', 'marca', 'codigo']
    # list_editable removed: do not allow inline edits from changelist

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'categoria', 'lugar_pertenencia', 'marca', 'codigo')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
    )

    readonly_fields = ('codigo',)

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