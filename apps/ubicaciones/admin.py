from django.contrib import admin
from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from django.forms.widgets import DateInput, DateTimeInput
from .models import RegistroUbicacion, SemanaLaboralEmpleado, SemanaLaboralDia


@admin.register(RegistroUbicacion)
class RegistroUbicacionAdmin(admin.ModelAdmin):
    list_display = [
        'empleado', 'tipo', 'fecha_local_formatted', 
        'coordenadas_str', 'precision'
    ]
    list_filter = ['tipo', 'timestamp', 'empleado']
    search_fields = ['empleado__usuario__first_name', 'empleado__usuario__last_name', 'empleado__numero_empleado']
    readonly_fields = ['fecha_creacion', 'timestamp']
    date_hierarchy = 'timestamp'
    
    def fecha_local_formatted(self, obj):
        return obj.fecha_local.strftime('%d/%m/%Y %H:%M:%S')
    fecha_local_formatted.short_description = 'Fecha y Hora (Local)'
    fecha_local_formatted.admin_order_field = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('empleado__usuario')

class SemanaLaboralEmpleadoForm(forms.ModelForm):
    # Use a plain HTML5 date input (type=date) to avoid JS/widget localization issues
    semana_inicio = forms.DateField(
        widget=DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y']
    )

    class Meta:
        model = SemanaLaboralEmpleado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use the bound instance (self.instance) to set explicit initial value.
        # Setting initial as ISO string helps AdminDateWidget display correctly
        inst = getattr(self, 'instance', None)
        if inst and getattr(inst, 'semana_inicio', None):
            try:
                # Use ISO format which AdminDateWidget accepts reliably
                self.fields['semana_inicio'].initial = inst.semana_inicio.isoformat()
            except Exception:
                self.fields['semana_inicio'].initial = inst.semana_inicio


@admin.register(SemanaLaboralEmpleado)
class SemanaLaboralEmpleadoAdmin(admin.ModelAdmin):
    form = SemanaLaboralEmpleadoForm
    list_display = ['empleado', 'semana_inicio', 'horas_trabajadas', 'fecha_actualizacion']
    list_filter = ['semana_inicio']
    search_fields = ['empleado__usuario__first_name', 'empleado__usuario__last_name', 'empleado__numero_empleado']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    date_hierarchy = 'semana_inicio'
    change_list_template = 'admin/ubicaciones/semanalaboralempleado/change_list.html'
    actions = ['export_selected_as_excel']

    def export_selected_as_excel(self, request, queryset):
        """Exporta las semanas seleccionadas a Excel/CSV incluyendo columnas Lunes..Domingo con entrada/salida/horas."""
        # Build rows
        headers = [
            'Empleado (no.)', 'Empleado (nombre)', 'Semana inicio',
            'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo',
            'Horas trabajadas', 'Fecha actualización', 'Fecha creación'
        ]

        rows = []
        for semana in queryset.select_related('empleado__usuario').prefetch_related('dias'):
            # Map days by weekday (0=Monday..6=Sunday)
            dias_map = {d.fecha.weekday(): d for d in semana.dias.all()}
            def fmt_day(d):
                if not d:
                    return '-'
                ent = d.entrada.strftime('%Y-%m-%d %H:%M') if getattr(d, 'entrada', None) else ''
                sal = d.salida.strftime('%Y-%m-%d %H:%M') if getattr(d, 'salida', None) else ''
                hrs = f"{d.horas:.2f}" if getattr(d, 'horas', None) is not None else ''
                parts = []
                if ent:
                    parts.append(ent)
                if sal:
                    parts.append(sal)
                if hrs:
                    parts.append(f"({hrs} h)")
                return ' - '.join(parts) if parts else '-'

            day_cells = [fmt_day(dias_map.get(i)) for i in range(7)]

            empleado_no = getattr(semana.empleado, 'numero_empleado', '')
            empleado_name = semana.empleado.usuario.get_full_name() if getattr(semana.empleado, 'usuario', None) else str(semana.empleado)
            row = [
                empleado_no,
                empleado_name,
                semana.semana_inicio.strftime('%Y-%m-%d') if semana.semana_inicio else '',
            ] + day_cells + [
                f"{semana.horas_trabajadas:.2f}",
                semana.fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S') if getattr(semana, 'fecha_actualizacion', None) else '',
                semana.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if getattr(semana, 'fecha_creacion', None) else '',
            ]
            rows.append(row)

        # Try openpyxl
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
            data = out.getvalue()
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = 'semanas_laborales.xlsx'
        except Exception:
            # Fallback CSV
            import io, csv
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(headers)
            for r in rows:
                writer.writerow(r)
            data = out.getvalue().encode('utf-8')
            content_type = 'text/csv; charset=utf-8'
            filename = 'semanas_laborales.csv'

        from django.http import HttpResponse
        resp = HttpResponse(data, content_type=content_type)
        resp['Content-Disposition'] = f'attachment; filename={filename}'
        return resp
    export_selected_as_excel.short_description = 'Exportar seleccionados a Excel/CSV'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('export-all-excel/', self.admin_site.admin_view(self.export_all_excel_view), name='ubicaciones_semanalaboralempleado_export_all_excel'),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        try:
            from django.urls import reverse
            extra_context['export_all_url'] = reverse('admin:ubicaciones_semanalaboralempleado_export_all_excel')
        except Exception:
            extra_context['export_all_url'] = None
        return super().changelist_view(request, extra_context=extra_context)

    def export_all_excel_view(self, request):
        """Exportar todo el queryset del changelist actual a Excel/CSV."""
        qs = self.get_queryset(request).all()
        # Reuse logic from action: build rows
        headers = [
            'Empleado (no.)', 'Empleado (nombre)', 'Semana inicio',
            'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo',
            'Horas trabajadas', 'Fecha actualización', 'Fecha creación'
        ]
        rows = []
        for semana in qs.select_related('empleado__usuario').prefetch_related('dias'):
            dias_map = {d.fecha.weekday(): d for d in semana.dias.all()}
            def fmt_day(d):
                if not d:
                    return '-'
                ent = d.entrada.strftime('%Y-%m-%d %H:%M') if getattr(d, 'entrada', None) else ''
                sal = d.salida.strftime('%Y-%m-%d %H:%M') if getattr(d, 'salida', None) else ''
                hrs = f"{d.horas:.2f}" if getattr(d, 'horas', None) is not None else ''
                parts = []
                if ent:
                    parts.append(ent)
                if sal:
                    parts.append(sal)
                if hrs:
                    parts.append(f"({hrs} h)")
                return ' - '.join(parts) if parts else '-'
            day_cells = [fmt_day(dias_map.get(i)) for i in range(7)]
            empleado_no = getattr(semana.empleado, 'numero_empleado', '')
            empleado_name = semana.empleado.usuario.get_full_name() if getattr(semana.empleado, 'usuario', None) else str(semana.empleado)
            row = [empleado_no, empleado_name, semana.semana_inicio.strftime('%Y-%m-%d') if semana.semana_inicio else ''] + day_cells + [f"{semana.horas_trabajadas:.2f}", semana.fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S') if getattr(semana, 'fecha_actualizacion', None) else '', semana.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if getattr(semana, 'fecha_creacion', None) else '']
            rows.append(row)

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
            data = out.getvalue()
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = 'semanas_laborales_all.xlsx'
        except Exception:
            import io, csv
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(headers)
            for r in rows:
                writer.writerow(r)
            data = out.getvalue().encode('utf-8')
            content_type = 'text/csv; charset=utf-8'
            filename = 'semanas_laborales_all.csv'

        from django.http import HttpResponse
        resp = HttpResponse(data, content_type=content_type)
        resp['Content-Disposition'] = f'attachment; filename={filename}'
        return resp


class SemanaLaboralDiaInline(admin.TabularInline):
    model = SemanaLaboralDia
    fields = ['fecha', 'entrada', 'salida', 'horas']
    readonly_fields = ['horas']
    extra = 0
    ordering = ['fecha']


class SemanaLaboralDiaForm(forms.ModelForm):
    fecha = forms.DateField(
        widget=DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y']
    )

    entrada = forms.DateTimeField(
        required=False,
        widget=DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M']
    )

    salida = forms.DateTimeField(
        required=False,
        widget=DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M']
    )

    class Meta:
        model = SemanaLaboralDia
        fields = ['fecha', 'entrada', 'salida', 'horas']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = getattr(self, 'instance', None)
        if inst:
            if getattr(inst, 'fecha', None):
                try:
                    self.fields['fecha'].initial = inst.fecha.isoformat()
                except Exception:
                    self.fields['fecha'].initial = inst.fecha
            if getattr(inst, 'entrada', None):
                try:
                    self.fields['entrada'].initial = inst.entrada.strftime('%Y-%m-%dT%H:%M')
                except Exception:
                    self.fields['entrada'].initial = inst.entrada
            if getattr(inst, 'salida', None):
                try:
                    self.fields['salida'].initial = inst.salida.strftime('%Y-%m-%dT%H:%M')
                except Exception:
                    self.fields['salida'].initial = inst.salida

SemanaLaboralEmpleadoAdmin.inlines = [SemanaLaboralDiaInline]
SemanaLaboralDiaInline.form = SemanaLaboralDiaForm