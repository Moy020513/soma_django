from django.contrib import admin
from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Contacto

class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidos', 'fecha_nacimiento')
    search_fields = ('nombre', 'apellidos')
    list_filter = ('fecha_nacimiento',)

"""
Este módulo no registra modelos propios en el admin.
Los cumpleaños se gestionan desde los admins de empleados y contactos.
"""
