from django.contrib import admin
from .models import Empresa, Sucursal, Departamento


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'razon_social', 'rfc', 'telefono', 'activa', 'fecha_creacion']
    list_filter = ['activa', 'fecha_creacion']
    search_fields = ['nombre', 'razon_social', 'rfc']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    list_editable = ['activa']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'razon_social', 'rfc')
        }),
        ('Contacto', {
            'fields': ('direccion', 'telefono', 'email', 'sitio_web')
        }),
        ('Imagen', {
            'fields': ('logo',),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('activa',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'empresa', 'codigo', 'gerente', 'activa', 'fecha_apertura']
    list_filter = ['empresa', 'activa', 'fecha_apertura']
    search_fields = ['nombre', 'codigo', 'empresa__nombre', 'gerente']
    readonly_fields = ['fecha_creacion']
    list_editable = ['activa']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'nombre', 'codigo')
        }),
        ('Contacto', {
            'fields': ('direccion', 'telefono', 'email')
        }),
        ('Administración', {
            'fields': ('gerente', 'fecha_apertura')
        }),
        ('Estado', {
            'fields': ('activa',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'sucursal', 'empresa', 'codigo', 'jefe_departamento', 'activo']
    list_filter = ['sucursal__empresa', 'sucursal', 'activo']
    search_fields = ['nombre', 'codigo', 'sucursal__nombre', 'jefe_departamento']
    readonly_fields = ['fecha_creacion']
    list_editable = ['activo']
    
    def empresa(self, obj):
        return obj.sucursal.empresa.nombre
    empresa.short_description = 'Empresa'
    empresa.admin_order_field = 'sucursal__empresa__nombre'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('sucursal', 'nombre', 'codigo')
        }),
        ('Descripción', {
            'fields': ('descripcion',)
        }),
        ('Administración', {
            'fields': ('jefe_departamento', 'presupuesto_anual')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )