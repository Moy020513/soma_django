from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Empleado, Puesto
import re

Usuario = get_user_model()


class EmpleadoRegistroForm(forms.Form):
    # Personales
    nombre = forms.CharField(max_length=30, label='Nombre', required=True)
    apellido_paterno = forms.CharField(max_length=30, label='Apellido paterno', required=True)
    apellido_materno = forms.CharField(max_length=30, label='Apellido materno', required=False)
    telefono = forms.CharField(max_length=10, label='Teléfono', required=True)
    nss = forms.CharField(max_length=20, label='NSS', required=False)
    curp = forms.CharField(max_length=18, label='CURP', required=True)
    rfc = forms.CharField(max_length=13, label='RFC', required=False)
    fecha_nacimiento = forms.DateField(label='Fecha de nacimiento', required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    sexo = forms.ChoiceField(choices=[('M','Masculino'), ('F','Femenino'), ('I','Indefinido')], required=True, label='Sexo')

    # Laborales
    fecha_ingreso = forms.DateField(label='Fecha de ingreso', required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    puesto = forms.ModelChoiceField(queryset=Puesto.objects.filter(activo=True), required=True, label='Puesto')
    # Eliminado campo de supervisor en registro de empleado

    def clean_telefono(self):
        tel = self.cleaned_data['telefono']
        if not re.fullmatch(r"\d{10}", tel):
            raise ValidationError('El teléfono debe tener exactamente 10 dígitos numéricos.')
        # Unicidad en Usuario.telefono
        if Usuario.objects.filter(telefono=tel).exists():
            raise ValidationError('El teléfono ya está registrado en otro usuario.')
        # Unicidad en Empleado.telefono_personal
        if Empleado.objects.filter(telefono_personal=tel).exists():
            raise ValidationError('El teléfono ya está asignado a otro empleado.')
        return tel

    def clean_curp(self):
        curp = self.cleaned_data['curp'].upper()
        if len(curp) != 18:
            raise ValidationError('La CURP debe tener 18 caracteres.')
        if Empleado.objects.filter(curp=curp).exists():
            raise ValidationError('La CURP ya está registrada.')
        return curp

    def _suggest_username(self, nombre: str, ap_pat: str, ap_mat: str) -> str:
        base = (nombre.split()[0] + (ap_pat[:1] if ap_pat else '') + (ap_mat[:1] if ap_mat else '')).upper()
        return base

    def _unique_username(self, base: str) -> str:
        """Devuelve un username único. Si base existe, añade sufijos numéricos base1, base2, ..."""
        if not Usuario.objects.filter(username=base).exists():
            return base
        # Buscar sufijos existentes
        pattern = re.compile(rf'^{re.escape(base)}(\d+)$')
        max_suffix = 0
        for u in Usuario.objects.filter(username__startswith=base).values_list('username', flat=True):
            m = pattern.match(u)
            if m:
                try:
                    s = int(m.group(1))
                    if s > max_suffix:
                        max_suffix = s
                except ValueError:
                    continue
        return f"{base}{max_suffix + 1}"

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        nombre = cleaned.get('nombre', '').strip()
        ap_pat = cleaned.get('apellido_paterno', '').strip()
        ap_mat = cleaned.get('apellido_materno', '').strip()
        base = self._suggest_username(nombre, ap_pat, ap_mat)
        username = self._unique_username(base)
        cleaned['username_sugerido'] = username
        cleaned['password_generada'] = cleaned['curp'][:8]
        return cleaned
