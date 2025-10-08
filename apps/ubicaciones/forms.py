from django import forms
from .models import RegistroUbicacion


class RegistroUbicacionForm(forms.ModelForm):
    """Formulario para registro de ubicación"""
    
    class Meta:
        model = RegistroUbicacion
        fields = ['empleado', 'latitud', 'longitud', 'precision', 'tipo']
        widgets = {
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
            'precision': forms.HiddenInput(),
            'empleado': forms.HiddenInput(),
        }
    
    def __init__(self, *args, empleado=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empleado:
            self.fields['empleado'].initial = empleado
    
    def clean(self):
        cleaned_data = super().clean()
        empleado = cleaned_data.get('empleado')
        tipo = cleaned_data.get('tipo')
        
        if empleado and tipo:
            # Verificar si ya existe un registro del mismo tipo hoy
            if RegistroUbicacion.ya_registro_hoy(empleado, tipo):
                raise forms.ValidationError(
                    f'Ya se registró {tipo} para hoy. Solo se permite un registro por día.'
                )
        
        return cleaned_data