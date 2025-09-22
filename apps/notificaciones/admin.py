from django.contrib import admin
from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'usuario', 'tipo', 'leida', 'fecha_creacion']
    list_filter = ['tipo', 'leida', 'fecha_creacion']
    search_fields = ['titulo', 'mensaje', 'usuario__email', 'usuario__first_name', 'usuario__last_name']
    readonly_fields = ['fecha_creacion']
    list_editable = ['leida']
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        (None, {
            'fields': ('usuario', 'titulo', 'mensaje')
        }),
        ('Configuración', {
            'fields': ('tipo', 'leida', 'url')
        }),
        ('Información adicional', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario')
    
    actions = ['marcar_como_leidas', 'marcar_como_no_leidas']
    
    def marcar_como_leidas(self, request, queryset):
        updated = queryset.update(leida=True)
        self.message_user(request, f'{updated} notificaciones marcadas como leídas.')
    marcar_como_leidas.short_description = "Marcar seleccionadas como leídas"
    
    def marcar_como_no_leidas(self, request, queryset):
        updated = queryset.update(leida=False)
        self.message_user(request, f'{updated} notificaciones marcadas como no leídas.')
    marcar_como_no_leidas.short_description = "Marcar seleccionadas como no leídas"