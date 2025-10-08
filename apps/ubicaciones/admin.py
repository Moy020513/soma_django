from django.contrib import admin
from .models import RegistroUbicacion


@admin.register(RegistroUbicacion)
class RegistroUbicacionAdmin(admin.ModelAdmin):
    list_display = [
        'empleado', 'tipo', 'fecha_local_formatted', 
        'coordenadas_str', 'precision'
    ]
    list_filter = ['tipo', 'timestamp', 'empleado']
    search_fields = ['empleado__usuario__first_name', 'empleado__usuario__last_name', 'empleado__numero_empleado']
    readonly_fields = ['fecha_creacion', 'timestamp']
    date_hierarchy = 'timestamp'
    
    def fecha_local_formatted(self, obj):
        return obj.fecha_local.strftime('%d/%m/%Y %H:%M:%S')
    fecha_local_formatted.short_description = 'Fecha y Hora (Local)'
    fecha_local_formatted.admin_order_field = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('empleado__usuario')