from django.contrib import admin
from django import forms
from .models import Asignacion
from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Empresa
from .forms_custom import EmpleadoAsignacionFormSet, AsignacionCustomForm, ActividadAsignadaFormSet


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    def save_form(self, request, form, change):
        return form.save(commit=False)
    form = AsignacionCustomForm
    change_form_template = 'admin/asignaciones/asignacion/change_form.html'
    change_list_template = 'admin/asignaciones/asignacion/change_list.html'
    list_display = ('fecha', 'get_empleados', 'empresa', 'supervisor', 'detalles')
    list_filter = ('fecha', 'empresa')
    search_fields = (
        'empleados__usuario__first_name',
        'empleados__usuario__last_name',
        'empleados__numero_empleado',
        'empresa__nombre',
        'supervisor__usuario__first_name',
        'supervisor__usuario__last_name',
    )

    def get_empleados(self, obj):
        return ', '.join([str(e) for e in obj.empleados.all()])
    get_empleados.short_description = 'Empleados'

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get('original')
        if request.method == 'POST':
            empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados')
            actividades_formset = ActividadAsignadaFormSet(request.POST, prefix='actividades')
        else:
            # Inicializa los empleados y actividades registrados, sin campos extra
            empleados_initial = []
            actividades_initial = []
            if obj:
                empleados_initial = [{'empleado': e.pk} for e in obj.empleados.all()]
                actividades_initial = [{'nombre': a.nombre, 'porcentaje': a.porcentaje} for a in obj.actividades.all()]
            from .forms_custom import EmpleadoAsignacionFormSetFactory, ActividadAsignadaFormSetFactory
            empleados_formset = EmpleadoAsignacionFormSetFactory(extra=0 if empleados_initial else 1)(initial=empleados_initial, prefix='empleados')
            actividades_formset = ActividadAsignadaFormSetFactory(extra=0 if actividades_initial else 1)(initial=actividades_initial, prefix='actividades')
        context = dict(context)  # Copia el contexto para modificarlo
        context['empleados_formset'] = empleados_formset
        context['actividades_formset'] = actividades_formset
        # Asegura las claves requeridas por el template de admin
        context.setdefault('inline_admin_formsets', [])
        # adminform nunca debe ser None
        if not context.get('adminform'):
            from django.contrib.admin.helpers import AdminForm
            # Asegura que 'form' esté en el contexto
            form = context.get('form')
            if form is None and 'adminform' not in context:
                initial = dict(context.get('initial', {}))
                # Si estamos editando, usa la fecha del objeto
                if obj and obj.fecha:
                    initial['fecha'] = obj.fecha.strftime('%Y-%m-%d')
                form = self.get_form(request)(initial=initial)
                context['form'] = form
            fieldsets = self.get_fieldsets(request, context.get('original'))
            prepopulated_fields = self.get_prepopulated_fields(request, context.get('original'))
            readonly_fields = self.get_readonly_fields(request, context.get('original'))
            model_admin = self
            adminform = AdminForm(form, fieldsets, prepopulated_fields, readonly_fields, model_admin)
            context['adminform'] = adminform
        context.setdefault('object_id', context.get('object_id'))
        context.setdefault('original', context.get('original'))
        context.setdefault('is_popup', False)
        context.setdefault('to_field', None)
        context.setdefault('media', context.get('media'))
        context.setdefault('errors', context.get('errors'))
        context.setdefault('app_label', self.model._meta.app_label)
        return super().render_change_form(request, context, *args, **kwargs)


    def response_add(self, request, obj, post_url_continue=None):
        from django.contrib import messages
        empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados')
        actividades_formset = ActividadAsignadaFormSet(request.POST, prefix='actividades')
        if not actividades_formset.is_valid():
            # Marca el formset para saltar la validación y evitar error de formulario
            actividades_formset._skip_clean = True
            form = self.get_form(request)(request.POST, request.FILES)
            from django.contrib.admin.helpers import AdminForm
            fieldsets = self.get_fieldsets(request)
            prepopulated_fields = self.get_prepopulated_fields(request)
            readonly_fields = self.get_readonly_fields(request)
            adminform = AdminForm(form, fieldsets, prepopulated_fields, readonly_fields, self)
            context = self.admin_site.each_context(request)
            context.update({
                'title': 'Añadir asignación',
                'adminform': adminform,
                'form': form,
                'empleados_formset': empleados_formset,
                'actividades_formset': actividades_formset,
                'is_popup': False,
                'to_field': None,
                'media': self.media + form.media,
                'errors': form.errors,
                'app_label': self.model._meta.app_label,
                'inline_admin_formsets': [],
            })
            return super().render_change_form(request, context, add=True, change=False, obj=None)
        return super().response_add(request, obj, post_url_continue)
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        from django.contrib import messages
        empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados')
        actividades_formset = ActividadAsignadaFormSet(request.POST, prefix='actividades')
        if not actividades_formset.is_valid():
            error_msg = actividades_formset.non_form_errors()
            if error_msg:
                messages.error(request, error_msg[0])
            else:
                messages.error(request, 'Error en las actividades asignadas. Verifica los porcentajes.')
            return self.render_change_form(request, {
                'empleados_formset': empleados_formset,
                'actividades_formset': actividades_formset,
            })
        return super().response_change(request, obj)

    def save_model(self, request, obj, form, change):
        empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados')
        actividades_formset = ActividadAsignadaFormSet(request.POST, prefix='actividades')
        if not actividades_formset.is_valid():
            # No guardar si hay error
            return
        obj = form.save(commit=False)
        obj.save()
        if empleados_formset.is_valid():
            empleados = [f.cleaned_data['empleado'] for f in empleados_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE', False)]
            obj.empleados.set(empleados)
        actividades = []
        for f in actividades_formset.forms:
            if f.cleaned_data and not f.cleaned_data.get('DELETE', False):
                actividades.append(f.cleaned_data)
        obj.actividades.all().delete()
        for act in actividades:
            obj.actividades.create(nombre=act['nombre'], porcentaje=act['porcentaje'])
