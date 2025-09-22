from django.contrib import admin
from .models import Puesto, Empleado, TipoContrato, Contrato


@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'salario_minimo', 'salario_maximo', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']
    readonly_fields = ['fecha_creacion']


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ['numero_empleado', 'nombre_completo', 'departamento', 'puesto', 'fecha_ingreso', 'activo']
    list_filter = ['departamento__sucursal__empresa', 'departamento', 'puesto', 'activo', 'fecha_ingreso']
    search_fields = ['numero_empleado', 'usuario__first_name', 'usuario__last_name', 'curp', 'rfc']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    list_editable = ['activo']
    
    fieldsets = (
        ('Información del Usuario', {
            'fields': ('usuario', 'numero_empleado', 'foto')
        }),
        ('Documentos Oficiales', {
            'fields': ('curp', 'rfc', 'nss')
        }),
        ('Información Personal', {
            'fields': ('fecha_nacimiento', 'estado_civil', 'tipo_sangre')
        }),
        ('Contacto', {
            'fields': ('telefono_personal', 'direccion', 'telefono_emergencia', 'contacto_emergencia')
        }),
        ('Información Laboral', {
            'fields': ('departamento', 'puesto', 'jefe_directo', 'salario_actual')
        }),
        ('Fechas Laborales', {
            'fields': ('fecha_ingreso', 'fecha_baja', 'motivo_baja')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas del Sistema', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def nombre_completo(self, obj):
        return obj.usuario.get_full_name()
    nombre_completo.short_description = 'Nombre completo'
    nombre_completo.admin_order_field = 'usuario__first_name'


@admin.register(TipoContrato)
class TipoContratoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ['empleado', 'tipo_contrato', 'fecha_inicio', 'fecha_fin', 'salario', 'activo']
    list_filter = ['tipo_contrato', 'activo', 'fecha_inicio']
    search_fields = ['empleado__numero_empleado', 'empleado__usuario__first_name', 'empleado__usuario__last_name']
    readonly_fields = ['fecha_creacion']
    list_editable = ['activo']
    date_hierarchy = 'fecha_inicio'