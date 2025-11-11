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
from django.utils.html import format_html
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
                # Fecha de inicio = mínima fecha de asignación
                fechas = [a.fecha for a in asigns if a.fecha]
                if fechas:
                    contrato.fecha_inicio = min(fechas)
                # Fecha término = máxima fecha_termino de las asignaciones (si existe),
                # si no, fallback a la máxima fecha de asignación
                terminos = [a.fecha_termino for a in asigns if getattr(a, 'fecha_termino', None)]
                if terminos:
                    contrato.fecha_termino = max(terminos)
                else:
                    if fechas:
                        contrato.fecha_termino = max(fechas)
                # Calcular cantidad_empleados como suma de empleados por asignación
                total_emps = 0
                for a in asigns:
                    try:
                        total_emps += a.empleados.count()
                    except Exception:
                        pass
                contrato.cantidad_empleados = total_emps
                # Calcular días activos como la suma de días_trabajados por asignación
                total_dias = 0
                for a in asigns:
                    try:
                        total_dias += a.dias_trabajados.count()
                    except Exception:
                        pass
                contrato.dias_activos = total_dias

            if commit:
                contrato.save()
                # Asignar ManyToMany
                if asigns:
                        contrato.asignaciones_vinculadas.set(asigns)
                else:
                        contrato.asignaciones_vinculadas.clear()
                self.save_m2m()
                # Crear/actualizar AsignacionPorTrabajador para cada empleado encontrado en las asignaciones
                try:
                    # Mapear empleado -> lista de asignaciones relacionadas en este contrato
                    emp_map = {}
                    for a in asigns:
                        for emp in a.empleados.all():
                            emp_map.setdefault(emp.pk, {'empleado': emp, 'fechas_inicio': [], 'fechas_termino': []})
                            if getattr(a, 'fecha', None):
                                emp_map[emp.pk]['fechas_inicio'].append(a.fecha)
                            if getattr(a, 'fecha_termino', None):
                                emp_map[emp.pk]['fechas_termino'].append(a.fecha_termino)
                    from .models import AsignacionPorTrabajador
                    existing_qs = AsignacionPorTrabajador.objects.filter(contrato=contrato)
                    existing_map = {ap.empleado_id: ap for ap in existing_qs}
                    # Actualizar o crear
                    for emp_pk, info in emp_map.items():
                        empleado = info['empleado']
                        fecha_inicio = min(info['fechas_inicio']) if info['fechas_inicio'] else None
                        fecha_termino = max(info['fechas_termino']) if info['fechas_termino'] else None
                        defaults = {
                            'empresa': contrato.empresa,
                            'fecha_inicio': fecha_inicio,
                            'fecha_termino': fecha_termino,
                            'nss': getattr(empleado, 'nss', '') or ''
                        }
                        AsignacionPorTrabajador.objects.update_or_create(contrato=contrato, empleado=empleado, defaults=defaults)
                    # Borrar registros que ya no correspondan
                    to_delete = [ap.pk for eid, ap in existing_map.items() if eid not in emp_map]
                    if to_delete:
                        AsignacionPorTrabajador.objects.filter(pk__in=to_delete).delete()
                except Exception:
                    # no bloquear el guardado de contrato por errores en la creación automática
                    pass
            return contrato

    form = ContratoForm
    class Media:
        js = ('js/contrato_autofill.js',)
        css = {
            'all': ('/static/css/contrato_admin.css',)
        }
    list_display = ("numero_contrato", "empresa", "fecha_inicio", "fecha_termino", "cantidad_empleados", 'dias_activos')
    list_filter = ("empresa", "fecha_inicio", "fecha_termino")
    search_fields = ("numero_contrato", "empresa__nombre")
    # autocomplete_fields = ["empresa"]

    readonly_fields = ('resumen_asignaciones',)

    fieldsets = (
        (None, {
            'fields': (('numero_contrato',), ('empresa', 'cantidad_empleados', 'dias_activos'), 'asignaciones_vinculadas')
        }),
        ('Periodo y fechas', {
            'fields': (('fecha_inicio', 'fecha_termino'), ('resumen_asignaciones',))
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
        empresa_id = request.GET.get('empresa_id')

        # Si se solicita por empresa_id, devolver lista de asignaciones (pk y numero_cotizacion)
        if empresa_id:
            try:
                eid = int(empresa_id)
            except Exception:
                return JsonResponse({'ok': False, 'error': 'invalid empresa_id'})
            asigns_qs = Asignacion.objects.filter(empresa_id=eid).order_by('-fecha')
            data = []
            for a in asigns_qs:
                data.append({
                    'pk': a.pk,
                    'numero_cotizacion': a.numero_cotizacion,
                    'fecha': a.fecha.strftime('%Y-%m-%d') if getattr(a, 'fecha', None) else None,
                    'completada': bool(getattr(a, 'completada', False)),
                    'fecha_termino': a.fecha_termino.strftime('%Y-%m-%d') if getattr(a, 'fecha_termino', None) else None,
                    'empresa_id': getattr(a, 'empresa_id', None),
                    'empresa_nombre': getattr(a.empresa, 'nombre', '') if getattr(a, 'empresa', None) else '',
                    'empleados': a.empleados.count() if hasattr(a, 'empleados') else 0,
                    'dias_activos': a.dias_trabajados.count() if hasattr(a, 'dias_trabajados') else 0,
                })
            return JsonResponse({'ok': True, 'assignments': data})

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
        # Total dias activos
        total_dias = sum(a.dias_trabajados.count() for a in asigns)
        # Periodo
        fechas = [a.fecha for a in asigns if a.fecha]
        fecha_min = None
        fecha_termino_max = None
        if fechas:
            fecha_min = min(fechas).strftime('%Y-%m-%d')
        # Fecha término: máximo entre las fechas_termino de las asignaciones si existen
        terminos = [a.fecha_termino for a in asigns if getattr(a, 'fecha_termino', None)]
        if terminos:
            fecha_termino_max = max(terminos).strftime('%Y-%m-%d')
        else:
            # fallback: si no hay fecha_termino, considerar asignaciones completadas por fecha
            fechas_completadas = [a.fecha for a in asigns if getattr(a, 'completada', False) and a.fecha]
            if fechas_completadas:
                fecha_termino_max = max(fechas_completadas).strftime('%Y-%m-%d')
        return JsonResponse({'ok': True, 'empresa_id': empresa_id, 'empresa': empresa_name, 'total_emps': total_emps, 'total_dias': total_dias, 'fecha_inicio': fecha_min, 'fecha_termino': fecha_termino_max})

# Admin AsignacionPorTrabajador
@admin.register(AsignacionPorTrabajador)
class AsignacionPorTrabajadorAdmin(admin.ModelAdmin):
    change_list_template = 'admin/recursos_humanos/asignacionportrabajador/change_list.html'
    list_display = ("contrato_numero", "empresa", "empleado", "periodo", "nss")
    list_filter = ("empresa", "contrato", "empleado")
    search_fields = ("contrato__numero_contrato", "empleado__numero_empleado", "empleado__usuario__first_name", "empleado__usuario__last_name")
    class Media:
        css = {
            'all': ('/static/css/contrato_admin.css',)
        }

    def periodo(self, obj):
        """Mostrar periodo como 'dd/mm/YYYY — dd/mm/YYYY' o fecha de inicio si falta término."""
        def fmt(d):
            try:
                return d.strftime('%d/%m/%Y') if d else ''
            except Exception:
                return str(d) if d else ''

        if obj.fecha_inicio and obj.fecha_termino:
            return f"{fmt(obj.fecha_inicio)} — {fmt(obj.fecha_termino)}"
        if obj.fecha_inicio:
            return fmt(obj.fecha_inicio)
        return ''

    periodo.short_description = 'Periodo'
    
    from django.utils.html import format_html

    def contrato_numero(self, obj):
        """Mostrar únicamente el número de contrato (evita usar __str__ del Contrato)."""
        try:
            val = obj.contrato.numero_contrato if obj.contrato else ''
            return format_html('<div style="text-align:center;">{}</div>', val)
        except Exception:
            return ''

    contrato_numero.short_description = 'No. contrato'
    contrato_numero.admin_order_field = 'contrato__numero_contrato'

    def empresa_display(self, obj):
        try:
            return format_html('<div style="text-align:center;">{}</div>', obj.empresa.nombre if obj.empresa else '')
        except Exception:
            return ''
    empresa_display.short_description = 'Empresa'
    empresa_display.admin_order_field = 'empresa__nombre'

    # Ajustar list_display para usar empresa_display
    list_display = ("contrato_numero", "empresa_display", "empleado", "periodo", "nss")
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


