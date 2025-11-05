from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import Usuario
from .forms import UsuarioCreationForm, UsuarioChangeForm

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'tipo_usuario', 'estado_display', 'staff_display')
    list_filter = ('tipo_usuario', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    # Remove 'rol' from the admin form fields so it's not editable from the admin user form
    fieldsets = UserAdmin.fieldsets + (
        ('Información SOMA', {'fields': ('tipo_usuario', 'telefono')}),
    )

    def get_list_display(self, request):
        return ['username', 'email', 'first_name', 'last_name', 'tipo_usuario', 'estado_display', 'staff_display']

    def username(self, obj):
        return obj.username
    username.short_description = 'Usuario'

    def email(self, obj):
        return obj.email
    email.short_description = 'Email'

    def first_name(self, obj):
        return obj.first_name
    first_name.short_description = 'Nombre'

    def last_name(self, obj):
        return obj.last_name
    last_name.short_description = 'Apellido'

    def tipo_usuario(self, obj):
        return obj.get_tipo_usuario_display()
    tipo_usuario.short_description = 'Tipo'

    def estado_display(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">Activo</span>')
        return format_html('<span class="badge badge-danger">Inactivo</span>')
    estado_display.short_description = 'Estado'
    estado_display.admin_order_field = 'is_active'

    def staff_display(self, obj):
        if obj.is_staff:
            return format_html('<span class="badge badge-info">Sí</span>')
        return format_html('<span class="badge badge-danger">No</span>')
    staff_display.short_description = 'Staff'
    staff_display.admin_order_field = 'is_staff'

    # Use the admin's filter_horizontal widget for better multi-select UX
    filter_horizontal = ('groups', 'user_permissions')

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Adjust widget attributes for groups and permissions to increase visible height.

        We avoid replacing the widget so the admin JS behavior remains intact; instead
        we call super() and update attrs on the returned field.widget.
        """
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name in ('groups', 'user_permissions') and field is not None:
            try:
                field.widget.attrs.update({'style': 'min-height:180px; max-height:320px;'})
            except Exception:
                pass
        return field

# El modelo Rol ya no se registra en el admin para ocultarlo del módulo "Usuarios".