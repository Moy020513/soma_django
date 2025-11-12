from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Empleado, Puesto
import re

Usuario = get_user_model()

class EmpleadoEdicionForm(forms.Form):
    usuario = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(is_active=True).order_by('username'),
        label='Usuario',
        required=True,
        help_text='Usuario vinculado al empleado.'
    )
    nombre = forms.CharField(max_length=30, label='Nombre', required=True)
    apellido_paterno = forms.CharField(max_length=30, label='Apellido paterno', required=True)
    apellido_materno = forms.CharField(max_length=30, label='Apellido materno', required=False)
    telefono = forms.CharField(max_length=10, label='Teléfono', required=True)
    nss = forms.CharField(max_length=20, label='NSS', required=False)
    curp = forms.CharField(max_length=18, label='CURP', required=True)
    rfc = forms.CharField(max_length=13, label='RFC', required=False)
    fecha_nacimiento = forms.DateField(label='Fecha de nacimiento', required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    sexo = forms.ChoiceField(choices=[('M','Masculino'), ('F','Femenino'), ('I','Indefinido')], required=True, label='Sexo')
    fecha_ingreso = forms.DateField(label='Fecha de ingreso', required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    puesto = forms.ModelChoiceField(queryset=Puesto.objects.filter(activo=True), required=True, label='Puesto')
    salario_inicial = forms.DecimalField(label='Salario inicial', required=False, max_digits=10, decimal_places=2, min_value=0)
    salario_actual = forms.DecimalField(label='Salario actual', required=False, max_digits=10, decimal_places=2, min_value=0)

    def clean_telefono(self):
        tel = self.cleaned_data['telefono']
        if not re.fullmatch(r"\d{10}", tel):
            raise ValidationError('El teléfono debe tener exactamente 10 dígitos numéricos.')
        usuario_sel = self.cleaned_data.get('usuario')
        qs_usuarios = Usuario.objects.filter(telefono=tel)
        if usuario_sel:
            qs_usuarios = qs_usuarios.exclude(pk=usuario_sel.pk)
        if qs_usuarios.exists():
            raise ValidationError('El teléfono ya está registrado en otro usuario.')
        if Empleado.objects.filter(telefono_personal=tel).exclude(usuario=usuario_sel).exists():
            raise ValidationError('El teléfono ya está asignado a otro empleado.')
        return tel

    def clean_curp(self):
        curp = self.cleaned_data['curp'].upper()
        if len(curp) != 18:
            raise ValidationError('La CURP debe tener 18 caracteres.')
        if Empleado.objects.filter(curp=curp).exclude(usuario=self.cleaned_data.get('usuario')).exists():
            raise ValidationError('La CURP ya está registrada.')
        return curp

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        usuario_sel = cleaned.get('usuario')
        if not usuario_sel:
            raise ValidationError('Debes seleccionar un usuario existente.')
        return cleaned
