from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class SomaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'soma'
    verbose_name = _("Administración SOMA")

    def ready(self):
        # Cambiar nombres de apps de Django cuando la app esté lista
        from django.apps import apps

        # Cambiar verbose_name de apps de Django
        try:
            auth_app = apps.get_app_config('auth')
            auth_app.verbose_name = 'Autenticación y Autorización'

            contenttypes_app = apps.get_app_config('contenttypes')
            contenttypes_app.verbose_name = 'Tipos de Contenido'

            sessions_app = apps.get_app_config('sessions')
            sessions_app.verbose_name = 'Sesiones'

            admin_app = apps.get_app_config('admin')
            admin_app.verbose_name = 'Administración'

            messages_app = apps.get_app_config('messages')
            messages_app.verbose_name = 'Mensajes'
        except Exception as e:
            # Si hay algún error, continuar sin cambios
            pass