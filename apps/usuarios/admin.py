from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Rol

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'tipo_usuario', 'is_active')
    list_filter = ('tipo_usuario', 'is_active', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Información SOMA', {'fields': ('tipo_usuario', 'rol', 'telefono')}),
    )

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)