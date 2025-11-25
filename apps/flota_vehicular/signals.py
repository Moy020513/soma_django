from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import GasolinaRequest
from apps.notificaciones.models import Notificacion


@receiver(pre_save, sender=GasolinaRequest)
def gasolina_pre_save(sender, instance, **kwargs):
    """Guardar el estado anterior en la instancia para compararlo en post_save."""
    if not instance.pk:
        instance._old_estado = None
        instance._old_comprobante = None
        return
    try:
        old = GasolinaRequest.objects.get(pk=instance.pk)
        instance._old_estado = old.estado
        # Guardar si antes tenía comprobante (ruta/nombre) para comparar luego
        try:
            instance._old_comprobante = bool(old.comprobante)
        except Exception:
            instance._old_comprobante = False
    except GasolinaRequest.DoesNotExist:
        instance._old_estado = None
        instance._old_comprobante = None


@receiver(post_save, sender=GasolinaRequest)
def gasolina_post_save(sender, instance, created, **kwargs):
    """Enviar notificación al empleado cuando su solicitud cambia a 'revisado' o 'rechazado'.

    Esta señal asume que los administradores cambian el campo `estado` desde el admin u otra interfaz.
    """
    # Sólo nos interesa cambios (no creación)
    if created:
        return

    old = getattr(instance, '_old_estado', None)
    new = instance.estado

    if old == new:
        return

    if new in ('revisado', 'rechazado'):
        usuario = instance.empleado.usuario
        # Usar el mismo texto que usa el admin para evitar notificaciones duplicadas
        titulo = '✅ Solicitud de gasolina aprobada' if new == 'revisado' else '❌ Solicitud de gasolina rechazada'
        mensaje = ''
        if new == 'revisado':
            mensaje = f'Tu solicitud de gasolina por {instance.precio} MXN ha sido aceptada por un administrador. Por favor, sube el comprobante desde la sección de gasolina.'
        else:
            mensaje = f'Tu solicitud de gasolina por {instance.precio} MXN ha sido revisada y fue rechazada. Por favor, sube el comprobante o revisa las observaciones.'

        url = ''
        try:
            # Intentar construir una URL hacia la vista de subida de comprobante
            url = reverse('flota:subir_comprobante_gasolina', args=[instance.pk])
        except Exception:
            url = ''

        # Evitar crear notificación si ya existe (posibles rutas que ya la crearon desde admin)
        if not Notificacion.objects.filter(usuario=usuario, titulo=titulo, url=url).exists():
            Notificacion.objects.create(
                usuario=usuario,
                titulo=titulo,
                mensaje=mensaje,
                tipo='success' if new == 'revisado' else 'danger',
                url=url
            )

    # Detectar subida de comprobante: si antes no había comprobante y ahora sí, notificar a admins
    # También cubrir el caso de creación con comprobante
    try:
        old_has = getattr(instance, '_old_comprobante', None)
    except Exception:
        old_has = None

    # Si se creó con comprobante o se actualizó agregando comprobante
    if (created and getattr(instance, 'comprobante', None)) or (not created and not old_has and getattr(instance, 'comprobante', None)):
        try:
            from apps.usuarios.models import Usuario
            admins = Usuario.objects.filter(is_staff=True)
            for admin in admins:
                mensaje_admin = f'El empleado {instance.empleado.usuario.get_full_name()} ha subido un comprobante de gasolina para {instance.vehiculo or instance.vehiculo_externo} por ${instance.precio}.'
                # Incluir enlace público al archivo si está disponible
                try:
                    if instance.comprobante:
                        mensaje_admin += f' Comprobante: {instance.comprobante.url}'
                except Exception:
                    pass

                # Crear notificación y establecer su URL al detalle admin de notificaciones con gasolina_id
                try:
                    noti = Notificacion.objects.create(
                        usuario=admin,
                        titulo='📥 Comprobante de gasolina subido',
                        mensaje=mensaje_admin,
                        tipo='info',
                        url=''
                    )
                    try:
                        noti.url = reverse('notificaciones:admin_detalle', args=[noti.pk]) + f'?gasolina_id={instance.pk}'
                        noti.save()
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass