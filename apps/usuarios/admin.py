from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Usuario, Rol

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'tipo_usuario', 'estado_display', 'staff_display')
    list_filter = ('tipo_usuario', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Información SOMA', {'fields': ('tipo_usuario', 'rol', 'telefono')}),
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
        return format_html('<span class="badge badge-secondary">No</span>')
    staff_display.short_description = 'Staff'
    staff_display.admin_order_field = 'is_staff'

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)