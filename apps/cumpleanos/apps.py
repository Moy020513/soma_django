from django.apps import AppConfig

class CumpleanosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cumpleanos'
    verbose_name = 'Cumpleaños'

    def ready(self):
        import apps.cumpleanos.signals
