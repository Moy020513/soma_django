from django import forms
from .models import PeriodoEstatusEmpleado

class NuevoPeriodoEstatusForm(forms.ModelForm):
    def clean(self):
        cleaned = super().clean()
        estatus = cleaned.get('estatus')
        fecha_inicio = cleaned.get('fecha_inicio')
        fecha_fin = cleaned.get('fecha_fin')
        empleado = self.initial.get('empleado_instance')
        if estatus == 'vacaciones' and fecha_inicio and empleado:
            from datetime import date
            if fecha_fin:
                dias = (fecha_fin - fecha_inicio).days + 1
            else:
                dias = 1
            disponibles = empleado.dias_vacaciones_disponibles()
            if dias > disponibles:
                raise forms.ValidationError(f"Te estás excediendo en días de vacaciones. Solo tienes {disponibles} disponibles.")
        return cleaned
    class Meta:
        model = PeriodoEstatusEmpleado
        fields = ['estatus', 'fecha_inicio', 'fecha_fin', 'observaciones']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'observaciones': forms.Textarea(attrs={'rows':2, 'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control form-control-sm').strip()
            style = field.widget.attrs.get('style', '')
            compact_style = 'max-width: 400px; padding: .25rem .5rem; font-size: .875rem;'
            field.widget.attrs['style'] = (style + ' ' + compact_style).strip()
