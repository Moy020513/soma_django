from django.contrib import admin, messages
from django import forms
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from django.contrib.admin.utils import unquote
from django.urls import reverse
from .models import Puesto, Empleado, PeriodoEstatusEmpleado
# Admin para estatus de empleado

# Formulario personalizado para PeriodoEstatusEmpleado
class PeriodoEstatusEmpleadoForm(forms.ModelForm):
    class Meta:
        model = PeriodoEstatusEmpleado
        fields = '__all__'
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control form-control-sm').strip()
            style = field.widget.attrs.get('style', '')
            compact_style = 'max-width: 400px; padding: .25rem .5rem; font-size: .875rem;'
            field.widget.attrs['style'] = (style + ' ' + compact_style).strip()
        # Forzar inicialización correcta de fecha_inicio si existe instancia
        if self.instance and self.instance.pk and self.instance.fecha_inicio:
            self.initial['fecha_inicio'] = self.instance.fecha_inicio.strftime('%Y-%m-%d')

@admin.register(PeriodoEstatusEmpleado)
class PeriodoEstatusEmpleadoAdmin(admin.ModelAdmin):
    form = PeriodoEstatusEmpleadoForm
    list_display = ('empleado', 'estatus', 'fecha_inicio', 'fecha_fin', 'observaciones')
    list_filter = ('estatus', 'fecha_inicio', 'fecha_fin')
    search_fields = ('empleado__numero_empleado', 'empleado__usuario__first_name', 'empleado__usuario__last_name', 'estatus')
    autocomplete_fields = ['empleado']

# Inline para periodos de estatus laboral
class PeriodoEstatusEmpleadoInline(admin.TabularInline):
    model = PeriodoEstatusEmpleado
    extra = 1
    fields = ('estatus', 'fecha_inicio', 'fecha_fin', 'observaciones')
    readonly_fields = ()
    show_change_link = True
from apps.asignaciones.models import Asignacion


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
    list_display = ['numero_empleado', 'nombre_completo', 'fecha_nacimiento', 'puesto', 'fecha_ingreso', 'activo']
    list_filter = ['puesto', 'activo', 'fecha_ingreso', 'fecha_nacimiento']
    search_fields = ['numero_empleado', 'usuario__first_name', 'usuario__last_name', 'curp', 'rfc']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    list_editable = ['activo']
    inlines = [PeriodoEstatusEmpleadoInline]
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
            'fields': (('puesto',), ('jefe_directo', 'salario_actual')),
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

    # Inline de asignaciones eliminado porque la relación ahora es ManyToMany

    def has_add_permission(self, request):
        # Deshabilitar el alta estándar en admin para usar el nuevo flujo
        return False

    def add_view(self, request, form_url='', extra_context=None):
        # Redirigir siempre al nuevo flujo de registro de empleados
        return redirect('rh:registrar_empleado')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Redirigir al formulario personalizado de edición
        return redirect(reverse('rh:editar_empleado', args=[object_id]))

    def get_model_perms(self, request):
        # Ocultar el enlace "Añadir" también en el índice de la app del admin
        perms = super().get_model_perms(request)
        perms['add'] = False
        return perms
    
    def nombre_completo(self, obj):
        return obj.usuario.get_full_name()
    nombre_completo.short_description = 'Nombre completo'
    nombre_completo.admin_order_field = 'usuario__first_name'

    def delete_view(self, request, object_id, extra_context=None):
        """Vista de borrado personalizada que evita construir URLs con reverse
        que están causando NoReverseMatch en la plantilla de confirmación.
        """
        opts = self.model._meta
        obj = self.get_object(request, unquote(object_id))
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            # Si no existe, volver al changelist
            return redirect(f"admin:{opts.app_label}_{opts.model_name}_changelist")

        if request.method == "POST":
            # Eliminar y redirigir al changelist
            self.log_deletion(request, obj, str(obj))
            obj_display = str(obj)
            obj.delete()
            messages.success(request, _(f'Se eliminó "{obj_display}" correctamente.'))
            return redirect(f"admin:{opts.app_label}_{opts.model_name}_changelist")

        context = {
            **self.admin_site.each_context(request),
            "title": _("Are you sure?"),
            "object_id": object_id,
            "original": obj,
            "object": obj,  # por compatibilidad con plantilla
            "opts": opts,
            "app_label": opts.app_label,
            # Evitar cálculos de relaciones que puedan intentar hacer reverse
            "deleted_objects": [],
            "perms_lacking": [],
            "protected": [],
        }
        if extra_context:
            context.update(extra_context)
        return TemplateResponse(request, "admin/delete_confirmation.html", context)


