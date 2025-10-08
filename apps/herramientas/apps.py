from django.apps import AppConfig


class HerramientasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.herramientas'
    verbose_name = 'Herramientas'
    
    def ready(self):
        import apps.herramientas.signals