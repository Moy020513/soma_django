from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _

# Personalizar el sitio admin
admin.site.site_header = "Administración SOMA"
admin.site.site_title = "SOMA Admin"
admin.site.index_title = "Panel de Administración"

# Personalizar nombres de modelos de Django
User._meta.verbose_name = _('Usuario')
User._meta.verbose_name_plural = _('Usuarios')
Group._meta.verbose_name = _('Grupo')
Group._meta.verbose_name_plural = _('Grupos')
