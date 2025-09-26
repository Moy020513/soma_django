from django.contrib import admin
from apps.notificaciones.models import Notificacion, RespuestaNotificacion


@admin.register(RespuestaNotificacion)
class RespuestaNotificacionAdmin(admin.ModelAdmin):
    list_display = ['notificacion', 'usuario', 'mensaje', 'documento', 'fecha_respuesta', 'revisada_admin']
    list_filter = ['revisada_admin', 'fecha_respuesta', 'usuario']
    search_fields = ['mensaje', 'usuario__email', 'notificacion__titulo']
    readonly_fields = ['fecha_respuesta']
    date_hierarchy = 'fecha_respuesta'
    actions = ['marcar_como_revisadas']

    def marcar_como_revisadas(self, request, queryset):
        updated = queryset.update(revisada_admin=True)
        self.message_user(request, f'{updated} respuestas marcadas como revisadas.')
    marcar_como_revisadas.short_description = "Marcar seleccionadas como revisadas"
from .forms import NotificacionForm



@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    def response_add(self, request, obj, post_url_continue=None):
        from django.contrib import messages
        # Elimina todos los mensajes automáticos antes de mostrar el personalizado
        if hasattr(request, '_messages'):
            storage = request._messages
            if hasattr(storage, '_queued_messages'):
                storage._queued_messages = []
        self.message_user(request, 'La Notificación fue agregada correctamente.', level=messages.SUCCESS)
        # Redirige igual que el método padre, pero sin mostrar el mensaje automático
        from django.http import HttpResponseRedirect
        opts = self.model._meta
        pk_value = obj._get_pk_val()
        if "_addanother" in request.POST:
            return HttpResponseRedirect(request.path)
        elif "_continue" in request.POST:
            return HttpResponseRedirect(f"../{pk_value}/change/")
        else:
            return HttpResponseRedirect("../")
    def get_deleted_objects(self, objs, request):
        # Suprime el mensaje automático de Django devolviendo una lista vacía
        return [], {}, set(), []
    def delete_queryset(self, request, queryset):
        # Eliminar sin mostrar mensaje aquí
        for obj in queryset:
            obj.delete()

    def response_delete(self, request, obj_display, obj_id):
        from django.contrib import messages
        # Elimina todos los mensajes automáticos antes de mostrar el personalizado
        if hasattr(request, '_messages'):
            storage = request._messages
            if hasattr(storage, '_queued_messages'):
                storage._queued_messages = []
        self.message_user(request, 'La Notificación fue eliminada con éxito.', level=messages.SUCCESS)
        # Redirige SIEMPRE al listado de notificaciones, evitando que Django busque el objeto eliminado
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        opts = self.model._meta
        changelist_url = reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')
        return HttpResponseRedirect(changelist_url)

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

    def delete_model(self, request, obj):
        obj.delete()