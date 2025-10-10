from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Contacto
from apps.notificaciones.models import Notificacion
from django.contrib.auth import get_user_model

# Notifica al admin si el empleado cumple hoy o en los próximos 30 días
@receiver(post_save, sender=Empleado)
def notificar_cumple_empleado(sender, instance, created, **kwargs):
    fecha = instance.fecha_nacimiento
    if not fecha:
        return
    hoy = timezone.localdate()
    en_30_dias = hoy + timedelta(days=30)
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True, activo=True).first()
    if not admin:
        return
    cumple_hoy = (fecha.month == hoy.month and fecha.day == hoy.day)
    # Genera lista de fechas de cumpleaños en los próximos 30 días
    proximos = [(hoy + timedelta(days=i)) for i in range(1, 31)]
    cumple_prox = any(fecha.month == d.month and fecha.day == d.day for d in proximos)
    from django.urls import reverse
    if cumple_hoy:
        mensaje = f'Empleado: {instance.nombre_completo} ({fecha}) cumple años hoy.'
        notif = Notificacion.objects.create(
            usuario=admin,
            titulo='Cumpleaños de hoy',
            mensaje=mensaje,
            tipo='success'
        )
        notif.url = reverse('notificaciones:detalle_cumpleanos', args=[notif.pk])
        notif.save()
    elif cumple_prox:
        mensaje = f'Empleado: {instance.nombre_completo} ({fecha}) cumple años en los próximos 30 días.'
        notif = Notificacion.objects.create(
            usuario=admin,
            titulo='Cumpleaños próximos',
            mensaje=mensaje,
            tipo='info'
        )
        notif.url = reverse('notificaciones:detalle_cumpleanos', args=[notif.pk])
        notif.save()

# Notifica al admin si el contacto cumple hoy o en los próximos 30 días
@receiver(post_save, sender=Contacto)
def notificar_cumple_contacto(sender, instance, created, **kwargs):
    fecha = instance.fecha_nacimiento
    if not fecha:
        return
    hoy = timezone.localdate()
    en_30_dias = hoy + timedelta(days=30)
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True, activo=True).first()
    if not admin:
        return
    cumple_hoy = (fecha.month == hoy.month and fecha.day == hoy.day)
    proximos = [(hoy + timedelta(days=i)) for i in range(1, 31)]
    cumple_prox = any(fecha.month == d.month and fecha.day == d.day for d in proximos)
    from django.urls import reverse
    if cumple_hoy:
        mensaje = f'Contacto: {instance.nombre_completo} ({fecha}) cumple años hoy.'
        notif = Notificacion.objects.create(
            usuario=admin,
            titulo='Cumpleaños de hoy',
            mensaje=mensaje,
            tipo='success'
        )
        notif.url = reverse('notificaciones:detalle_cumpleanos', args=[notif.pk])
        notif.save()
    elif cumple_prox:
        mensaje = f'Contacto: {instance.nombre_completo} ({fecha}) cumple años en los próximos 30 días.'
        notif = Notificacion.objects.create(
            usuario=admin,
            titulo='Cumpleaños próximos',
            mensaje=mensaje,
            tipo='info'
        )
        notif.url = reverse('notificaciones:detalle_cumpleanos', args=[notif.pk])
        notif.save()
