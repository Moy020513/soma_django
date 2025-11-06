from django.contrib import admin, messages
from django import forms
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from django.contrib.admin.utils import unquote
from django.urls import reverse
from django.db import models as dj_models
from .models import Puesto, Empleado, PeriodoEstatusEmpleado, Contrato, AsignacionPorTrabajador
from .models import Inasistencia
from apps.asignaciones.models import Asignacion
from django.http import JsonResponse
# Admin Contrato
@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    # Asignacion importado a nivel de módulo

    # Formulario admin personalizado
    class ContratoForm(forms.ModelForm):
        class AsignacionNumeroMultipleField(forms.ModelMultipleChoiceField):
            def label_from_instance(self, obj):
                return str(obj.numero_cotizacion) if getattr(obj, 'numero_cotizacion', None) else '(sin cot)'

        asignaciones_vinculadas = AsignacionNumeroMultipleField(
            queryset=Asignacion.objects.all().order_by('-fecha'),
            required=False,
            widget=admin.widgets.FilteredSelectMultiple('Asignaciones', is_stacked=False),
            label='No. cotización'
        )

        class Meta:
            model = Contrato
            fields = '__all__'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Inicializar asignaciones con las ya vinculadas
            if self.instance and self.instance.pk:
                self.fields['asignaciones_vinculadas'].initial = self.instance.asignaciones_vinculadas.all()
            # Exponer la URL de información al widget para que el JS pueda consultarla
            try:
                info_url = reverse('admin:recursos_humanos_contrato_assignments_info')
                self.fields['asignaciones_vinculadas'].widget.attrs['data-assignments-info-url'] = info_url
            except Exception:
                pass

        def save(self, commit=True):
            # Guardado en dos pasos: primero el Contrato, luego relacionar asignaciones y computar campos
            contrato = super().save(commit=False)
            asigns = self.cleaned_data.get('asignaciones_vinculadas') or []
            # Si hay asignaciones, tomar la empresa de la primera (asumiendo mismo cliente)
            if asigns:
                contrato.empresa = asigns[0].empresa
                # Calcular periodo de ejecución: rango entre la fecha mínima y máxima de las asignaciones
                fechas = [a.fecha for a in asigns if a.fecha]
                if fechas:
                    fecha_min = min(fechas).strftime('%Y-%m-%d')
                    fecha_max = max(fechas).strftime('%Y-%m-%d')
                    contrato.periodo_ejecucion = f"{fecha_min} - {fecha_max}"
                # Calcular cantidad_empleados como suma de empleados por asignación
                total_emps = 0
                for a in asigns:
                    try:
                        total_emps += a.empleados.count()
                    except Exception:
                        pass
                contrato.cantidad_empleados = total_emps

            if commit:
                contrato.save()
                # Asignar ManyToMany
                if asigns:
                        contrato.asignaciones_vinculadas.set(asigns)
                else:
                        contrato.asignaciones_vinculadas.clear()
                self.save_m2m()
            return contrato

    form = ContratoForm
    class Media:
        js = ('/static/js/contrato_autofill.js',)
        css = {
            'all': ('/static/css/contrato_admin.css',)
        }
    list_display = ("numero_contrato", "empresa", "fecha_inicio", "fecha_termino", "periodo_ejecucion", "cantidad_empleados")
    list_filter = ("empresa", "fecha_inicio", "fecha_termino")
    search_fields = ("numero_contrato", "empresa__nombre")
    # autocomplete_fields = ["empresa"]

    readonly_fields = ('resumen_asignaciones',)

    fieldsets = (
        (None, {
            'fields': (('numero_contrato',), ('empresa', 'cantidad_empleados'), 'asignaciones_vinculadas')
        }),
        ('Periodo y fechas', {
            'fields': (('fecha_inicio', 'fecha_termino'), ('periodo_ejecucion', 'resumen_asignaciones'))
        }),
    )

    def resumen_asignaciones(self, obj):
        """Muestra un resumen (días estimados y total empleados) por asignación vinculada."""
        from django.utils.safestring import mark_safe
        if not obj or not obj.pk:
            return "Sin asignaciones vinculadas."
        parts = []
        for a in obj.asignaciones_vinculadas.all():
            dias = getattr(a, 'tiempo_estimado_total', None)
            if dias is None:
                try:
                    dias = a.actividades.aggregate(total=dj_models.Sum('tiempo_estimado_dias'))['total'] or 0
                except Exception:
                    dias = 'N/A'
            emp_count = a.empleados.count()
            num = a.numero_cotizacion or '(sin cot)'
            parts.append(f"<li><strong>{num}</strong>: {dias} días — {emp_count} empleados</li>")
        html = '<ul>' + ''.join(parts) + '</ul>'
        return mark_safe(html)

    resumen_asignaciones.short_description = 'Resumen de asignaciones'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('assignments-info/', self.admin_site.admin_view(self.assignments_info_view), name='recursos_humanos_contrato_assignments_info'),
        ]
        return custom + urls

    def assignments_info_view(self, request):
        """Devuelve JSON con empresa_id/nombre, total_emps y periodo (fecha_min - fecha_max) para los IDs enviados."""
        ids = request.GET.get('ids', '')
        if not ids:
            return JsonResponse({'ok': False, 'error': 'no ids'})
        try:
            pks = [int(x) for x in ids.split(',') if x.strip()]
        except Exception:
            return JsonResponse({'ok': False, 'error': 'invalid ids'})
        asigns = Asignacion.objects.filter(pk__in=pks).select_related('empresa')
        if not asigns.exists():
            return JsonResponse({'ok': True, 'empresa_id': None, 'empresa': '', 'total_emps': 0, 'periodo': ''})
        # Empresa: si todas comparten la misma empresa devolvemos el id, si no None
        empresa_ids = set(a.empresa_id for a in asigns)
        empresa_id = asigns[0].empresa_id if len(empresa_ids) == 1 else None
        empresa_name = asigns[0].empresa.nombre if empresa_id else ''
        # Total empleados
        total_emps = sum(a.empleados.count() for a in asigns)
        # Periodo
        fechas = [a.fecha for a in asigns if a.fecha]
        periodo = ''
        if fechas:
            fecha_min = min(fechas).strftime('%Y-%m-%d')
            fecha_max = max(fechas).strftime('%Y-%m-%d')
            periodo = f"{fecha_min} - {fecha_max}"
        return JsonResponse({'ok': True, 'empresa_id': empresa_id, 'empresa': empresa_name, 'total_emps': total_emps, 'periodo': periodo})

# Admin AsignacionPorTrabajador
@admin.register(AsignacionPorTrabajador)
class AsignacionPorTrabajadorAdmin(admin.ModelAdmin):
    list_display = ("contrato", "empleado")
    list_filter = ("contrato", "empleado")
    search_fields = ("contrato__numero_contrato", "empleado__numero_empleado", "empleado__usuario__first_name", "empleado__usuario__last_name")
    # autocomplete_fields = ["contrato", "empleado"]
from .forms_inasistencia import InasistenciaForm
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
        # Forzar inicialización correcta de fecha_inicio y fecha_fin si existen en la instancia
        if self.instance and self.instance.pk:
            if self.instance.fecha_inicio:
                self.initial['fecha_inicio'] = self.instance.fecha_inicio.strftime('%Y-%m-%d')
            if self.instance.fecha_fin:
                self.initial['fecha_fin'] = self.instance.fecha_fin.strftime('%Y-%m-%d')

@admin.register(PeriodoEstatusEmpleado)
class PeriodoEstatusEmpleadoAdmin(admin.ModelAdmin):
    form = PeriodoEstatusEmpleadoForm
    list_display = ('empleado', 'estatus', 'fecha_inicio', 'fecha_fin', 'observaciones')
    list_filter = ('estatus', 'fecha_inicio', 'fecha_fin')
    search_fields = ('empleado__numero_empleado', 'empleado__usuario__first_name', 'empleado__usuario__last_name', 'estatus')
    autocomplete_fields = ['empleado']

# Inline para periodos de estatus laboral
class UltimoPeriodoEstatusInline(admin.TabularInline):
    model = PeriodoEstatusEmpleado
    extra = 0
    fields = ('estatus', 'fecha_inicio', 'fecha_fin', 'observaciones')
    readonly_fields = ()
    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-fecha_inicio')[:1]  # Solo el último periodo

    def has_add_permission(self, request, obj=None):
        return False  # No permitir añadir desde el inline

@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'salario_minimo', 'salario_maximo', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    # list_editable removed: do not allow inline edits from changelist
    readonly_fields = ['fecha_creacion']

    def get_fields(self, request, obj=None):
        """Ocultar el campo 'superior' (Puesto supervisor) en los formularios de add y change.
        Si en el futuro se desea mostrar solo en edición, ajustar la condición sobre `obj`.
        """
        fields = list(super().get_fields(request, obj))
        # Eliminar 'superior' siempre (tanto en add como en change)
        if 'superior' in fields:
            fields.remove('superior')
        return fields


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
    # list_editable removed: do not allow inline edits from changelist
    inlines = [UltimoPeriodoEstatusInline]
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


@admin.register(Inasistencia)
class InasistenciaAdmin(admin.ModelAdmin):
    form = InasistenciaForm
    list_display = ('empleado', 'fecha', 'tipo', 'fecha_creacion')
    list_filter = ('tipo', 'fecha')
    search_fields = ('empleado__numero_empleado', 'empleado__usuario__first_name', 'empleado__usuario__last_name')


