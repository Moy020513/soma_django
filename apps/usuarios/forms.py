from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Usuario

class UsuarioCreationForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'first_name', 'last_name', 'tipo_usuario')

class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'first_name', 'last_name', 'tipo_usuario')

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))