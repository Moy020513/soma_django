from django.contrib import admin
from django import forms
from .models import Asignacion
from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Empresa
from .forms_custom import EmpleadoAsignacionFormSet, AsignacionCustomForm


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    form = AsignacionCustomForm
    change_form_template = 'admin/asignaciones/asignacion/change_form.html'
    list_display = ('fecha', 'get_empleados', 'empresa', 'supervisor')
    list_filter = ('fecha', 'empresa')
    search_fields = (
        'empleados__usuario__first_name',
        'empleados__usuario__last_name',
        'empleados__numero_empleado',
        'empresa__nombre',
        'supervisor__usuario__first_name',
        'supervisor__usuario__last_name',
    )

    def get_empleados(self, obj):
        return ', '.join([str(e) for e in obj.empleados.all()])
    get_empleados.short_description = 'Empleados'

    def render_change_form(self, request, context, *args, **kwargs):
        if request.method == 'POST':
            empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados')
        else:
            empleados_formset = EmpleadoAsignacionFormSet(prefix='empleados')
        context['empleados_formset'] = empleados_formset
        return super().render_change_form(request, context, *args, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados')
        if empleados_formset.is_valid():
            empleados = [f.cleaned_data['empleado'] for f in empleados_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE', False)]
            obj.empleados.set(empleados)
