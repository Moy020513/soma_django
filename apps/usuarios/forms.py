from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Permission
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import Usuario


class PermissionModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """ModelMultipleChoiceField que muestra las etiquetas de permisos en español.

    Ejemplo de etiqueta resultante: "ubicaciones | Registro de Ubicación | Puede eliminar Registro de Ubicación"
    """
    def label_from_instance(self, obj):
        # Obtener nombre legible del modelo
        try:
            model_class = obj.content_type.model_class()
            model_verbose = getattr(model_class._meta, 'verbose_name', obj.content_type.model)
        except Exception:
            model_verbose = obj.content_type.model

        # Mapear acción por el codename (add/change/delete/view)
        codename = obj.codename or ''
        if codename.startswith('add_'):
            action = 'Puede agregar'
        elif codename.startswith('change_'):
            action = 'Puede cambiar'
        elif codename.startswith('delete_'):
            action = 'Puede eliminar'
        elif codename.startswith('view_'):
            action = 'Puede ver'
        else:
            # Fallback: usar el nombre ya existente pero traducir "Can" si aparece
            name = obj.name
            name = name.replace('Can ', 'Puede ')
            return f"{obj.content_type.app_label} | {model_verbose} | {name}"

        return f"{obj.content_type.app_label} | {model_verbose} | {action} {model_verbose}"

class UsuarioCreationForm(UserCreationForm):
    class Meta:
        model = Usuario
        # incluir campos de permisos para permitir su selección desde el admin
        fields = (
            'username', 'email', 'first_name', 'last_name', 'tipo_usuario',
            'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que user_permissions use el widget del admin para que filter_horizontal funcione
        if 'user_permissions' in self.fields:
            widget = FilteredSelectMultiple('User permissions', is_stacked=False)
            widget.attrs.update({'style': 'min-height:180px; max-height:320px;'})
            self.fields['user_permissions'] = PermissionModelMultipleChoiceField(
                queryset=Permission.objects.select_related('content_type').all(),
                required=False,
                widget=widget,
            )

class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        # incluir campos de permisos y flags para administrarlos desde el admin
        fields = (
            'username', 'email', 'first_name', 'last_name', 'tipo_usuario',
            'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Reemplazar el campo user_permissions por nuestra versión que genera etiquetas en español
        if 'user_permissions' in self.fields:
            widget = FilteredSelectMultiple('User permissions', is_stacked=False)
            widget.attrs.update({'style': 'min-height:180px; max-height:320px;'})
            self.fields['user_permissions'] = PermissionModelMultipleChoiceField(
                queryset=Permission.objects.select_related('content_type').all(),
                required=False,
                widget=widget,
            )

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))