from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Contacto
from apps.notificaciones.models import Notificacion
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Notifica al administrador sobre cumpleaños próximos y de hoy.'

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        en_30_dias = hoy + timedelta(days=30)


        # Empleados que cumplen en los próximos 30 días
        empleados_proximos = Empleado.objects.filter(
            fecha_nacimiento__isnull=False,
            fecha_nacimiento__month__gte=hoy.month,
            fecha_nacimiento__day__gte=hoy.day,
            fecha_nacimiento__month__lte=en_30_dias.month,
            fecha_nacimiento__day__lte=en_30_dias.day
        )
        # Empleados que cumplen hoy
        empleados_hoy = Empleado.objects.filter(
            fecha_nacimiento__isnull=False,
            fecha_nacimiento__month=hoy.month,
            fecha_nacimiento__day=hoy.day
        )
        # Contactos que cumplen en los próximos 30 días
        contactos_proximos = Contacto.objects.filter(
            fecha_nacimiento__isnull=False,
            fecha_nacimiento__month__gte=hoy.month,
            fecha_nacimiento__day__gte=hoy.day,
            fecha_nacimiento__month__lte=en_30_dias.month,
            fecha_nacimiento__day__lte=en_30_dias.day
        )
        # Contactos que cumplen hoy
        contactos_hoy = Contacto.objects.filter(
            fecha_nacimiento__isnull=False,
            fecha_nacimiento__month=hoy.month,
            fecha_nacimiento__day=hoy.day
        )

        User = get_user_model()
        admin = User.objects.filter(es_administrador=True, activo=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR('No se encontró usuario administrador activo.'))
            return

        # Mensaje para próximos 30 días
        mensaje_proximos = 'Cumpleaños próximos (30 días):\n'
        for e in empleados_proximos:
            mensaje_proximos += f'- Empleado: {e.nombre_completo} ({e.fecha_nacimiento})\n'
        for c in contactos_proximos:
            mensaje_proximos += f'- Contacto: {c.nombre_completo} ({c.fecha_nacimiento})\n'
        if empleados_proximos or contactos_proximos:
            Notificacion.objects.create(
                usuario=admin,
                titulo='Cumpleaños próximos',
                mensaje=mensaje_proximos,
                tipo='info'
            )

        # Mensaje para cumpleaños de hoy
        mensaje_hoy = 'Cumpleaños de hoy:\n'
        for e in empleados_hoy:
            mensaje_hoy += f'- Empleado: {e.nombre_completo} ({e.fecha_nacimiento})\n'
        for c in contactos_hoy:
            mensaje_hoy += f'- Contacto: {c.nombre_completo} ({c.fecha_nacimiento})\n'
        if empleados_hoy or contactos_hoy:
            Notificacion.objects.create(
                usuario=admin,
                titulo='Cumpleaños de hoy',
                mensaje=mensaje_hoy,
                tipo='success'
            )

        self.stdout.write(self.style.SUCCESS('Notificaciones de cumpleaños enviadas al administrador.'))
