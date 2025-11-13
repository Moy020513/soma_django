from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _
from .models import FraseAdministradores

# Personalizar el sitio admin
admin.site.site_header = "Administración SOMA"
admin.site.site_title = "SOMA Admin"
admin.site.index_title = "Panel de Administración"

# Personalizar nombres de modelos de Django
User._meta.verbose_name = _('Usuario')
User._meta.verbose_name_plural = _('Usuarios')
Group._meta.verbose_name = _('Grupo')
Group._meta.verbose_name_plural = _('Grupos')


@admin.register(FraseAdministradores)
class FraseAdministradoresAdmin(admin.ModelAdmin):
	list_display = ('__str__', 'activo', 'creado_por', 'fecha_creacion')
	list_filter = ('activo', 'fecha_creacion')
	search_fields = ('texto', 'creado_por__username')
	readonly_fields = ('fecha_creacion',)
	fieldsets = (
		(None, {'fields': ('texto', 'activo')}),
		('Meta', {'fields': ('creado_por', 'fecha_creacion')}),
	)
	def save_model(self, request, obj, form, change):
		if not obj.creado_por:
			obj.creado_por = request.user
		super().save_model(request, obj, form, change)
