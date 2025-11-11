from django.apps import AppConfig


class UbicacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ubicaciones'
    verbose_name = 'Ubicaciones'

    def ready(self):
        # Import models to ensure signal handlers are connected
        try:
            import apps.ubicaciones.models  # noqa: F401
        except Exception:
            pass