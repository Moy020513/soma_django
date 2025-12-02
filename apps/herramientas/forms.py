from django import forms
from django.core.exceptions import ValidationError
from .models import TransferenciaHerramienta, Herramienta, AsignacionHerramienta, CombustibleRequest, CombustibleComprobante
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


class CombustibleRequestCreateForm(forms.ModelForm):
    class Meta:
        model = CombustibleRequest
        fields = ['precio', 'observaciones']
        widgets = {
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'precio': 'Monto solicitado (MXN)',
            'observaciones': 'Observaciones (opcional)'
        }

    def clean_precio(self):
        p = self.cleaned_data.get('precio')
        if p is None or p <= 0:
            raise forms.ValidationError('Ingresa un precio válido mayor a 0')
        return p


class CombustibleComprobanteForm(forms.ModelForm):
    class Meta:
        # El formulario para subir comprobante debe apuntar a CombustibleRequest
        # para establecer `comprobante` en la solicitud (igual que en gasolina).
        model = CombustibleRequest
        fields = ['comprobante']
        widgets = {
            'comprobante': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'comprobante': 'Comprobante de pago (imagen/PDF)'
        }

    def clean_comprobante(self):
        c = self.cleaned_data.get('comprobante')
        if not c:
            raise forms.ValidationError('Debes adjuntar un comprobante.')
        return c
