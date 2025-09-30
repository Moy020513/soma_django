from django import forms
from django.forms import formset_factory
from apps.recursos_humanos.models import Empleado
from .models import Asignacion, ActividadAsignada
class ActividadAsignadaForm(forms.Form):
    nombre = forms.CharField(max_length=120, label='Actividad')
    porcentaje = forms.IntegerField(min_value=1, max_value=100, label='Porcentaje')

from django.core.exceptions import ValidationError

class ActividadAsignadaBaseFormSet(forms.BaseFormSet):
    def clean(self):
        import django.http
        from django.core.exceptions import ValidationError
        super().clean()
        # Solo valida si no es petición POST (para permitir solo el flash en admin)
        request = getattr(self, 'request', None)
        total = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                total += form.cleaned_data.get('porcentaje', 0)
        # Si el formset fue marcado para saltar la validación, no lanzar error
        if hasattr(self, '_skip_clean') and self._skip_clean:
            return
        if total != 100:
            raise ValidationError('La suma de los porcentajes de actividades debe ser 100%.')

ActividadAsignadaFormSet = formset_factory(ActividadAsignadaForm, formset=ActividadAsignadaBaseFormSet, extra=1, can_delete=True)

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
        # El guardado se realiza en el admin
        return instance
