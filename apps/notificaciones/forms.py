from django import forms
from .models import Notificacion, RespuestaNotificacion


class NotificacionForm(forms.ModelForm):
    class Meta:
        model = Notificacion
        # Solo mostrar estos campos en el formulario
        fields = ['usuario', 'titulo', 'mensaje', 'tipo']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Título'}),
            'mensaje': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3, 'placeholder': 'Mensaje'}),
            'tipo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }


class RespuestaNotificacionForm(forms.ModelForm):
    class Meta:
        model = RespuestaNotificacion
        fields = ['mensaje', 'documento']
        widgets = {
            'mensaje': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Escribe tu respuesta breve...'}),
        }
