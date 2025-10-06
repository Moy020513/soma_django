from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    """
    Formulario personalizado que valida que el email exista en la base de datos
    """
    
    email = forms.EmailField(
        label="Correo electrónico",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@empresa.com',
            'autocomplete': 'email'
        })
    )
    
    def clean_email(self):
        """
        Validar que el email ingresado esté asociado a un usuario existente
        """
        email = self.cleaned_data.get('email')
        
        if email:
            # Buscar usuarios con este email
            users = User.objects.filter(email__iexact=email, is_active=True)
            
            if not users.exists():
                raise ValidationError(
                    "❌ Este correo electrónico no está asociado con ninguna cuenta de usuario. "
                    "Verifica que hayas ingresado correctamente tu email o contacta al administrador."
                )
        
        return email
    
    def get_users(self, email):
        """
        Obtener usuarios activos con el email dado
        """
        active_users = User.objects.filter(
            email__iexact=email, 
            is_active=True
        )
        return (u for u in active_users if u.has_usable_password())