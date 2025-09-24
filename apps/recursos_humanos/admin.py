from django.contrib import admin
from django import forms
from django.shortcuts import redirect
from .models import Puesto, Empleado, TipoContrato, Contrato


@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'salario_minimo', 'salario_maximo', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']
    readonly_fields = ['fecha_creacion']


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = '__all__'
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'fecha_baja': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Compactar inputs
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control form-control-sm').strip()
            # Hacer los campos más compactos visualmente
            style = field.widget.attrs.get('style', '')
            compact_style = 'max-width: 600px; padding: .25rem .5rem; font-size: .875rem;'
            field.widget.attrs['style'] = (style + ' ' + compact_style).strip()
        # Hacer numero_empleado de solo lectura si ya existe (se genera automático)
        if self.instance and self.instance.pk:
            self.fields['numero_empleado'].widget.attrs['readonly'] = True
        # No requerir numero_empleado en alta: se generará automáticamente
        if 'numero_empleado' in self.fields:
            self.fields['numero_empleado'].required = False
            self.fields['numero_empleado'].help_text = 'Si lo dejas vacío, se generará automáticamente.'


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    form = EmpleadoForm
    save_on_top = True
    list_display = ['numero_empleado', 'nombre_completo', 'departamento', 'puesto', 'fecha_ingreso', 'activo']
    list_filter = ['departamento__sucursal__empresa', 'departamento', 'puesto', 'activo', 'fecha_ingreso']
    search_fields = ['numero_empleado', 'usuario__first_name', 'usuario__last_name', 'curp', 'rfc']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    list_editable = ['activo']
    
    fieldsets = (
        ('Información del Usuario', {
            'fields': (
                ('usuario', 'numero_empleado'),
                ('foto',),
            ),
            'classes': ('',),
        }),
        ('Documentos Oficiales', {
            'fields': (('curp', 'rfc'), ('nss',)),
        }),
        ('Información Personal', {
            'fields': (('fecha_nacimiento', 'estado_civil', 'tipo_sangre', 'sexo'),),
        }),
        ('Contacto', {
            'fields': (('telefono_personal', 'telefono_emergencia'), ('contacto_emergencia',), ('direccion',)),
        }),
        ('Información Laboral', {
            'fields': (('departamento', 'puesto'), ('jefe_directo', 'salario_actual')),
        }),
        ('Fechas Laborales', {
            'fields': (('fecha_ingreso', 'fecha_baja'), ('motivo_baja',)),
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Fechas del Sistema', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )

    class Media:
        css = {
            'all': (
                # Compactar controles en admin
                'admin/css/forms.css',
            )
        }

    change_list_template = 'admin/recursos_humanos/empleado/change_list.html'

    def has_add_permission(self, request):
        # Deshabilitar el alta estándar en admin para usar el nuevo flujo
        return False

    def add_view(self, request, form_url='', extra_context=None):
        # Redirigir siempre al nuevo flujo de registro de empleados
        return redirect('rh:registrar_empleado')

    def get_model_perms(self, request):
        # Ocultar el enlace "Añadir" también en el índice de la app del admin
        perms = super().get_model_perms(request)
        perms['add'] = False
        return perms
    
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