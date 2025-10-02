from django import forms
from django.forms import formset_factory
from apps.recursos_humanos.models import Empleado
from .models import Asignacion, ActividadAsignada
class ActividadAsignadaForm(forms.Form):
    nombre = forms.CharField(max_length=120, label='Actividad')
    porcentaje = forms.IntegerField(min_value=1, max_value=100, label='Porcentaje')

from django.core.exceptions import ValidationError

class ActividadAsignadaBaseFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.actividades_completadas_porcentaje = kwargs.pop('actividades_completadas_porcentaje', 0)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        import django.http
        from django.core.exceptions import ValidationError
        super().clean()
        # Solo valida si no es petición POST (para permitir solo el flash en admin)
        request = getattr(self, 'request', None)
        total_pendientes = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                total_pendientes += form.cleaned_data.get('porcentaje', 0)
        
        # Sumar el porcentaje de actividades ya completadas
        total_general = total_pendientes + self.actividades_completadas_porcentaje
        
        # Si el formset fue marcado para saltar la validación, no lanzar error
        if hasattr(self, '_skip_clean') and self._skip_clean:
            return
        if total_general != 100:
            if self.actividades_completadas_porcentaje > 0:
                raise ValidationError(
                    f'La suma de los porcentajes debe ser 100%. '
                    f'Actividades completadas: {self.actividades_completadas_porcentaje}%, '
                    f'Actividades pendientes: {total_pendientes}%, '
                    f'Total actual: {total_general}%'
                )
            else:
                raise ValidationError('La suma de los porcentajes de actividades debe ser 100%.')

def ActividadAsignadaFormSetFactory(extra=1):
    return formset_factory(ActividadAsignadaForm, formset=ActividadAsignadaBaseFormSet, extra=extra, can_delete=True)

ActividadAsignadaFormSet = ActividadAsignadaFormSetFactory()

class EmpleadoAsignacionForm(forms.Form):
    empleado = forms.ModelChoiceField(
        queryset=Empleado.objects.filter(activo=True).order_by('numero_empleado'),
        label='Empleado',
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        supervisor_id = kwargs.pop('supervisor_id', None)
        super().__init__(*args, **kwargs)
        if supervisor_id:
            # Excluir el supervisor de la lista de empleados
            self.fields['empleado'].queryset = self.fields['empleado'].queryset.exclude(id=supervisor_id)

class EmpleadoAsignacionBaseFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.form_kwargs = kwargs.pop('form_kwargs', {})
        super().__init__(*args, **kwargs)
    
    def _construct_form(self, i, **kwargs):
        kwargs.update(self.form_kwargs)
        return super()._construct_form(i, **kwargs)

def EmpleadoAsignacionFormSetFactory(extra=1):
    return formset_factory(EmpleadoAsignacionForm, formset=EmpleadoAsignacionBaseFormSet, extra=extra, can_delete=True)

EmpleadoAsignacionFormSet = EmpleadoAsignacionFormSetFactory()

class AsignacionCustomForm(forms.ModelForm):
    class Meta:
        model = Asignacion
        exclude = ['empleados']


    archivos = forms.FileField(required=False, label='Archivos adjuntos')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empresa'].queryset = self.fields['empresa'].queryset.filter(activa=True)
        self.fields['supervisor'].queryset = self.fields['supervisor'].queryset.filter(activo=True)
        # Configura el widget para mostrar el calendario nativo del navegador
        self.fields['fecha'].widget = forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
        # Inicializa la fecha en formato HTML5 si estamos editando y no hay datos POST
        if self.instance.pk and self.instance.fecha and not self.data:
            self.fields['fecha'].initial = self.instance.fecha.strftime('%Y-%m-%d')

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Asegura que la fecha de asignación se mantenga al editar
        if self.instance.pk and 'fecha' in self.cleaned_data:
            instance.fecha = self.cleaned_data['fecha']
        return instance
