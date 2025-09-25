from django.contrib import admin
from django import forms
from .models import Asignacion
from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Empresa


class AsignacionForm(forms.ModelForm):
    class Meta:
        model = Asignacion
        fields = ['fecha', 'empleado', 'empresa', 'supervisor', 'detalles']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar solo activos
        self.fields['empleado'].queryset = Empleado.objects.filter(activo=True).select_related('usuario').order_by('numero_empleado')
        self.fields['empresa'].queryset = Empresa.objects.filter(activa=True).order_by('nombre')
        self.fields['supervisor'].queryset = Empleado.objects.filter(activo=True).select_related('usuario').order_by('numero_empleado')
        # Ayudas
        self.fields['supervisor'].help_text = 'Opcional. Si lo dejas vacío, se usará el Jefe Directo o el Puesto supervisor, si existen.'


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    form = AsignacionForm
    list_display = ('fecha', 'empleado', 'empresa', 'supervisor')
    list_filter = ('fecha', 'empresa')
    search_fields = (
        'empleado__usuario__first_name',
        'empleado__usuario__last_name',
        'empleado__numero_empleado',
        'empresa__nombre',
        'supervisor__usuario__first_name',
        'supervisor__usuario__last_name',
    )
    # Usamos selects normales para que veas opciones directamente
