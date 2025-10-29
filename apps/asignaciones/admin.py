from django.contrib import admin, messages
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.utils.translation import gettext as _
from django.template.response import TemplateResponse
import json
from django.contrib.admin.options import IS_POPUP_VAR, TO_FIELD_VAR
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
        supervisor_id = None
        
        # Obtener supervisor_id del POST o del objeto existente
        if request.method == 'POST':
            supervisor_id = request.POST.get('supervisor')
            empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados', form_kwargs={'supervisor_id': supervisor_id})
            # Calcular porcentaje de actividades completadas para validación
            porcentaje_completadas = 0
            if obj and obj.pk:
                porcentaje_completadas = sum(a.porcentaje for a in obj.actividades.filter(completada=True))
            actividades_formset = ActividadAsignadaFormSet(request.POST, prefix='actividades', actividades_completadas_porcentaje=porcentaje_completadas)
        else:
            # Inicializa los empleados y actividades registrados, sin campos extra
            empleados_initial = []
            actividades_initial = []
            actividades_completadas = []
            porcentaje_completadas = 0
            if obj:
                empleados_initial = [{'empleado': e.pk} for e in obj.empleados.all()]
                # Separar actividades completadas de las pendientes
                for a in obj.actividades.all():
                    if a.completada:
                        actividades_completadas.append(a)
                        porcentaje_completadas += a.porcentaje
                    else:
                        actividades_initial.append({
                            'nombre': a.nombre, 
                            'porcentaje': a.porcentaje,
                            'tiempo_estimado_dias': a.tiempo_estimado_dias
                        })
                supervisor_id = obj.supervisor_id if obj.supervisor else None
            from .forms_custom import EmpleadoAsignacionFormSetFactory, ActividadAsignadaFormSetFactory
            EmpleadoFormSetClass = EmpleadoAsignacionFormSetFactory(extra=0 if empleados_initial else 1)
            empleados_formset = EmpleadoFormSetClass(initial=empleados_initial, prefix='empleados', form_kwargs={'supervisor_id': supervisor_id})
            actividades_formset = ActividadAsignadaFormSetFactory(extra=0 if actividades_initial else 1)(initial=actividades_initial, prefix='actividades', actividades_completadas_porcentaje=porcentaje_completadas)
            context['actividades_completadas'] = actividades_completadas
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
        # Validate actividades formset first; if invalid, render form again
        supervisor_id = request.POST.get('supervisor')
        empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados', form_kwargs={'supervisor_id': supervisor_id})
        actividades_formset = ActividadAsignadaFormSet(request.POST, prefix='actividades', actividades_completadas_porcentaje=0)
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

        # If valid, build message and redirect similarly to ModelAdmin.response_add
        opts = obj._meta
        preserved_filters = self.get_preserved_filters(request)
        obj_url = reverse(
            "admin:%s_%s_change" % (opts.app_label, opts.model_name),
            args=(obj.pk,),
            current_app=self.admin_site.name,
        )
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', obj_url, obj)
        else:
            obj_repr = str(obj)

        msg_dict = {"name": opts.verbose_name, "obj": obj_repr}

        if IS_POPUP_VAR in request.POST:
            to_field = request.POST.get(TO_FIELD_VAR)
            if to_field:
                attr = str(to_field)
            else:
                attr = obj._meta.pk.attname
            value = obj.serializable_value(attr)
            popup_response_data = json.dumps({"value": str(value), "obj": str(obj)})
            return TemplateResponse(
                request,
                self.popup_response_template
                or [
                    "admin/%s/%s/popup_response.html" % (opts.app_label, opts.model_name),
                    "admin/%s/popup_response.html" % opts.app_label,
                    "admin/popup_response.html",
                ],
                {"popup_response_data": popup_response_data},
            )

        if "_continue" in request.POST or ("_saveasnew" in request.POST and self.save_as_continue and self.has_change_permission(request, obj)):
            msg = _("La {name} \"{obj}\" fue agregada correctamente.")
            if self.has_change_permission(request, obj):
                msg = msg + " " + _("Puede editarla nuevamente a continuación.")
            self.message_user(request, format_html(msg, name=opts.verbose_name, obj=obj_repr), messages.SUCCESS)
            if post_url_continue is None:
                post_url_continue = obj_url
            post_url_continue = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, post_url_continue)
            return HttpResponseRedirect(post_url_continue)

        if "_addanother" in request.POST:
            fmt = _("La {name} \"{obj}\" fue agregada correctamente. Puede agregar otra {name} a continuación.")
            self.message_user(request, format_html(fmt, name=opts.verbose_name, obj=obj_repr), messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        fmt = _("La {name} \"{obj}\" fue agregada correctamente.")
        self.message_user(request, format_html(fmt, name=opts.verbose_name, obj=obj_repr), messages.SUCCESS)
        return self.response_post_save_add(request, obj)

    def response_change(self, request, obj):
        # Validar el formset de actividades primero
        supervisor_id = request.POST.get('supervisor')
        empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados', form_kwargs={'supervisor_id': supervisor_id})
        porcentaje_completadas = sum(a.porcentaje for a in obj.actividades.filter(completada=True))
        actividades_formset = ActividadAsignadaFormSet(request.POST, prefix='actividades', actividades_completadas_porcentaje=porcentaje_completadas)
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

        # Construir mensajes femeninos como en ModelAdmin.response_change
        opts = self.opts
        preserved_filters = self.get_preserved_filters(request)
        obj_url = reverse("admin:%s_%s_change" % (opts.app_label, opts.model_name), args=(obj.pk,), current_app=self.admin_site.name)
        obj_repr = format_html('<a href="{}">{}</a>', obj_url, obj) if self.has_change_permission(request, obj) else str(obj)

        if "_continue" in request.POST:
            msg = format_html(_("La {name} \"{obj}\" se cambió correctamente. Puede editarla nuevamente a continuación."), name=opts.verbose_name, obj=obj_repr)
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        if "_saveasnew" in request.POST:
            msg = format_html(_("La {name} \"{obj}\" se cambió correctamente. Puede editarla nuevamente a continuación."), name=opts.verbose_name, obj=obj_repr)
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse("admin:%s_%s_change" % (opts.app_label, opts.model_name), args=(obj.pk,), current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        if "_addanother" in request.POST:
            msg = format_html(_("La {name} \"{obj}\" se cambió correctamente. Puede agregar otra {name} a continuación."), name=opts.verbose_name, obj=obj_repr)
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse("admin:%s_%s_add" % (opts.app_label, opts.model_name), current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        msg = format_html(_("La {name} \"{obj}\" se cambió correctamente."), name=opts.verbose_name, obj=obj_repr)
        self.message_user(request, msg, messages.SUCCESS)
        return self.response_post_save_change(request, obj)

    def response_delete(self, request, obj_display, obj_id):
        """
        Custom delete response to provide a feminine message for Asignacion.
        """
        msg = _("La %(name)s \"%(obj)s\" fue eliminada con éxito.") % {
            "name": self.opts.verbose_name,
            "obj": obj_display,
        }
        self.message_user(request, msg, messages.SUCCESS)

        if self.has_change_permission(request, None):
            post_url = reverse(
                "admin:%s_%s_changelist" % (self.opts.app_label, self.opts.model_name),
                current_app=self.admin_site.name,
            )
            preserved_filters = self.get_preserved_filters(request)
            post_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": self.opts}, post_url)
        else:
            post_url = reverse("admin:index", current_app=self.admin_site.name)

        return HttpResponseRedirect(post_url)

    def save_model(self, request, obj, form, change):
        supervisor_id = request.POST.get('supervisor')
        empleados_formset = EmpleadoAsignacionFormSet(request.POST, prefix='empleados', form_kwargs={'supervisor_id': supervisor_id})
        # Calcular porcentaje de actividades completadas si estamos editando
        porcentaje_completadas = 0
        if change and obj.pk:
            porcentaje_completadas = sum(a.porcentaje for a in obj.actividades.filter(completada=True))
        actividades_formset = ActividadAsignadaFormSet(request.POST, prefix='actividades', actividades_completadas_porcentaje=porcentaje_completadas)
        if not actividades_formset.is_valid():
            # No guardar si hay error
            return
        
        # Guardar el supervisor anterior antes de actualizar
        supervisor_anterior = None
        if change and obj.pk:
            obj_anterior = Asignacion.objects.get(pk=obj.pk)
            supervisor_anterior = obj_anterior.supervisor
        
        obj = form.save(commit=False)
        obj.save()
        
        if empleados_formset.is_valid():
            empleados = [f.cleaned_data['empleado'] for f in empleados_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE', False)]
            obj.empleados.set(empleados)
        
        # Manejar actividades preservando las completadas
        if change and obj.pk:
            self._actualizar_actividades_preservando_completadas(obj, actividades_formset, supervisor_anterior)
        else:
            # Es una nueva asignación, crear normalmente
            actividades = []
            for f in actividades_formset.forms:
                if f.cleaned_data and not f.cleaned_data.get('DELETE', False):
                    actividades.append(f.cleaned_data)
            obj.actividades.all().delete()
            for act in actividades:
                obj.actividades.create(
                    nombre=act['nombre'], 
                    porcentaje=act['porcentaje'],
                    tiempo_estimado_dias=act.get('tiempo_estimado_dias', 1)
                )

    def _actualizar_actividades_preservando_completadas(self, obj, actividades_formset, supervisor_anterior):
        """
        Actualiza las actividades preservando las que ya están completadas
        """
        from django.contrib import messages
        from django.shortcuts import get_object_or_404
        
        # Obtener actividades actuales
        actividades_actuales = {act.nombre: act for act in obj.actividades.all()}
        
        # Obtener las nuevas actividades del formset
        nuevas_actividades = []
        for f in actividades_formset.forms:
            if f.cleaned_data and not f.cleaned_data.get('DELETE', False):
                nuevas_actividades.append(f.cleaned_data)
        
        # Obtener actividades completadas que deben preservarse
        actividades_completadas = {
            nombre: act for nombre, act in actividades_actuales.items() 
            if act.completada
        }
        
        # Eliminar solo las actividades pendientes (no completadas)
        actividades_a_eliminar = [
            act for act in actividades_actuales.values() 
            if not act.completada
        ]
        for act in actividades_a_eliminar:
            act.delete()
        
        # Agregar las nuevas actividades (solo si no están ya completadas)
        for nueva_act in nuevas_actividades:
            nombre = nueva_act['nombre']
            if nombre not in actividades_completadas:
                # Es una actividad nueva o pendiente, crearla
                obj.actividades.create(
                    nombre=nombre, 
                    porcentaje=nueva_act['porcentaje'],
                    tiempo_estimado_dias=nueva_act.get('tiempo_estimado_dias', 1)
                )
        
        # Si había actividades completadas y cambió el supervisor, notificar al admin
        if actividades_completadas and obj.supervisor != supervisor_anterior:
            self._notificar_cambio_supervisor_con_actividades_completadas(
                obj, supervisor_anterior, actividades_completadas
            )

    def _notificar_cambio_supervisor_con_actividades_completadas(self, obj, supervisor_anterior, actividades_completadas):
        """
        Notifica al admin cuando se cambia de supervisor y hay actividades completadas
        """
        from apps.notificaciones.models import Notificacion
        from apps.usuarios.models import Usuario
        
        admin_users = Usuario.objects.filter(is_staff=True)
        
        # Crear mensaje con detalles del cambio
        lineas = []
        lineas.append(f"🔄 CAMBIO DE SUPERVISOR EN ASIGNACIÓN")
        lineas.append("=" * 45)
        lineas.append(f"📋 Asignación: {obj.fecha.strftime('%d/%m/%Y')} - {obj.empresa.nombre}")
        lineas.append("")
        lineas.append(f"👤 Supervisor anterior: {supervisor_anterior.nombre_completo if supervisor_anterior else 'Sin supervisor'}")
        lineas.append(f"👤 Nuevo supervisor: {obj.supervisor.nombre_completo if obj.supervisor else 'Sin supervisor'}")
        lineas.append("")
        lineas.append(f"✅ Actividades completadas preservadas ({len(actividades_completadas)}):")
        
        for act in actividades_completadas.values():
            completada_por = act.completada_por.nombre_completo if act.completada_por else 'Usuario desconocido'
            fecha_completada = act.fecha_completada.strftime('%d/%m/%Y %H:%M') if act.fecha_completada else 'Fecha desconocida'
            lineas.append(f"   ✓ {act.nombre} ({act.porcentaje}%) - Completada por {completada_por} el {fecha_completada}")
        
        mensaje = '\n'.join(lineas)
        
        for admin in admin_users:
            Notificacion.objects.create(
                usuario=admin,
                titulo=f"🔄 Cambio de supervisor - {obj.empresa.nombre}",
                mensaje=mensaje,
                tipo='info'
            )
