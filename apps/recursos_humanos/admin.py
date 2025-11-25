from django.contrib import admin, messages
from django import forms
from django.forms.widgets import DateTimeInput
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.utils.translation import gettext as _
from django.contrib.admin.utils import unquote
from django.urls import reverse
from django.db import models as dj_models
from django.db import transaction
from .models import Puesto, Empleado, PeriodoEstatusEmpleado, Contrato, AsignacionPorTrabajador, CambioSalarioEmpleado
from django.utils.html import format_html
from django.utils import timezone
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
                # Calcular cantidad_empleados como el número de empleados únicos en
                # todas las asignaciones seleccionadas, incluyendo al supervisor si existe
                try:
                    empleados_set = set()
                    for a in asigns:
                        try:
                            # añadir empleados M2M
                            for e in a.empleados.all():
                                if getattr(e, 'pk', None):
                                    empleados_set.add(e.pk)
                        except Exception:
                            pass
                        # añadir supervisor si existe y no está ya en el set
                        try:
                            sup = getattr(a, 'supervisor', None)
                            if sup and getattr(sup, 'pk', None):
                                empleados_set.add(sup.pk)
                        except Exception:
                            pass
                    contrato.cantidad_empleados = len(empleados_set)
                except Exception:
                    # fallback conservador: mantener valor previo o contar como 0
                    try:
                        contrato.cantidad_empleados = contrato.cantidad_empleados or 0
                    except Exception:
                        contrato.cantidad_empleados = 0
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
    list_display = ("numero_contrato", "empresa", 'fecha_inicio_display', 'fecha_termino_display', "cantidad_empleados", 'dias_activos', 'numeros_cotizacion', 'empleados_en_contrato')
    list_filter = ("empresa", "fecha_inicio", "fecha_termino")
    search_fields = ("numero_contrato", "empresa__nombre")
    actions = ['export_selected_as_excel']
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

    def fecha_inicio_display(self, obj):
        try:
            if not getattr(obj, 'fecha_inicio', None):
                return ''
            return obj.fecha_inicio.strftime('%d/%m/%Y')
        except Exception:
            return ''
    fecha_inicio_display.short_description = 'Fecha de inicio'
    fecha_inicio_display.admin_order_field = 'fecha_inicio'

    def fecha_termino_display(self, obj):
        try:
            if not getattr(obj, 'fecha_termino', None):
                return ''
            return obj.fecha_termino.strftime('%d/%m/%Y')
        except Exception:
            return ''
    fecha_termino_display.short_description = 'Fecha de término'
    fecha_termino_display.admin_order_field = 'fecha_termino'

    resumen_asignaciones.short_description = 'Resumen de asignaciones'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('assignments-info/', self.admin_site.admin_view(self.assignments_info_view), name='recursos_humanos_contrato_assignments_info'),
            path('export-all-excel/', self.admin_site.admin_view(self.export_all_excel_view), name='recursos_humanos_contrato_export_all_excel'),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        """Inyectar URL para exportar todos en el contexto del changelist para el botón en la plantilla."""
        if extra_context is None:
            extra_context = {}
        try:
            from django.urls import reverse
            extra_context['export_all_url'] = reverse('admin:recursos_humanos_contrato_export_all_excel')
        except Exception:
            extra_context['export_all_url'] = None
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        """Prefetch related objects to avoid N+1 in changelist when showing cotizaciones y empleados."""
        qs = super().get_queryset(request)
        try:
            # Prefetch empleados y supervisor de las asignaciones vinculadas para reducir consultas
            return qs.prefetch_related('asignaciones_vinculadas__empleados', 'asignaciones_vinculadas__supervisor__usuario')
        except Exception:
            return qs

    def numeros_cotizacion(self, obj):
        """Devuelve los números de cotización vinculados separados por comas."""
        try:
            nums = [str(a.numero_cotizacion) if getattr(a, 'numero_cotizacion', None) else '(sin cot)' for a in obj.asignaciones_vinculadas.all()]
            return ', '.join(nums)
        except Exception:
            return ''
    numeros_cotizacion.short_description = 'No. cotización'

    def empleados_en_contrato(self, obj):
        """Lista los nombres de los empleados que estuvieron en este contrato (evita duplicados)."""
        try:
            # Construir la lista en orden de asignaciones: supervisor (si existe) primero, luego empleados
            names = []
            seen = set()
            for a in obj.asignaciones_vinculadas.all():
                # supervisor first
                try:
                    sup = getattr(a, 'supervisor', None)
                    if sup and getattr(sup, 'pk', None):
                        try:
                            sup_name = sup.usuario.get_full_name() if getattr(sup, 'usuario', None) else str(sup)
                        except Exception:
                            sup_name = str(sup)
                        if sup_name and sup_name not in seen:
                            seen.add(sup_name)
                            names.append(sup_name)
                except Exception:
                    pass
                # then employees in the assignment in their stored order
                try:
                    for e in a.empleados.all():
                        try:
                            nombre = e.usuario.get_full_name() if getattr(e, 'usuario', None) else str(e)
                        except Exception:
                            nombre = str(e)
                        if nombre and nombre not in seen:
                            seen.add(nombre)
                            names.append(nombre)
                except Exception:
                    continue

            # Mostrar cada empleado en una línea sin que el navegador rompa el nombre (nowrap)
            if not names:
                return ''
            from django.utils.html import format_html_join
            return format_html_join('\n', '<div style="white-space:nowrap;">{}</div>', ((n,) for n in names))
        except Exception:
            return ''
    empleados_en_contrato.short_description = 'Empleados'

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
                    # Contar empleados incluyendo al supervisor (sin duplicados)
                    'empleados': (len(set(list(a.empleados.values_list('pk', flat=True)) + ([a.supervisor.pk] if getattr(a, 'supervisor', None) and getattr(a.supervisor, 'pk', None) else []))) if hasattr(a, 'empleados') else 0),
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
        # Total empleados: contar empleados únicos entre las asignaciones seleccionadas,
        # incluyendo supervisores de cada asignación si existen
        total_set = set()
        for a in asigns:
            try:
                for pk in a.empleados.values_list('pk', flat=True):
                    total_set.add(pk)
            except Exception:
                pass
            try:
                sup = getattr(a, 'supervisor', None)
                if sup and getattr(sup, 'pk', None):
                    total_set.add(sup.pk)
            except Exception:
                pass
        total_emps = len(total_set)
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

    # ---- Export helpers ----
    def _generate_workbook_bytes(self, qs):
        """Try to build an XLSX using openpyxl; if not available, return CSV bytes as fallback."""
        headers = [
            'numero_contrato', 'empresa', 'fecha_inicio', 'fecha_termino', 'cantidad_empleados', 'dias_activos', 'numeros_cotizacion'
        ]
        # Build rows
        rows = []
        for obj in qs:
            nums = ','.join([str(a.numero_cotizacion) if getattr(a, 'numero_cotizacion', None) else '' for a in obj.asignaciones_vinculadas.all()])
            rows.append([
                obj.numero_contrato,
                getattr(obj.empresa, 'nombre', ''),
                obj.fecha_inicio.strftime('%Y-%m-%d') if getattr(obj, 'fecha_inicio', None) else '',
                obj.fecha_termino.strftime('%Y-%m-%d') if getattr(obj, 'fecha_termino', None) else '',
                str(getattr(obj, 'cantidad_empleados', '')),
                str(getattr(obj, 'dias_activos', '')),
                nums,
            ])

        try:
            import io
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.append(headers)
            for r in rows:
                ws.append(r)
            out = io.BytesIO()
            wb.save(out)
            return out.getvalue(), 'xlsx'
        except Exception:
            # Fallback to CSV
            import io, csv
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(headers)
            for r in rows:
                writer.writerow(r)
            return out.getvalue().encode('utf-8'), 'csv'

    def export_selected_as_excel(self, request, queryset):
        """Admin action: export selected Contrato rows to Excel/CSV."""
        data_bytes, fmt = self._generate_workbook_bytes(queryset)
        if fmt == 'xlsx':
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ext = 'xlsx'
        else:
            content_type = 'text/csv; charset=utf-8'
            ext = 'csv'
        from django.http import HttpResponse
        resp = HttpResponse(data_bytes, content_type=content_type)
        resp['Content-Disposition'] = f'attachment; filename=contratos_selected.{ext}'
        return resp
    export_selected_as_excel.short_description = 'Exportar seleccionados a Excel/CSV'

    def export_all_excel_view(self, request):
        """View to export all Contrato rows to Excel/CSV."""
        qs = self.get_queryset(request).all()
        data_bytes, fmt = self._generate_workbook_bytes(qs)
        if fmt == 'xlsx':
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ext = 'xlsx'
        else:
            content_type = 'text/csv; charset=utf-8'
            ext = 'csv'
        from django.http import HttpResponse
        resp = HttpResponse(data_bytes, content_type=content_type)
        resp['Content-Disposition'] = f'attachment; filename=contratos_all.{ext}'
        return resp

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
    # Use model fields directly in changelist so values render reliably
    list_display = ['numero_empleado', 'nombre_completo', 'fecha_nacimiento', 'puesto', 'salario_inicial', 'salario_actual', 'salario_fecha_ultima_modificacion', 'fecha_ingreso', 'activo', 'historial']
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

    def historial(self, obj):
        """Botones para acceder al historial de estatus y al historial de salario del empleado."""
        try:
            from django.urls import reverse
            estatus_url = reverse('admin:recursos_humanos_periodoestatusempleado_changelist') + f'?empleado__id__exact={obj.pk}'
            salario_url = reverse('admin:recursos_humanos_cambiosalarioempleado_changelist') + f'?empleado__id__exact={obj.pk}'
            return format_html(
                '<a class="button btn btn-sm btn-outline-primary" href="{}" style="margin-right:4px;">Estatus</a>'
                '<a class="button btn btn-sm btn-outline-secondary" href="{}">Salario</a>',
                estatus_url, salario_url
            )
        except Exception:
            return ''
    historial.short_description = 'Historial'
    historial.allow_tags = True

    def salario_inicial_display(self, obj):
        try:
            val = getattr(obj, 'salario_inicial', None)
            # Mostrar $0.00 cuando no tenga valor
            if val is None:
                val = 0
            # Formatear con signo peso y dos decimales
            return format_html('<span style="white-space:nowrap">${:,.2f}</span>', float(val))
        except Exception:
            return ''
    salario_inicial_display.short_description = 'Salario inicial'
    salario_inicial_display.admin_order_field = 'salario_inicial'

    def salario_actual_display(self, obj):
        try:
            val = getattr(obj, 'salario_actual', None)
            if val is None:
                val = 0
            return format_html('<span style="white-space:nowrap">${:,.2f}</span>', float(val))
        except Exception:
            return ''
    salario_actual_display.short_description = 'Salario actual'
    salario_actual_display.admin_order_field = 'salario_actual'

    def salario_fecha_ultima_modificacion(self, obj):
        """Devuelve la fecha del último cambio de salario (si existe)."""
        try:
            last = obj.historial_salario.first()
            if last and last.fecha:
                # Convertir a la zona horaria configurada en settings (si es aware)
                try:
                    fecha_local = timezone.localtime(last.fecha)
                except Exception:
                    fecha_local = last.fecha
                # Formatear como dd/mm/YYYY HH:MM
                return fecha_local.strftime('%d/%m/%Y %H:%M')
        except Exception:
            pass
        return ''
    salario_fecha_ultima_modificacion.short_description = 'Última modificación salario'

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
            # Si el POST contiene 'force', primero eliminar relaciones protegidas y luego el objeto
            if request.POST.get('force') == '1':
                # eliminar AsignacionPorTrabajador relacionados (si existen)
                try:
                    with transaction.atomic():
                        AsignacionPorTrabajador.objects.filter(empleado=obj).delete()
                        # proceder a eliminar el empleado
                        self.log_deletion(request, obj, str(obj))
                        obj_display = str(obj)
                        obj.delete()
                except Exception:
                    messages.error(request, _("Ocurrió un error al eliminar los registros relacionados."))
                    return redirect(f"admin:{opts.app_label}_{opts.model_name}_changelist")
                messages.success(request, _(f'Se eliminó "{obj_display}" y sus registros relacionados correctamente.'))
                return redirect(f"admin:{opts.app_label}_{opts.model_name}_changelist")
            # Intento normal de borrado: capturar ProtectedError y mostrar aviso
            try:
                with transaction.atomic():
                    self.log_deletion(request, obj, str(obj))
                    obj_display = str(obj)
                    obj.delete()
                messages.success(request, _(f'Se eliminó "{obj_display}" correctamente.'))
                return redirect(f"admin:{opts.app_label}_{opts.model_name}_changelist")
            except ProtectedError:
                # Obtener objetos protegidos que impiden la eliminación
                protected_qs = AsignacionPorTrabajador.objects.filter(empleado=obj)
                context = {
                    **self.admin_site.each_context(request),
                    "title": _("No se puede eliminar: existen registros relacionados"),
                    "object": obj,
                    "protected_qs": protected_qs,
                    "opts": opts,
                    "app_label": opts.app_label,
                }
                if extra_context:
                    context.update(extra_context)
                return TemplateResponse(request, "admin/recursos_humanos/empleado/delete_protected_confirmation.html", context)

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


# Registro simple para el historial de cambios de salario
@admin.register(CambioSalarioEmpleado)
class CambioSalarioEmpleadoAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'salario_anterior', 'salario_nuevo', 'observaciones')
    list_filter = ('fecha',)
    search_fields = ('empleado__numero_empleado', 'empleado__usuario__first_name', 'empleado__usuario__last_name')
    raw_id_fields = ('empleado',)

    # Usar un ModelForm para asegurar que el widget datetime-local muestre la fecha/hora local correctamente
    class CambioSalarioEmpleadoForm(forms.ModelForm):
        class Meta:
            model = CambioSalarioEmpleado
            fields = '__all__'
            widgets = {
                'fecha': DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'class': 'vDateTimeField form-control form-control-sm'}),
            }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Si viene una instancia con fecha (aware), convertir a hora local y formatear para datetime-local
            try:
                inst = kwargs.get('instance')
                if inst and getattr(inst, 'fecha', None):
                    from django.utils import timezone as timezone_local
                    local = timezone_local.localtime(inst.fecha)
                    # format as YYYY-MM-DDTHH:MM
                    self.initial['fecha'] = local.strftime('%Y-%m-%dT%H:%M')
            except Exception:
                pass

    form = CambioSalarioEmpleadoForm


