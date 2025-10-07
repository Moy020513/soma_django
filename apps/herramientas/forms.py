from django import forms
from django.core.exceptions import ValidationError
from .models import TransferenciaHerramienta, Herramienta, AsignacionHerramienta
from apps.recursos_humanos.models import Empleado


class SolicitudTransferenciaHerramientaForm(forms.ModelForm):
    herramienta_select = forms.ModelChoiceField(
        queryset=Herramienta.objects.none(),
        required=False,
        label='Herramienta a transferir',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = TransferenciaHerramienta
        fields = ['empleado_destino', 'observaciones_solicitud']
        widgets = {
            'empleado_destino': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'observaciones_solicitud': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Motivo y estado actual de la herramienta'})
        }
        labels = {
            'empleado_destino': 'Empleado destino',
            'observaciones_solicitud': 'Observaciones de la solicitud'
        }

    def __init__(self, *args, **kwargs):
        empleado_actual = kwargs.pop('empleado_actual', None)
        pre_herramienta_id = kwargs.pop('pre_herramienta_id', None)
        super().__init__(*args, **kwargs)
        qs = Empleado.objects.filter(activo=True).select_related('usuario')
        if empleado_actual:
            qs = qs.exclude(id=empleado_actual.id)
            # Herramientas activas asignadas al empleado
            asignaciones = AsignacionHerramienta.objects.filter(
                empleado=empleado_actual,
                fecha_devolucion__isnull=True
            ).select_related('herramienta')
            herramientas = [a.herramienta for a in asignaciones]
            if len(herramientas) > 1:
                self.fields['herramienta_select'].queryset = Herramienta.objects.filter(id__in=[h.id for h in herramientas])
                if pre_herramienta_id and any(h.id == pre_herramienta_id for h in herramientas):
                    self.fields['herramienta_select'].initial = pre_herramienta_id
            else:
                # Si solo hay una, ocultar el campo (no se usa)
                self.fields['herramienta_select'].widget = forms.HiddenInput()
        else:
            self.fields['herramienta_select'].widget = forms.HiddenInput()
        self.fields['empleado_destino'].queryset = qs
        self.fields['empleado_destino'].empty_label = '--- Selecciona empleado destino ---'

    def clean_empleado_destino(self):
        empleado_destino = self.cleaned_data['empleado_destino']
        # Permitir múltiples herramientas por empleado (a diferencia de vehículos) - si se quisiera restringir, se haría aquí.
        return empleado_destino

    def get_herramienta(self, empleado_actual):
        """Determina la herramienta a transferir según selección o única asignada."""
        if not empleado_actual:
            return None
        asignaciones = AsignacionHerramienta.objects.filter(
            empleado=empleado_actual,
            fecha_devolucion__isnull=True
        ).select_related('herramienta')
        if not asignaciones:
            return None
        if len(asignaciones) == 1:
            return asignaciones[0].herramienta
        # Si hay varias, usar la seleccionada
        return self.cleaned_data.get('herramienta_select')


class RespuestaTransferenciaHerramientaForm(forms.Form):
    RESPUESTAS = [
        ('aprobar', 'Aprobar transferencia'),
        ('rechazar', 'Rechazar transferencia'),
    ]
    respuesta = forms.ChoiceField(choices=RESPUESTAS, widget=forms.RadioSelect, label='Respuesta')
    observaciones = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones (opcional)'}), required=False)
