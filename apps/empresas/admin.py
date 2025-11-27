from django.contrib import admin, messages
from django.contrib import admin, messages
from django.utils.html import format_html, format_html_join
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.utils.translation import gettext as _
from django.conf import settings
from django.template.response import TemplateResponse
import json
from django.contrib.admin.options import IS_POPUP_VAR, TO_FIELD_VAR
from .models import Empresa, Contacto
from .models import CTZ
from .models import CTZItem
from .models import CTZFormato
from .models import CTZFormatoDetalle
from django import forms
import logging
from django.db.models.deletion import ProtectedError


class CTZFormatoForm(forms.ModelForm):
    class Meta:
        model = CTZFormato
        # Excluir campos legacy `ctz`, `cantidad`, `unidad` y `pu` del formulario principal.
        # El admin mostrará únicamente el M2M `ctzs`, los campos descriptivos y los totales
        # (subtotal/iva/total) que son actualizados por el JS en base a las entradas por-CTZ.
        # Añadimos 'propuesta_redaccion' y 'notas_observaciones' como textareas opcionales.
        fields = ('ctzs', 'partida', 'concepto', 'propuesta_redaccion', 'notas_observaciones', 'contacto', 'fecha_manual', 'subtotal', 'iva', 'total')
        widgets = {
            # Renderizar subtotal/iva/total como inputs readonly para permitir que el JS los actualice.
            'subtotal': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'iva': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'total': forms.NumberInput(attrs={'readonly': 'readonly'}),
            # Hacer que 'concepto' y 'propuesta_redaccion' tengan la misma altura
            # que 'notas_observaciones' para consistencia visual en el admin.
            'concepto': forms.Textarea(attrs={'rows': 6}),
            'propuesta_redaccion': forms.Textarea(attrs={'rows': 6}),
            'notas_observaciones': forms.Textarea(attrs={'rows': 6}),
        }
        labels = {
            'partida': 'Propuesta No.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos editando una instancia existente, filtrar el queryset
        # del campo 'contacto' para mostrar sólo los contactos pertenecientes
        # a la(s) empresa(s) de las CTZ asociadas a este formato.
        try:
            instance = kwargs.get('instance')
            if instance and getattr(instance, 'pk', None):
                # Recoger empresas únicas de las CTZ relacionadas
                empresas_qs = instance.ctzs.select_related('empresa').all()
                empresa_ids = []
                for c in empresas_qs:
                    try:
                        eid = getattr(c.empresa, 'pk', None)
                    except Exception:
                        eid = None
                    if eid:
                        empresa_ids.append(eid)
                if empresa_ids:
                    # Filtrar contactos sólo de esas empresas
                    self.fields['contacto'].queryset = Contacto.objects.filter(empresa__pk__in=list(dict.fromkeys(empresa_ids)))
                else:
                    # Si no hay empresas asociadas, dejar queryset vacío para evitar mostrar todos los contactos
                    self.fields['contacto'].queryset = Contacto.objects.none()
        except Exception:
            # No queremos romper el form por errores al filtrar el queryset
            pass


class CTZForm(forms.ModelForm):
    class Meta:
        model = CTZ
        fields = '__all__'
        widgets = {
            'pu': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'total_pu': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'proveedor': forms.NumberInput(attrs={'min': 0}),
            'mo_soma': forms.NumberInput(attrs={'min': 0}),
            'otros_materiales': forms.NumberInput(attrs={'min': 0}),
            'porcentaje_pu': forms.NumberInput(attrs={'step': '0.01', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        # Si se pasa una instancia (change form), calcular valores iniciales
        # para los campos proveedor/mo_soma/otros_materiales sumando los
        # ítems relacionados y el valor base (si existe). Esto corrige el
        # caso en el que guardamos los valores en CTZItem y pusimos a 0
        # los campos base en la fila de CTZ; queremos que el form muestre
        # la suma esperada al editar.
        super().__init__(*args, **kwargs)
        # Prefer explicit 'instance' kwarg (ModelForm convention). Do NOT
        # interpret args[0] as instance because in Django forms args[0]
        # is usually the POST data (QueryDict) when the form is bound.
        instance = kwargs.get('instance')
        if instance and getattr(instance, 'pk', None) and not self.is_bound:
            try:
                from django.db.models import Sum
                # Sumar cantidades de items por tipo
                prov_sum = instance.items.filter(tipo='proveedor').aggregate(s=Sum('cantidad')).get('s') or 0
                mo_sum = instance.items.filter(tipo='mo_soma').aggregate(s=Sum('cantidad')).get('s') or 0
                otros_sum = instance.items.filter(tipo='otros_materiales').aggregate(s=Sum('cantidad')).get('s') or 0
                # Valor base guardado en la fila (puede ser 0 si usamos la estrategia de fallback)
                base_prov = int(getattr(instance, 'proveedor', 0) or 0)
                base_mo = int(getattr(instance, 'mo_soma', 0) or 0)
                base_otros = int(getattr(instance, 'otros_materiales', 0) or 0)
                # Mostrar al usuario la suma total (base + items)
                total_prov = int(prov_sum or 0) + base_prov
                total_mo = int(mo_sum or 0) + base_mo
                total_otros = int(otros_sum or 0) + base_otros
                # Set both field.initial and form.initial so ModelAdmin templates
                # reliably render the values in the inputs.
                if 'proveedor' in self.fields:
                    self.fields['proveedor'].initial = total_prov
                    self.initial['proveedor'] = total_prov
                if 'mo_soma' in self.fields:
                    self.fields['mo_soma'].initial = total_mo
                    self.initial['mo_soma'] = total_mo
                if 'otros_materiales' in self.fields:
                    self.fields['otros_materiales'].initial = total_otros
                    self.initial['otros_materiales'] = total_otros
            except Exception:
                # No romper el form por errores al calcular sumas
                pass


class ContactoInline(admin.TabularInline):
    model = Contacto
    extra = 1
    fields = ('nombre', 'apellidos', 'telefono', 'correo')
    show_change_link = True


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    def delete_model(self, request, obj):
        """Intentar borrar la empresa; si hay ProtectedError, mostrar mensaje claro al usuario indicando qué relaciones la están usando."""
        try:
            return super().delete_model(request, obj)
        except ProtectedError as e:
            # Construir lista de relaciones con conteo
            parts = []
            for f in obj._meta.get_fields():
                # buscamos relaciones reversas auto creadas
                if not getattr(f, 'auto_created', False):
                    continue
                if not getattr(f, 'is_relation', False):
                    continue
                accessor = f.get_accessor_name()
                if not hasattr(obj, accessor):
                    continue
                rel = getattr(obj, accessor)
                try:
                    cnt = rel.count()
                except Exception:
                    cnt = 0
                if cnt:
                    # nombre legible
                    try:
                        label = f.related_model._meta.verbose_name_plural
                    except Exception:
                        label = accessor
                    parts.append(f"{cnt} {label}")
            if not parts:
                # Fallback al mensaje genérico provisto por ProtectedError
                msg = _('La %(name)s "%(obj)s" no se puede eliminar porque hay objetos relacionados que la protegen.') % {
                    'name': self.opts.verbose_name,
                    'obj': str(obj),
                }
            else:
                msg = _('La %(name)s "%(obj)s" no se puede eliminar porque actualmente está siendo usada por: %(rels)s.') % {
                    'name': self.opts.verbose_name,
                    'obj': str(obj),
                    'rels': ', '.join(parts),
                }
            self.message_user(request, msg, level=messages.ERROR)
            return None

    def delete_queryset(self, request, queryset):
        """Override para manejar borrados en lote y reportar cuáles no pudieron borrarse por ProtectedError."""
        failed = []
        for obj in list(queryset):
            try:
                obj.delete()
            except ProtectedError:
                failed.append(str(obj))
        if failed:
            msg = _('No se pudieron eliminar las siguientes %(name)s porque están siendo usadas: %(objs)s') % {
                'name': self.opts.verbose_name_plural,
                'objs': '; '.join(failed),
            }
            self.message_user(request, msg, level=messages.ERROR)

    def delete_view(self, request, object_id, extra_context=None):
        """Override delete view to show a friendly message on the confirmation
        page explaining which related objects would prevent deletion.
        """
        obj = self.get_object(request, object_id)
        if obj is None:
            return super().delete_view(request, object_id, extra_context=extra_context)

        # Only annotate the GET confirmation page (before deletion) with info
        if request.method == 'GET':
            parts = []
            for f in obj._meta.get_fields():
                if not getattr(f, 'auto_created', False):
                    continue
                if not getattr(f, 'is_relation', False):
                    continue
                accessor = f.get_accessor_name()
                if not hasattr(obj, accessor):
                    continue
                rel = getattr(obj, accessor)
                try:
                    cnt = rel.count()
                except Exception:
                    cnt = 0
                if cnt:
                    try:
                        label = f.related_model._meta.verbose_name_plural
                    except Exception:
                        label = accessor
                    parts.append(f"{cnt} {label}")
            if parts:
                msg = _('La %(name)s "%(obj)s" no se puede eliminar porque actualmente está siendo usada por: %(rels)s.') % {
                    'name': self.opts.verbose_name,
                    'obj': str(obj),
                    'rels': ', '.join(parts),
                }
                # Use warning so it appears on the confirmation page
                self.message_user(request, msg, level=messages.WARNING)

        return super().delete_view(request, object_id, extra_context=extra_context)

    def logo_preview(self, obj: Empresa):
        if obj.logo:
            return format_html('<img src="{}" alt="Logo" style="height:32px; width:auto; object-fit:contain; background:#fafafa; padding:2px; border:1px solid #eee; border-radius:4px;"/>', obj.logo.url)
        return '—'
    logo_preview.short_description = 'Logo'
    logo_preview.admin_order_field = 'logo'

    def direccion_preview(self, obj: Empresa):
        if obj.direccion:
            text = obj.direccion.strip().replace('\n', ' ')
            return (text[:60] + '…') if len(text) > 60 else text
        return '—'
    direccion_preview.short_description = 'Dirección'

    list_display = ['logo_preview', 'nombre', 'direccion_preview', 'activa']
    list_display_links = ['nombre']
    # No incluir el inline Contacto aquí: los Contactos se gestionan en su
    # propio apartado del admin. Evita que el formulario de Empresa muestre
    # la tabla de Contactos y problemas con el ManagementForm.
    list_filter = ['activa']
    search_fields = ['nombre']
    # list_editable removed: do not allow inline edits from changelist
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre',)
        }),
        ('Dirección', {
            'fields': ('direccion',)
        }),
        ('Imagen', {
            'fields': ('logo',),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('activa',)
        }),
    )

    def response_delete(self, request, obj_display, obj_id):
        """
        Custom delete response to provide a feminine message for Empresa.
        """
        # Use feminine phrasing specifically for Empresa
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
            post_url = add_preserved_filters(
                {"preserved_filters": preserved_filters, "opts": self.opts}, post_url
            )
        else:
            post_url = reverse("admin:index", current_app=self.admin_site.name)

        return HttpResponseRedirect(post_url)

    def response_change(self, request, obj):
        """
        Custom change response to provide a feminine message for Empresa.
        Replicates ModelAdmin.response_change behaviour but customizes the
        success messages to use feminine phrasing.
        """
        opts = self.opts
        preserved_filters = self.get_preserved_filters(request)

        msg_dict = {
            "name": opts.verbose_name,
            "obj": str(obj),
        }

        if "_continue" in request.POST:
            msg = _("La %(name)s \"%(obj)s\" se cambió correctamente. Puede editarlo nuevamente a continuación.") % msg_dict
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_saveasnew" in request.POST:
            msg = _("La %(name)s \"%(obj)s\" se cambió correctamente. Puede editarlo nuevamente a continuación.") % msg_dict
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse("admin:%s_%s_change" % (opts.app_label, opts.model_name), args=(obj.pk,), current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_addanother" in request.POST:
            msg = _("La %(name)s \"%(obj)s\" se cambió correctamente. Puede agregar otro %(name)s a continuación.") % msg_dict
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse("admin:%s_%s_add" % (opts.app_label, opts.model_name), current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        else:
            msg = _("La %(name)s \"%(obj)s\" se cambió correctamente.") % msg_dict
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        """
        Custom add response to provide a feminine message for Empresa.
        Replicates ModelAdmin.response_add behaviour but customizes the
        success messages to use feminine phrasing.
        """
        opts = obj._meta
        preserved_filters = self.get_preserved_filters(request)
        obj_url = reverse(
            "admin:%s_%s_change" % (opts.app_label, opts.model_name),
            args=(obj.pk,),
            current_app=self.admin_site.name,
        )
        # Add a link to the object's change form if the user can edit the obj.
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', obj_url, obj)
        else:
            obj_repr = str(obj)

        msg_dict = {
            "name": opts.verbose_name,
            "obj": obj_repr,
        }

        if IS_POPUP_VAR in request.POST:
            to_field = request.POST.get(TO_FIELD_VAR)
            if to_field:
                attr = str(to_field)
            else:
                attr = obj._meta.pk.attname
            value = obj.serializable_value(attr)
            popup_response_data = json.dumps(
                {
                    "value": str(value),
                    "obj": str(obj),
                }
            )
            return TemplateResponse(
                request,
                self.popup_response_template
                or [
                    "admin/%s/%s/popup_response.html" % (opts.app_label, opts.model_name),
                    "admin/%s/popup_response.html" % opts.app_label,
                    "admin/popup_response.html",
                ],
                {
                    "popup_response_data": popup_response_data,
                },
            )

        elif "_continue" in request.POST or (
            # Redirecting after "Save as new".
            "_saveasnew" in request.POST
            and self.save_as_continue
            and self.has_change_permission(request, obj)
        ):
            msg = _("La %(name)s \"%(obj)s\" fue agregada correctamente.") % msg_dict
            if self.has_change_permission(request, obj):
                msg = msg + " " + _("Puede editarla nuevamente a continuación.")
            self.message_user(request, format_html(msg), messages.SUCCESS)
            if post_url_continue is None:
                post_url_continue = obj_url
            post_url_continue = add_preserved_filters(
                {"preserved_filters": preserved_filters, "opts": opts}, post_url_continue
            )
            return HttpResponseRedirect(post_url_continue)

        elif "_addanother" in request.POST:
            fmt = _(
                "La {name} \"{obj}\" fue agregada correctamente. Puede agregar otra {name} a continuación."
            )
            msg = format_html(fmt, name=opts.verbose_name, obj=obj_repr)
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters(
                {"preserved_filters": preserved_filters, "opts": opts}, redirect_url
            )
            return HttpResponseRedirect(redirect_url)

        else:
            fmt = _("La {name} \"{obj}\" fue agregada correctamente.")
            msg = format_html(fmt, name=opts.verbose_name, obj=obj_repr)
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_add(request, obj)


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'empresa', 'telefono', 'correo', 'fecha_nacimiento')
    list_filter = ('empresa', 'fecha_nacimiento')
    search_fields = ('nombre', 'apellidos', 'telefono', 'correo', 'empresa__nombre')
    verbose_name = 'Contacto'
    verbose_name_plural = 'Contactos'


@admin.register(CTZ)
class CTZAdmin(admin.ModelAdmin):
    form = CTZForm
    inlines = []
    list_display = ('id_manual', 'empresa', 'proveedor_display', 'mo_soma_display', 'otros_materiales_display', 'pu_display', 'porcentaje_pu_display', 'total_pu_display', 'fecha_creacion')
    list_filter = ('empresa',)
    search_fields = ('empresa__nombre',)
    # Mostrar los campos calculados como inputs readonly (no como "readonly_fields")
    # para que puedan actualizarse dinámicamente desde JS en el formulario.
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    fieldsets = (
        (None, {
            'fields': ('empresa', 'id_manual')
        }),
        ('Costos', {
            'fields': ('proveedor', 'mo_soma', 'otros_materiales', 'porcentaje_pu')
        }),
        ('Cálculos', {
            'fields': ('pu', 'total_pu')
        }),
    )

    def save_model(self, request, obj, form, change):
        # Asegurarse de recalcular antes de guardar (aunque el modelo ya lo hace)
        obj.pu = obj.calcular_pu()
        obj.total_pu = obj.calcular_total_pu(obj.pu)
        # Guardar primero el objeto para asegurar que tiene PK
        super().save_model(request, obj, form, change)
        # Sincronizar los CTZItem como reflejo de los campos individuales.
        # En este diseño dejamos el inline fuera del admin y gestionamos los
        # items en el servidor: borramos cualquier ítem previo de los tipos
        # manejados y (re)creamos uno por tipo con la cantidad actual.
        # Logging temporal para depuración: mostrar lo que llega en POST y los
        # valores calculados antes de guardar. Quitar o bajar nivel una vez
        # resuelto el problema.
        logger = logging.getLogger(__name__)
        try:
            logger.debug('CTZFormato.save_model POST keys: %s', list(request.POST.keys()))
        except Exception:
            pass

        try:
            # Borrar items antiguos de los tipos manejados
            # If the client submitted per-item values (ctz_items_<tipo>) use them.
            from .models import CTZItem
            prov_items = request.POST.getlist('ctz_items_proveedor') if request is not None else []
            mo_items = request.POST.getlist('ctz_items_mo_soma') if request is not None else []
            otros_items = request.POST.getlist('ctz_items_otros_materiales') if request is not None else []
            # (diagnostics removed) -- proceed with processing of posted ctz_items_*
            # remove previous items for these types
            obj.items.filter(tipo__in=['proveedor', 'mo_soma', 'otros_materiales']).delete()
            new_items = []
            if prov_items or mo_items or otros_items:
                # create one CTZItem per posted value (allow multiple per type)
                for v in prov_items:
                    try:
                        vv = int(float(v))
                    except Exception:
                        continue
                    new_items.append(CTZItem(ctz=obj, tipo='proveedor', cantidad=vv))
                for v in mo_items:
                    try:
                        vv = int(float(v))
                    except Exception:
                        continue
                    new_items.append(CTZItem(ctz=obj, tipo='mo_soma', cantidad=vv))
                for v in otros_items:
                    try:
                        vv = int(float(v))
                    except Exception:
                        continue
                    new_items.append(CTZItem(ctz=obj, tipo='otros_materiales', cantidad=vv))
            else:
                # fallback: create a single CTZItem per type from the main fields
                try:
                    prov = int(obj.proveedor or 0)
                except Exception:
                    prov = 0
                try:
                    mo = int(obj.mo_soma or 0)
                except Exception:
                    mo = 0
                try:
                    otros = int(obj.otros_materiales or 0)
                except Exception:
                    otros = 0
                if prov:
                    new_items.append(CTZItem(ctz=obj, tipo='proveedor', cantidad=prov))
                if mo:
                    new_items.append(CTZItem(ctz=obj, tipo='mo_soma', cantidad=mo))
                if otros:
                    new_items.append(CTZItem(ctz=obj, tipo='otros_materiales', cantidad=otros))
            # If we have items to create (either from posted values or from fallback), persist them
            if new_items:
                created = CTZItem.objects.bulk_create(new_items)
                # Recalcular totales basados en lo que acabamos de crear + base
                try:
                    # compute sums directly from the created/new_items to avoid cached relation issues
                    prov_sum = sum(i.cantidad for i in new_items if i.tipo == 'proveedor')
                    mo_sum = sum(i.cantidad for i in new_items if i.tipo == 'mo_soma')
                    otros_sum = sum(i.cantidad for i in new_items if i.tipo == 'otros_materiales')
                    # If the new items were created from posted extra items, they are extras
                    # and we must add them to the base fields. If they were created as a
                    # fallback from the base fields (no posted extras), prov_sum already
                    # contains the base values so we must NOT add the base again (avoid double count).
                    has_posted_items = bool(prov_items or mo_items or otros_items)
                    if has_posted_items:
                        base_prov = int(obj.proveedor or 0)
                        base_mo = int(obj.mo_soma or 0)
                        base_otros = int(obj.otros_materiales or 0)
                    else:
                        base_prov = base_mo = base_otros = 0
                    # Build the desired values without calling obj.save() which would
                    # trigger CTZ.save and recompute pu based on current DB state
                    new_pu = base_prov + prov_sum + base_mo + mo_sum + base_otros + otros_sum
                    new_total = obj.calcular_total_pu(new_pu)
                    # Prepare atomic update: set pu/total_pu and optionally zero base fields
                    update_kwargs = {'pu': new_pu, 'total_pu': new_total}
                    if not has_posted_items:
                        # Clear base fields so display helpers won't sum them again
                        if getattr(obj, 'proveedor', 0):
                            update_kwargs['proveedor'] = 0
                        if getattr(obj, 'mo_soma', 0):
                            update_kwargs['mo_soma'] = 0
                        if getattr(obj, 'otros_materiales', 0):
                            update_kwargs['otros_materiales'] = 0
                    # Use QuerySet.update to avoid model save() side-effects
                    CTZ.objects.filter(pk=obj.pk).update(**update_kwargs)
                    # Refresh object from DB so subsequent logic has current values
                    obj.refresh_from_db()
                except Exception:
                    try:
                        obj.pu = obj.calcular_pu()
                        obj.total_pu = obj.calcular_total_pu(obj.pu)
                        obj.save(update_fields=['pu', 'total_pu'])
                    except Exception:
                        pass
                except Exception:
                    try:
                        obj.pu = obj.calcular_pu()
                        obj.total_pu = obj.calcular_total_pu(obj.pu)
                        obj.save(update_fields=['pu', 'total_pu'])
                    except Exception:
                        pass
                # (diagnostics removed)
        except Exception:
            # No queremos romper la operación de guardado del admin por errores
            # en la sincronización de items; loguear sería ideal.
            pass

    class Media:
        js = ('js/ctz_admin.js',)
        css = {
            'all': ('css/ctz_admin_hide_items.css',)
        }


    # Formateo para la vista de lista: mostrar signos de moneda y porcentaje
    def _fmt_money(self, v):
        try:
            # Use a non-breaking space between the currency symbol and the amount
            # so browsers won't wrap the sign and the number onto separate lines.
            return f"$\u00A0{int(v):,}"
        except Exception:
            return f"$\u00A0{v}"

    def proveedor_display(self, obj):
        # Mostrar suma de items si existen, sino el campo antiguo
        try:
            # Mostrar la suma del campo base más los items asociados
            from django.db.models import Sum
            base = int(obj.proveedor or 0)
            extras_agg = obj.items.filter(tipo='proveedor').aggregate(s=Sum('cantidad')) if hasattr(obj, 'items') else {'s': 0}
            extras = int(extras_agg.get('s') or 0)
            v = base + extras
            return self._fmt_money(v)
        except Exception:
            pass
        return self._fmt_money(obj.proveedor)
    proveedor_display.short_description = 'Proveedor'
    proveedor_display.admin_order_field = 'proveedor'

    def mo_soma_display(self, obj):
        try:
            from django.db.models import Sum
            base = int(obj.mo_soma or 0)
            extras_agg = obj.items.filter(tipo='mo_soma').aggregate(s=Sum('cantidad')) if hasattr(obj, 'items') else {'s': 0}
            extras = int(extras_agg.get('s') or 0)
            v = base + extras
            return self._fmt_money(v)
        except Exception:
            pass
        return self._fmt_money(obj.mo_soma)
    mo_soma_display.short_description = 'MO SOMA'
    mo_soma_display.admin_order_field = 'mo_soma'

    def otros_materiales_display(self, obj):
        try:
            from django.db.models import Sum
            base = int(obj.otros_materiales or 0)
            extras_agg = obj.items.filter(tipo='otros_materiales').aggregate(s=Sum('cantidad')) if hasattr(obj, 'items') else {'s': 0}
            extras = int(extras_agg.get('s') or 0)
            v = base + extras
            return self._fmt_money(v)
        except Exception:
            pass
        return self._fmt_money(obj.otros_materiales)
    otros_materiales_display.short_description = 'Otros materiales'
    otros_materiales_display.admin_order_field = 'otros_materiales'

    def pu_display(self, obj):
        return self._fmt_money(obj.pu)
    pu_display.short_description = 'PU'
    pu_display.admin_order_field = 'pu'

    def total_pu_display(self, obj):
        return self._fmt_money(obj.total_pu)
    total_pu_display.short_description = 'TOTAL PU'
    total_pu_display.admin_order_field = 'total_pu'

    def porcentaje_pu_display(self, obj):
        try:
            # Mostrar el valor tal cual seguido de % (ej. 1.25%)
            s = format(obj.porcentaje_pu, 'f')
            # quitar ceros innecesarios
            s = s.rstrip('0').rstrip('.') if '.' in s else s
            return f"{s}%"
        except Exception:
            return f"{obj.porcentaje_pu}%"
    porcentaje_pu_display.short_description = 'Porcentaje PU'
    porcentaje_pu_display.admin_order_field = 'porcentaje_pu'


class CTZItemInline(admin.TabularInline):
    model = CTZItem
    extra = 1
    fields = ('tipo', 'descripcion', 'cantidad')
    verbose_name = 'Ítem CTZ'
    verbose_name_plural = 'Ítems CTZ'

# Insertar el inline en CTZAdmin (después de la clase para mantener orden de archivo)


class CTZFormatoAdmin(admin.ModelAdmin):
    form = CTZFormatoForm
    """Admin para CTZFormato: permite seleccionar CTZ y copia/consulta total_pu via AJAX.
    Además calcula los campos `subtotal`, `iva` y `total` en el cliente para mostrarlos como readonly.
    """
    # Mostrar sólo campos relevantes en el changelist; los campos por-CTZ
    # (cantidad, unidad, pu) se manejan dinámicamente y no aparecen aquí.
    list_display = ('partida', 'concepto', 'ctzs_breakdown', 'subtotal', 'iva', 'total', 'export_pdf_link')
    list_filter = ('ctzs',)
    # Mostrar selector horizontal para la M2M `ctzs` para que sea más usable
    # en el admin (dos columnas con botones Agregar/Quitar).
    filter_horizontal = ('ctzs',)
    search_fields = ('partida', 'concepto')
    # Usamos el ModelForm para renderizar subtotal/iva/total como inputs readonly
    # Usar solo el campo M2M `ctzs` (ya no usamos el dropdown single `ctz` en el formulario)
    # Mantener sólo los campos necesarios en el formulario principal.
    fields = ('ctzs', 'partida', 'concepto', 'propuesta_redaccion', 'notas_observaciones', 'contacto', 'fecha_manual', 'subtotal', 'iva', 'total')

    def ctzs_breakdown(self, obj):
        """Devuelve una representación HTML con cada CTZ ligada a este formato y sus valores (PU, Cantidad, Total)."""
        try:
            detalles = obj.detalles.select_related('ctz').all()
            if not detalles:
                return '—'
            from decimal import Decimal

            def _fmt_number_trim(v):
                """Format a Decimal/number removing unnecessary trailing zeros.
                Examples: Decimal('2.000') -> '2', Decimal('2.500') -> '2.5'
                """
                try:
                    if v is None:
                        return ''
                    if isinstance(v, Decimal):
                        s = format(v, 'f')
                    else:
                        s = str(v)
                    # remove trailing zeros and trailing dot
                    if '.' in s:
                        s = s.rstrip('0').rstrip('.')
                    return s
                except Exception:
                    return str(v)
            return format_html_join(
                format_html('<br/>'),
                '<a href="{}">{}</a> — {} — {} — PU: {} — Cant: {} — Total: {}',
                ((
                    reverse('admin:empresas_ctz_change', args=(d.ctz.pk,), current_app=self.admin_site.name),
                    getattr(d.ctz, 'id_manual', d.ctz.pk),
                    (d.concepto or '').strip(),
                    (d.unidad or '').strip(),
                    d.pu,
                    _fmt_number_trim(d.cantidad),
                    d.total
                ) for d in detalles)
            )
        except Exception:
            return '—'
    ctzs_breakdown.short_description = 'CTZs (PU / Cant / Total)'

    class Media:
        js = ('js/ctz_formato_admin.js',)

    def get_inline_instances(self, request, obj=None):
        """Ocultar los inlines de detalles cuando se está creando (add) un CTZFormato.

        La vista de creación ya muestra controles dinámicos (JS) para introducir
        las cantidades por CTZ usando el M2M `ctzs` y campos `ctz_qty_<id>`. Si
        además mostramos el inline `CTZFormatoDetalleInline` aparecerán campos
        duplicados en la página de "add". Aquí devolvemos una lista vacía para
        la vista de creación y delegamos al comportamiento por defecto para la
        vista de cambio (cuando `obj` existe).
        """
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def get_urls(self):
        # Añadir una URL propia para consultar el total_pu de una CTZ concreta.
        from django.urls import path
        urls = super().get_urls()
        # Namespaced names so they can be reversed as admin:<app>_<model>_<name>
        my_urls = [
            path('ctz-total-pu/<int:ctz_id>/', self.admin_site.admin_view(self.ctz_total_pu_view), name=f'{self.opts.app_label}_{self.opts.model_name}_ctz_total_pu'),
            path('ctz-detalles/<int:formato_id>/', self.admin_site.admin_view(self.ctz_detalles_view), name=f'{self.opts.app_label}_{self.opts.model_name}_ctz_detalles'),
            path('ctz-contacts/<int:ctz_id>/', self.admin_site.admin_view(self.ctz_contacts_view), name=f'{self.opts.app_label}_{self.opts.model_name}_ctz_contacts'),
            path('export-pdf/<int:pk>/', self.admin_site.admin_view(self.export_pdf_view), name=f'{self.opts.app_label}_{self.opts.model_name}_export_pdf'),
        ]
        return my_urls + urls

    def ctz_total_pu_view(self, request, ctz_id):
        # Devuelve JSON con el total_pu de la CTZ solicitada.
        from django.http import JsonResponse
        from django.shortcuts import get_object_or_404
        try:
            ctz = get_object_or_404(CTZ, pk=ctz_id)
            return JsonResponse({'total_pu': ctz.total_pu})
        except Exception:
            return JsonResponse({'error': 'not found'}, status=404)

    def ctz_detalles_view(self, request, formato_id):
        """Devuelve JSON con los detalles guardados para un CTZFormato (lista de dicts)."""
        from django.http import JsonResponse
        from django.shortcuts import get_object_or_404
        try:
            obj = get_object_or_404(CTZFormato, pk=formato_id)
            from decimal import Decimal

            def _fmt_number_trim(v):
                try:
                    if v is None:
                        return ''
                    if isinstance(v, Decimal):
                        s = format(v, 'f')
                    else:
                        s = str(v)
                    if '.' in s:
                        s = s.rstrip('0').rstrip('.')
                    return s
                except Exception:
                    return str(v)

            detalles = []
            for d in obj.detalles.select_related('ctz').all():
                detalles.append({
                    'ctz_id': d.ctz.pk,
                    'ctz_label': getattr(d.ctz, 'id_manual', d.ctz.pk),
                    'cantidad': _fmt_number_trim(d.cantidad),
                    'pu': _fmt_number_trim(d.pu),
                    'total': _fmt_number_trim(d.total),
                    'concepto': d.concepto or '',
                    'unidad': d.unidad or '',
                })
            return JsonResponse({'detalles': detalles})
        except Exception:
            return JsonResponse({'error': 'not found'}, status=404)

    def ctz_contacts_view(self, request, ctz_id):
        """Devuelve JSON con la lista de contactos de la empresa asociada a la CTZ solicitada."""
        from django.http import JsonResponse
        from django.shortcuts import get_object_or_404
        try:
            ctz = get_object_or_404(CTZ, pk=ctz_id)
            empresa = getattr(ctz, 'empresa', None)
            if not empresa:
                return JsonResponse({'contacts': []})
            contacts = []
            for c in empresa.contactos.all():
                contacts.append({'id': c.pk, 'label': str(c.nombre_completo), 'telefono': c.telefono or '', 'correo': c.correo or ''})
            return JsonResponse({'contacts': contacts})
        except Exception:
            return JsonResponse({'error': 'not found'}, status=404)

    def export_pdf_view(self, request, pk):
        from django.http import HttpResponse
        from django.shortcuts import get_object_or_404
        from django.template.loader import render_to_string
        from django.contrib.staticfiles import finders
        try:
            obj = get_object_or_404(CTZFormato, pk=pk)
            # Determinar nombre de la(s) empresa(s) de las CTZ seleccionadas.
            empresa_name = ''
            try:
                # Intentar extraer nombres únicos de las CTZ relacionadas (detalles)
                detalles_qs = obj.detalles.select_related('ctz__empresa').all()
                nombres = []
                for d in detalles_qs:
                    try:
                        nom = getattr(d.ctz.empresa, 'nombre', None)
                    except Exception:
                        nom = None
                    if nom:
                        nombres.append(str(nom))
                # Si no hay detalles, intentar desde la relación M2M `ctzs`
                if not nombres:
                    for c in obj.ctzs.select_related('empresa').all():
                        try:
                            nom = getattr(c.empresa, 'nombre', None)
                        except Exception:
                            nom = None
                        if nom:
                            nombres.append(str(nom))
                # Unificar y presentar: si todos son iguales, mostrar uno; si hay varios, separarlos por coma.
                nombres_unicas = list(dict.fromkeys(nombres))
                if nombres_unicas:
                    if len(nombres_unicas) == 1:
                        empresa_name = nombres_unicas[0]
                    else:
                        empresa_name = ', '.join(nombres_unicas)
            except Exception:
                empresa_name = ''

            # Determinar nombre del contacto (si existe) para mostrar en el encabezado
            contact_name = ''
            try:
                if getattr(obj, 'contacto', None):
                    try:
                        contact_name = str(obj.contacto.nombre_completo)
                    except Exception:
                        # fallback a nombre + apellidos
                        try:
                            contact_name = f"{getattr(obj.contacto, 'nombre', '')} {getattr(obj.contacto, 'apellidos', '')}".strip()
                        except Exception:
                            contact_name = str(obj.contacto) if obj.contacto else ''
            except Exception:
                contact_name = ''

            html = render_to_string('admin/empresas/ctzformato/pdf.html', {'object': obj, 'empresa_name': empresa_name, 'contact_name': contact_name})
            # Helper: if there's a membretado PDF in static/pdf/membretado.pdf,
            # try to merge it as background onto each page of the generated PDF.
            def _merge_with_membrete(pdf_bytes: bytes) -> bytes:
                try:
                    memb_path = finders.find('pdf/membretado.pdf')
                    if not memb_path:
                        return pdf_bytes
                    import io
                    # We'll shift the content down to avoid overlapping the membretado header.
                    # Aumentado para dejar más espacio entre el encabezado membretado y el contenido.
                    SHIFT = 160  # points to move content down; adjust if needed
                    # Try modern pypdf first
                    try:
                        from pypdf import PdfReader, PdfWriter
                        reader = PdfReader(io.BytesIO(pdf_bytes))
                        bg = PdfReader(open(memb_path, 'rb'))
                        writer = PdfWriter()
                        for i, page in enumerate(reader.pages):
                            # choose corresponding background page or fallback to first
                            bg_page = bg.pages[i] if i < len(bg.pages) else bg.pages[0]
                            # Compute horizontal centering offset between bg and page
                            try:
                                try:
                                    bg_w = float(bg_page.mediabox.width)
                                except Exception:
                                    bg_w = float(bg_page.mediabox.upper_right[0]) - float(bg_page.mediabox.lower_left[0])
                            except Exception:
                                bg_w = None
                            try:
                                try:
                                    src_w = float(page.mediabox.width)
                                except Exception:
                                    src_w = float(page.mediabox.upper_right[0]) - float(page.mediabox.lower_left[0])
                            except Exception:
                                src_w = None
                            x_shift = 0
                            if bg_w is not None and src_w is not None:
                                try:
                                    # Center the generated content horizontally over the background
                                    x_shift = (bg_w - src_w) / 2.0
                                except Exception:
                                    x_shift = 0
                            # Merge content on top of background but translated down and centered
                            try:
                                # merge_translated_page takes (page, tx, ty)
                                bg_page.merge_translated_page(page, x_shift, -SHIFT)
                            except Exception:
                                # fallback: translate source page then merge
                                try:
                                    from pypdf import Transformation
                                    page.add_transformation(Transformation().translate(x_shift, -SHIFT))
                                    bg_page.merge_page(page)
                                except Exception:
                                    try:
                                        bg_page.merge_page(page)
                                    except Exception:
                                        bg_page.mergePage(page)
                            writer.add_page(bg_page)
                        out = io.BytesIO()
                        writer.write(out)
                        return out.getvalue()
                    except Exception:
                        # Try PyPDF2 as fallback
                        try:
                            from PyPDF2 import PdfReader as PR, PdfWriter as PW  # type: ignore[reportMissingImports]
                            reader = PR(io.BytesIO(pdf_bytes))
                            bg = PR(open(memb_path, 'rb'))
                            writer = PW()
                            for i, page in enumerate(reader.pages):
                                bg_page = bg.pages[i] if i < len(bg.pages) else bg.pages[0]
                                # Try to compute widths for centering
                                try:
                                    try:
                                        bg_w = float(bg_page.mediabox.width)
                                    except Exception:
                                        bg_w = float(bg_page.mediabox.upper_right[0]) - float(bg_page.mediabox.lower_left[0])
                                except Exception:
                                    bg_w = None
                                try:
                                    try:
                                        src_w = float(page.mediabox.width)
                                    except Exception:
                                        src_w = float(page.mediabox.upper_right[0]) - float(page.mediabox.lower_left[0])
                                except Exception:
                                    src_w = None
                                x_shift = 0
                                if bg_w is not None and src_w is not None:
                                    try:
                                        x_shift = (bg_w - src_w) / 2.0
                                    except Exception:
                                        x_shift = 0
                                try:
                                    # PyPDF2 historically has mergeTranslatedPage
                                    bg_page.mergeTranslatedPage(page, x_shift, -SHIFT)
                                except Exception:
                                    try:
                                        page.add_transformation(Transformation().translate(x_shift, -SHIFT))
                                        bg_page.merge_page(page)
                                    except Exception:
                                        try:
                                            bg_page.merge_page(page)
                                        except Exception:
                                            bg_page.mergePage(page)
                                writer.add_page(bg_page)
                            out = io.BytesIO()
                            writer.write(out)
                            return out.getvalue()
                        except Exception:
                            return pdf_bytes
                except Exception:
                    return pdf_bytes
            # Intentar generar PDF usando WeasyPrint si está disponible
            try:
                from weasyprint import HTML
            except Exception as e:
                # Mostrar instrucciones útiles si WeasyPrint no está instalado
                install_cmd = (
                    "pip install weasyprint\n"
                    "# En Debian/Ubuntu también: sudo apt install libcairo2 libpango-1.0-0 \\" 
                    "libgdk-pixbuf2.0-0 libffi-dev shared-mime-info"
                )
                hint = (
                    f"<h2>WeasyPrint no está disponible</h2>"
                    f"<p>Para habilitar la descarga en PDF instala WeasyPrint y sus dependencias del sistema.</p>"
                    f"<pre>{install_cmd}</pre>"
                    f"<p>Error detectado: {e}</p>"
                )
                return HttpResponse(hint, content_type='text/html', status=501)

            try:
                # Construir base_url para que WeasyPrint pueda resolver archivos estáticos
                # En producción preferimos usar el path de archivos estáticos (STATIC_ROOT)
                # para que WeasyPrint los lea desde el filesystem. Si no existe
                # STATIC_ROOT, usamos la URL absoluta de STATIC_URL como fallback
                try:
                    if getattr(settings, 'STATIC_ROOT', None):
                        base_url = request.build_absolute_uri(settings.STATIC_URL)
                    else:
                        # request.build_absolute_uri acceptará algo como 'https://domain/static/'
                        base_url = request.build_absolute_uri(getattr(settings, 'STATIC_URL', '/'))
                except Exception:
                    base_url = request.build_absolute_uri('/')

                pdf = HTML(string=html, base_url=base_url).write_pdf()
                try:
                    pdf = _merge_with_membrete(pdf)
                except Exception:
                    pass
                resp = HttpResponse(pdf, content_type='application/pdf')
                resp['Content-Disposition'] = f'attachment; filename="ctzformato_{obj.pk}.pdf"'
                return resp
            except Exception as e:
                # Si WeasyPrint falla (por ejemplo incompatibilidad con pydyf),
                # intentamos usar wkhtmltopdf (pdfkit) si está disponible, lo
                # que suele producir PDFs fieles al HTML/CSS (más parecido al
                # diseño que adjuntaste). Si no hay wkhtmltopdf, caemos al
                # fallback ReportLab ya implementado.
                try:
                    import shutil
                    wk = shutil.which('wkhtmltopdf')
                    if wk:
                        try:
                            import pdfkit
                            config = pdfkit.configuration(wkhtmltopdf=wk)
                            options = {
                                'enable-local-file-access': None,
                                'page-size': 'A4',
                                'encoding': 'UTF-8',
                                # wkhtmltopdf margins adjusted to 10mm (1.0cm)
                                'margin-left': '10mm',
                                'margin-right': '10mm',
                                'margin-top': '10mm',
                                'margin-bottom': '10mm',
                            }
                            pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)
                            if isinstance(pdf_bytes, bytes):
                                try:
                                    pdf_bytes = _merge_with_membrete(pdf_bytes)
                                except Exception:
                                    pass
                                resp = HttpResponse(pdf_bytes, content_type='application/pdf')
                                resp['Content-Disposition'] = f'attachment; filename="ctzformato_{obj.pk}.pdf"'
                                return resp
                        except Exception:
                            # Si pdfkit no está instalado o wkhtmltopdf falla,
                            # pasamos al fallback ReportLab
                            pass
                except Exception:
                    pass

                # Fallback: intentar ReportLab (ya implementado) para asegurar
                # que siempre devolvemos un PDF aunque sea con diseño simple.
                try:
                    from io import BytesIO
                    from reportlab.lib.pagesizes import A4
                    from reportlab.pdfgen import canvas

                    buffer = BytesIO()
                    c = canvas.Canvas(buffer, pagesize=A4)
                    width, height = A4
                    # apply 1.0cm margins (1cm = 28.3464567 points)
                    MARGIN = 1.0 * 28.3464567
                    x = MARGIN
                    y = height - MARGIN
                    c.setFont('Helvetica-Bold', 14)
                    # Mostrar nombre del contacto en lugar de la leyenda 'CTZ Formato'
                    try:
                        contact_name = ''
                        if getattr(obj, 'contacto', None):
                            try:
                                contact_name = str(obj.contacto.nombre_completo)
                            except Exception:
                                contact_name = f"{getattr(obj.contacto, 'nombre', '')} {getattr(obj.contacto, 'apellidos', '')}".strip()
                        if contact_name:
                            c.drawString(x, y, contact_name)
                        else:
                            c.drawString(x, y, f'CTZ Formato #{obj.pk}')
                    except Exception:
                        c.drawString(x, y, f'CTZ Formato #{obj.pk}')
                    # Dibujar Propuesta No. encima de la fecha en la esquina superior derecha
                    try:
                        partida_text = str(getattr(obj, 'partida', '') or '')
                        # line for propuesta (top)
                        fsize = 10
                        c.setFont('Helvetica-Bold', fsize)
                        c.drawRightString(width - MARGIN, y, f'Propuesta No.: {partida_text}')
                        # line for fecha (below propuesta)
                        y_date = y - 12
                        date_obj = getattr(obj, 'fecha_manual', None) or getattr(obj, 'fecha_creacion', None)
                        date_text = ''
                        if date_obj:
                            try:
                                date_text = date_obj.strftime('%d/%m/%Y')
                            except Exception:
                                date_text = str(date_obj)
                        # Draw fecha label and date (date bold)
                        try:
                            # draw date text right-aligned
                            c.setFont('Helvetica-Bold', fsize)
                            c.drawRightString(width - MARGIN, y_date, date_text)
                            # draw label to the left of the date
                            try:
                                from reportlab.pdfbase import pdfmetrics
                                width_date = pdfmetrics.stringWidth(date_text, 'Helvetica-Bold', fsize) if date_text else 0
                            except Exception:
                                width_date = 0
                            c.setFont('Helvetica', fsize)
                            label_x = width - MARGIN - width_date - 6
                            c.drawRightString(label_x, y_date, 'Fecha:')
                        except Exception:
                            # fallback: draw date alone
                            c.setFont('Helvetica', fsize)
                            c.drawRightString(width - MARGIN, y_date, date_text)
                        # advance y so the content below doesn't collide
                        y = y_date - 8
                    except Exception:
                        # if anything fails, leave y as-is (previous decrement will apply)
                        pass
                    # Dibujar la fecha manual en la esquina superior derecha (fallback a fecha_creacion)
                    try:
                        # Mostrar 'Fecha:' y la fecha en la misma fila; la fecha en negritas,
                        # ambos con el mismo tamaño de letra.
                        date_obj = getattr(obj, 'fecha_manual', None) or getattr(obj, 'fecha_creacion', None)
                        date_text = ''
                        if date_obj:
                            try:
                                date_text = date_obj.strftime('%d/%m/%Y')
                            except Exception:
                                date_text = str(date_obj)
                        # Font size to use for both label and date
                        fsize = 10
                        gap = 6
                        # Compute width of date in bold to position label to its left
                        try:
                            from reportlab.pdfbase import pdfmetrics
                            width_date = pdfmetrics.stringWidth(date_text, 'Helvetica-Bold', fsize) if date_text else 0
                        except Exception:
                            width_date = 0
                        # Draw date on the right in bold
                        try:
                            c.setFont('Helvetica-Bold', fsize)
                            c.drawRightString(width - MARGIN, y, date_text)
                        except Exception:
                            c.setFont('Helvetica', fsize)
                            c.drawRightString(width - MARGIN, y, date_text)
                        # Draw label to the left of the date with the same font size but normal weight
                        try:
                            c.setFont('Helvetica', fsize)
                            label_x = width - MARGIN - width_date - gap
                            c.drawRightString(label_x, y, 'Fecha:')
                        except Exception:
                            # ignore label drawing errors
                            pass
                    except Exception:
                        # No bloquear si hay problemas con la fecha
                        pass
                    # Dejar espacio vertical antes del resto del contenido
                    y -= 20
                    # Escribir la frase solicitada y el concepto en negritas en la misma línea
                    try:
                        sentence = 'En atención a su requerimiento, me permito enviarle la propuesta solicitada respecto a: '
                        fsize = 10
                        c.setFont('Helvetica', fsize)
                        c.drawString(x, y, sentence)
                        try:
                            from reportlab.pdfbase import pdfmetrics
                            sent_width = pdfmetrics.stringWidth(sentence, 'Helvetica', fsize)
                        except Exception:
                            sent_width = 0
                        # dibujar concepto en negritas justo después
                        try:
                            c.setFont('Helvetica-Bold', fsize)
                            c.drawString(x + sent_width, y, str(obj.concepto or ''))
                        except Exception:
                            c.setFont('Helvetica', fsize)
                            c.drawString(x + sent_width, y, str(obj.concepto or ''))
                    except Exception:
                        pass
                    y -= 20

                    # Encabezado tabla simple (orden: Partida, Concepto, Cantidad, Unidad, PU, Total)
                    c.setFont('Helvetica-Bold', 9)
                    # Center headers using approx center positions per column
                    try:
                        c.drawCentredString(x+20, y, 'Partida')
                        c.drawCentredString(x+170, y, 'Concepto')
                        c.drawCentredString(x+300, y, 'Cantidad')
                        c.drawCentredString(x+360, y, 'Unidad')
                        c.drawCentredString(x+420, y, 'PU')
                        c.drawCentredString(x+480, y, 'Total')
                    except Exception:
                        # Fallback to drawString if centering methods fail
                        c.drawString(x, y, 'Partida')
                        c.drawString(x+80, y, 'Concepto')
                        c.drawString(x+300, y, 'Cantidad')
                        c.drawString(x+340, y, 'Unidad')
                        c.drawString(x+400, y, 'PU')
                        c.drawString(x+460, y, 'Total')
                    y -= 10
                    c.setFont('Helvetica', 9)
                    for idx, d in enumerate(obj.detalles.select_related('ctz').all(), start=1):
                        if y < 60:
                            c.showPage()
                            y = height - 40
                        # Partida: numeración por fila: 1.00, 2.00, ...
                        try:
                            partida_label = f"{idx:.2f}"
                        except Exception:
                            partida_label = str(idx)
                        c.drawString(x, y, partida_label)
                        c.drawString(x+80, y, (d.concepto or '')[:30])
                        # cantidad (centered)
                        try:
                            c.drawCentredString(x+300, y, str(d.cantidad))
                        except Exception:
                            c.drawString(x+300, y, str(d.cantidad))
                        # unidad (centered)
                        try:
                            c.drawCentredString(x+360, y, (d.unidad or '')[:10])
                        except Exception:
                            c.drawString(x+340, y, (d.unidad or '')[:10])
                        # pu
                        try:
                            c.drawRightString(x+400, y, str(d.pu))
                        except Exception:
                            c.drawString(x+400, y, str(d.pu))
                        # total
                        try:
                            c.drawRightString(x+480, y, str(d.total))
                        except Exception:
                            c.drawString(x+480, y, str(d.total))
                        y -= 10

                    # Totales
                    y -= 10
                    c.setFont('Helvetica-Bold', 10)
                    c.drawRightString(x+480, y, f'Total: {obj.total}')
                    c.showPage()
                    c.save()
                    buffer.seek(0)
                    rl_bytes = buffer.getvalue()
                    try:
                        rl_bytes = _merge_with_membrete(rl_bytes)
                    except Exception:
                        pass
                    resp = HttpResponse(rl_bytes, content_type='application/pdf')
                    resp['Content-Disposition'] = f'attachment; filename="ctzformato_{obj.pk}.pdf"'
                    return resp
                except Exception:
                    # Fallback final: devolver HTML con el error para diagnóstico
                    fallback = f"<h2>Error generando PDF</h2><p>{e}</p>" + html
                    return HttpResponse(fallback, content_type='text/html', status=500)
        except Exception:
            return HttpResponse('No se encontró el CTZ Formato.', status=404)

    def export_pdf_link(self, obj):
        """Enlace para exportar este CTZFormato a PDF."""
        try:
            # Nombre completo del url name en el namespace admin:
            # admin:<app_label>_<model_name>_export_pdf
            url = reverse('admin:%s_%s_export_pdf' % (self.opts.app_label, self.opts.model_name), args=(obj.pk,))
            # small inline SVG icon for PDF (document with PDF text)
            # Usar una imagen SVG externa para evitar problemas de estilos
            # del admin que afectan al SVG inline. El archivo se espera en
            # static/img/pdf-icon.svg (tal como indicó el usuario).
            try:
                from django.templatetags.static import static
                img_url = static('img/pdf-icon.svg')
            except Exception:
                img_url = '/static/img/pdf-icon.svg'

            # Construir el <img> con tamaño controlado y centrarlo en la celda.
            return format_html(
                '<div style="text-align:center; width:100%;"><a href="{}" title="Exportar PDF" style="display:inline-flex;align-items:center;justify-content:center;height:40px;width:40px;margin:0 auto;"><img src="{}" alt="PDF" style="width:32px;height:32px;object-fit:contain;"/></a></div>',
                url,
                img_url,
            )
        except Exception:
            return ''
    export_pdf_link.short_description = 'Exportar'

    def save_model(self, request, obj, form, change):
        """Calcular subtotal/iva/total a partir de las CTZs seleccionadas y las cantidades
        publicadas en campos con nombre 'ctz_qty_<id>'. Luego guardar el objeto y las relaciones m2m.
        """
        # Construir la instancia desde el form (sin guardar todavía) para
        # evitar que `form.save()` sobrescriba los campos que calculemos aquí.
        try:
            instance = form.save(commit=False)
        except Exception:
            # Fallback si algo falla: usar el `obj` pasado por admin
            instance = obj

        try:
            # Calcular subtotal/iva/total a partir de las CTZs seleccionadas
            logger = logging.getLogger(__name__)
            ctz_ids = request.POST.getlist('ctzs') or []
            subtotal = 0.0
            for cid in ctz_ids:
                try:
                    c = CTZ.objects.get(pk=int(cid))
                except Exception:
                    continue
                pu = float(getattr(c, 'total_pu', 0) or 0)
                qty_raw = request.POST.get(f'ctz_qty_{cid}', '')
                try:
                    qty = float(qty_raw.replace(',', '.')) if qty_raw else 0.0
                except Exception:
                    qty = 0.0
                subtotal += pu * qty

            instance.subtotal = round(subtotal, 2)
            instance.iva = round(instance.subtotal * 0.16, 2)
            instance.total = round(instance.subtotal + instance.iva, 2)
            try:
                # Depuración: valores calculados
                logger.debug('CTZFormato calculated subtotal=%s iva=%s total=%s', instance.subtotal, instance.iva, instance.total)
                logger.debug('CTZ ids from POST: %s', ctz_ids)
                # prints además del logger para garantizar salida en runserver
                try:
                    print('DEBUG CTZFormato calculated', instance.subtotal, instance.iva, instance.total)
                    print('DEBUG CTZ ids from POST:', ctz_ids)
                except Exception:
                    pass
                # Logear cantidades enviadas por cada CTZ
                for cid in ctz_ids:
                    try:
                        logger.debug('POST ctz_qty_%s = %s', cid, request.POST.get(f'ctz_qty_{cid}'))
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            # fallback: conservar valores ya presentes en la instancia
            try:
                instance.subtotal = instance.subtotal
                instance.iva = instance.iva
                instance.total = instance.total
            except Exception:
                pass

        # Evitar que el save del modelo recompute y sobrescriba los valores que
        # acabamos de calcular (agregados por CTZs). Marcamos la instancia para
        # que `CTZFormato.save` detecte y salte su recálculo por defecto.
        try:
            instance._skip_recalc = True
        except Exception:
            pass

        # Guardar la instancia (para obtener PK) y luego aplicar save_m2m
        instance.save()
        try:
            if hasattr(form, 'save_m2m'):
                form.save_m2m()
        except Exception:
            pass

        # Persistir detalles por CTZ: leer cantidades publicadas como ctz_qty_<id>
        try:
            from decimal import Decimal
            # eliminar detalles previos
            instance.detalles.all().delete()
            ctz_ids = request.POST.getlist('ctzs') or []
            detalles = []
            for cid in ctz_ids:
                try:
                    c = CTZ.objects.get(pk=int(cid))
                except Exception:
                    continue
                qty_raw = request.POST.get(f'ctz_qty_{cid}', '')
                concept_raw = request.POST.get(f'ctz_concept_{cid}', '')
                unit_raw = request.POST.get(f'ctz_unit_{cid}', '')
                try:
                    qty = Decimal(str(qty_raw).replace(',', '.')) if qty_raw else Decimal('0')
                except Exception:
                    qty = Decimal('0')
                # Usar el total_pu del CTZ como PU por unidad
                try:
                    pu = Decimal(str(getattr(c, 'total_pu', 0)))
                except Exception:
                    pu = Decimal('0')
                total = (qty * pu).quantize(Decimal('0.01'))
                if qty and qty != Decimal('0'):
                    detalles.append(CTZFormatoDetalle(formato=instance, ctz=c, cantidad=qty, pu=pu, total=total, concepto=concept_raw, unidad=unit_raw))
            if detalles:
                CTZFormatoDetalle.objects.bulk_create(detalles)
        except Exception:
            # no queremos romper el guardado por errores en persistencia de detalles
            pass


class CTZFormatoDetalleInline(admin.TabularInline):
    model = CTZFormatoDetalle
    extra = 0
    readonly_fields = ('pu', 'total')
    fields = ('ctz', 'cantidad', 'unidad', 'concepto', 'pu', 'total')
    can_delete = True


# Registrar CTZFormato en admin
admin.site.register(CTZFormato, CTZFormatoAdmin)

# Nota: no registramos el inline para CTZFormato en el admin. La UI dinámica
# construida por `static/js/ctz_formato_admin.js` gestiona la creación/edición
# de los `CTZFormatoDetalle` tanto en add como en change, y persiste via
# `CTZFormatoAdmin.save_model` evitando mostrar el inline adicional.



