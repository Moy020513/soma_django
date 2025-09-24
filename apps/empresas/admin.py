from django.contrib import admin
from django.utils.html import format_html
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
    inlines = [ContactoInline]
    list_filter = ['activa']
    search_fields = ['nombre']
    list_editable = ['activa']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre',)
        }),
        ('Contacto', {
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


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'empresa', 'telefono', 'correo')
    list_filter = ('empresa',)
    search_fields = ('nombre', 'apellidos', 'telefono', 'correo', 'empresa__nombre')
    verbose_name = 'Contacto'
    verbose_name_plural = 'Contactos'


