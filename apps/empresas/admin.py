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
class ContactoInline(admin.TabularInline):
    model = Contacto
    extra = 1
    fields = ('nombre', 'apellidos', 'telefono', 'correo')
    show_change_link = True



@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
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


