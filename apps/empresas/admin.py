from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.utils.translation import gettext as _
from django.template.response import TemplateResponse
import json
from django.contrib.admin.options import IS_POPUP_VAR, TO_FIELD_VAR
from .models import Empresa, Contacto
from .models import CTZ
from .models import CTZItem
from django import forms

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
from django.db.models.deletion import ProtectedError
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
    list_display = ('empresa', 'proveedor_display', 'mo_soma_display', 'otros_materiales_display', 'pu_display', 'porcentaje_pu_display', 'total_pu_display', 'fecha_creacion')
    list_filter = ('empresa',)
    search_fields = ('empresa__nombre',)
    # Mostrar los campos calculados como inputs readonly (no como "readonly_fields")
    # para que puedan actualizarse dinámicamente desde JS en el formulario.
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    fieldsets = (
        (None, {
            'fields': ('empresa',)
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
                    base_prov = int(obj.proveedor or 0)
                    base_mo = int(obj.mo_soma or 0)
                    base_otros = int(obj.otros_materiales or 0)
                    obj.pu = base_prov + prov_sum + base_mo + mo_sum + base_otros + otros_sum
                    obj.total_pu = obj.calcular_total_pu(obj.pu)
                    obj.save(update_fields=['pu', 'total_pu'])
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



