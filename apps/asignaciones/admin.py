from django.contrib import admin
from .models import Asignacion


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'empleado', 'empresa', 'supervisor', 'completada')
    list_filter = ('fecha', 'empresa', 'completada')
    search_fields = (
        'empleado__usuario__first_name',
        'empleado__usuario__last_name',
        'empleado__numero_empleado',
        'empresa__nombre',
        'supervisor__usuario__first_name',
        'supervisor__usuario__last_name',
    )
    autocomplete_fields = ('empleado', 'empresa', 'supervisor')
