from django import forms
from django.forms import formset_factory
from apps.recursos_humanos.models import Empleado
from .models import Asignacion

class EmpleadoAsignacionForm(forms.Form):
    empleado = forms.ModelChoiceField(
        queryset=Empleado.objects.filter(activo=True).order_by('numero_empleado'),
        label='Empleado',
        required=True
    )

EmpleadoAsignacionFormSet = formset_factory(EmpleadoAsignacionForm, extra=1, can_delete=True)

class AsignacionCustomForm(forms.ModelForm):
    class Meta:
        model = Asignacion
        exclude = ['empleados']

    archivos = forms.FileField(required=False, label='Archivos adjuntos')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empresa'].queryset = self.fields['empresa'].queryset.filter(activa=True)
        self.fields['supervisor'].queryset = self.fields['supervisor'].queryset.filter(activo=True)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Los empleados se asignan en la vista
        if commit:
            instance.save()
        return instance
