from django.contrib import admin
from .models import Notificacion
from .forms import NotificacionForm


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    save_on_top = False
    form = NotificacionForm
    list_display = ['titulo', 'usuario', 'tipo', 'leida', 'fecha_creacion']
    list_filter = ['tipo', 'leida', 'fecha_creacion']
    search_fields = ['titulo', 'mensaje', 'usuario__email', 'usuario__first_name', 'usuario__last_name']
    readonly_fields = ['fecha_creacion']
    list_editable = ['leida']
    date_hierarchy = 'fecha_creacion'
    
    # En el formulario no se muestran 'leida', 'url' ni 'fecha_creacion'
    fieldsets = (
        (None, {
            'fields': ('usuario', 'titulo', 'mensaje', 'tipo')
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