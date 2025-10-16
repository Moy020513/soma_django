from django import forms
from .models import Inasistencia, Empleado

class InasistenciaForm(forms.ModelForm):
    class Meta:
        model = Inasistencia
        fields = ['empleado', 'fecha', 'tipo', 'dias', 'observaciones']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'observaciones': forms.Textarea(attrs={'rows':3, 'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        print('================= INASISTENCIA FORMULARIO =================')
        super().__init__(*args, **kwargs)
        # Mostrar todos los empleados en el select (sin filtro)
        self.fields['empleado'].queryset = Empleado.objects.all()
        # Ocultar el campo registrada_por en el formulario
        if 'registrada_por' in self.fields:
            self.fields['registrada_por'].widget = forms.HiddenInput()
        # Depuración: imprimir queryset en consola del servidor
        print('Empleados en queryset:', list(self.fields['empleado'].queryset))
        # compactar estilos como en otros formularios
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control form-control-sm').strip()
            style = field.widget.attrs.get('style', '')
            compact_style = 'max-width: 500px; padding: .25rem .5rem; font-size: .875rem;'
            field.widget.attrs['style'] = (style + ' ' + compact_style).strip()

    def clean_dias(self):
        dias = self.cleaned_data.get('dias') or 0
        if dias < 1:
            raise forms.ValidationError('Los días deben ser al menos 1.')
        return dias

    def clean(self):
        cleaned = super().clean()
        empleado = cleaned.get('empleado')
        fecha = cleaned.get('fecha')
        if empleado and fecha:
            # evitar duplicados: unique_together maneja, pero dar mensaje más amable
            if Inasistencia.objects.filter(empleado=empleado, fecha=fecha).exists():
                raise forms.ValidationError('Ya existe una inasistencia registrada para ese empleado en la fecha indicada.')
        return cleaned
