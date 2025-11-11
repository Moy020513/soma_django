from django.contrib import admin
from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from django.forms.widgets import DateInput, DateTimeInput
from .models import RegistroUbicacion, SemanaLaboralEmpleado, SemanaLaboralDia


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

class SemanaLaboralEmpleadoForm(forms.ModelForm):
    # Use a plain HTML5 date input (type=date) to avoid JS/widget localization issues
    semana_inicio = forms.DateField(
        widget=DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y']
    )

    class Meta:
        model = SemanaLaboralEmpleado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use the bound instance (self.instance) to set explicit initial value.
        # Setting initial as ISO string helps AdminDateWidget display correctly
        inst = getattr(self, 'instance', None)
        if inst and getattr(inst, 'semana_inicio', None):
            try:
                # Use ISO format which AdminDateWidget accepts reliably
                self.fields['semana_inicio'].initial = inst.semana_inicio.isoformat()
            except Exception:
                self.fields['semana_inicio'].initial = inst.semana_inicio


@admin.register(SemanaLaboralEmpleado)
class SemanaLaboralEmpleadoAdmin(admin.ModelAdmin):
    form = SemanaLaboralEmpleadoForm
    list_display = ['empleado', 'semana_inicio', 'horas_trabajadas', 'fecha_actualizacion']
    list_filter = ['semana_inicio']
    search_fields = ['empleado__usuario__first_name', 'empleado__usuario__last_name', 'empleado__numero_empleado']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    date_hierarchy = 'semana_inicio'


class SemanaLaboralDiaInline(admin.TabularInline):
    model = SemanaLaboralDia
    fields = ['fecha', 'entrada', 'salida', 'horas']
    readonly_fields = ['horas']
    extra = 0
    ordering = ['fecha']


class SemanaLaboralDiaForm(forms.ModelForm):
    fecha = forms.DateField(
        widget=DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y']
    )

    entrada = forms.DateTimeField(
        required=False,
        widget=DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M']
    )

    salida = forms.DateTimeField(
        required=False,
        widget=DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M']
    )

    class Meta:
        model = SemanaLaboralDia
        fields = ['fecha', 'entrada', 'salida', 'horas']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = getattr(self, 'instance', None)
        if inst:
            if getattr(inst, 'fecha', None):
                try:
                    self.fields['fecha'].initial = inst.fecha.isoformat()
                except Exception:
                    self.fields['fecha'].initial = inst.fecha
            if getattr(inst, 'entrada', None):
                try:
                    self.fields['entrada'].initial = inst.entrada.strftime('%Y-%m-%dT%H:%M')
                except Exception:
                    self.fields['entrada'].initial = inst.entrada
            if getattr(inst, 'salida', None):
                try:
                    self.fields['salida'].initial = inst.salida.strftime('%Y-%m-%dT%H:%M')
                except Exception:
                    self.fields['salida'].initial = inst.salida

SemanaLaboralEmpleadoAdmin.inlines = [SemanaLaboralDiaInline]
SemanaLaboralDiaInline.form = SemanaLaboralDiaForm