from django import forms
from django.core.exceptions import ValidationError
from .models import TransferenciaVehicular, Vehiculo
from apps.recursos_humanos.models import Empleado


class SolicitudTransferenciaForm(forms.ModelForm):
    """Formulario para solicitar una transferencia de vehículo"""
    
    class Meta:
        model = TransferenciaVehicular
        fields = ['empleado_destino', 'observaciones_solicitud']
        widgets = {
            'empleado_destino': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'observaciones_solicitud': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Motivo de la transferencia, condiciones actuales del vehículo, etc.'
            }),
        }
        labels = {
            'empleado_destino': 'Empleado destinatario',
            'observaciones_solicitud': 'Observaciones de la solicitud',
        }
        help_texts = {
            'empleado_destino': 'Selecciona el empleado al que deseas transferir el vehículo',
            'observaciones_solicitud': 'Describe el motivo de la transferencia y cualquier información relevante sobre el estado del vehículo',
        }
    
    def __init__(self, *args, **kwargs):
        empleado_actual = kwargs.pop('empleado_actual', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar empleados activos excluyendo al empleado actual
        if empleado_actual:
            self.fields['empleado_destino'].queryset = Empleado.objects.filter(
                activo=True
            ).exclude(id=empleado_actual.id).select_related('usuario')
        else:
            self.fields['empleado_destino'].queryset = Empleado.objects.filter(
                activo=True
            ).select_related('usuario')
    
    def clean_empleado_destino(self):
        empleado_destino = self.cleaned_data['empleado_destino']
        
        # Verificar que el empleado destino no tenga ya un vehículo asignado
        from .models import AsignacionVehiculo
        if AsignacionVehiculo.objects.filter(empleado=empleado_destino, estado='activa').exists():
            raise ValidationError(
                f"El empleado {empleado_destino.usuario.get_full_name()} ya tiene un vehículo asignado."
            )
        
        return empleado_destino


class InspeccionTransferenciaForm(forms.ModelForm):
    """Formulario para que el empleado destino haga la inspección del vehículo"""
    
    class Meta:
        model = TransferenciaVehicular
        fields = ['kilometraje_transferencia', 'observaciones_inspeccion']
        widgets = {
            'kilometraje_transferencia': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'required': True
            }),
            'observaciones_inspeccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe el estado actual del vehículo: daños, faltantes, limpieza, funcionamiento, etc.',
                'required': True
            }),
        }
        labels = {
            'kilometraje_transferencia': 'Kilometraje actual del vehículo',
            'observaciones_inspeccion': 'Observaciones de la inspección',
        }
        help_texts = {
            'kilometraje_transferencia': 'Registra el kilometraje exacto que muestra el vehículo al momento de la inspección',
            'observaciones_inspeccion': 'Detalla cualquier daño, faltante o condición especial del vehículo que observes durante la inspección',
        }


class RespuestaTransferenciaForm(forms.Form):
    """Formulario para que el empleado origen responda a la inspección"""
    
    OPCIONES_RESPUESTA = [
        ('aprobar', 'Aprobar transferencia'),
        ('rechazar', 'Rechazar transferencia'),
    ]
    
    respuesta = forms.ChoiceField(
        choices=OPCIONES_RESPUESTA,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Respuesta a la inspección'
    )
    
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones adicionales (opcional)'
        }),
        label='Observaciones',
        required=False,
        help_text='Puedes agregar comentarios sobre tu decisión'
    )


class RegistroUsoForm(forms.ModelForm):
    """Formulario para registrar el uso diario del vehículo (kilometraje diario y observaciones).

    Nota: para registros diarios sólo necesitamos un único valor de kilometraje (el odómetro al final del día).
    Guardamos este valor en el campo `kilometraje_fin` del modelo existente para evitar alterar la estructura.
    """
    class Meta:
        from .models import RegistroUso
        model = RegistroUso
        # Eliminamos el campo 'destino' del formulario de registro diario
        fields = ['fecha', 'kilometraje_fin', 'proposito', 'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'kilometraje_fin': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'proposito': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'required': False}),
        }
        labels = {
            'fecha': 'Fecha',
            'kilometraje_fin': 'Kilometraje (registro diario)',
            'proposito': 'Propósito',
            'observaciones': 'Observaciones (opcional)'
        }

    def clean(self):
        cleaned = super().clean()
        kf = cleaned.get('kilometraje_fin')
        if kf is not None and kf < 0:
            raise forms.ValidationError('El kilometraje no puede ser negativo.')
        return cleaned