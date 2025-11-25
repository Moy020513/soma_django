from django.apps import AppConfig


class FlotaVehicularConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.flota_vehicular'
    verbose_name = 'Flota Vehicular'
    
    def ready(self):
        # Importar señales que manejan notificaciones cuando cambia el estado
        try:
            from . import signals  # noqa: F401
        except Exception:
            # No queremos romper el arranque si las señales fallan; se registrará en logs si es necesario
            pass