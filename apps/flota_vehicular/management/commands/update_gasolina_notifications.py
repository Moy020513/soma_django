from django.core.management.base import BaseCommand
from django.urls import reverse
from apps.flota_vehicular.models import GasolinaRequest
from apps.notificaciones.models import Notificacion
from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Actualizar/crear notificaciones de solicitudes de gasolina para que apunten al admin y muestren comprobante'

    def handle(self, *args, **options):
        created = 0
        updated = 0
        admins = list(Usuario.objects.filter(is_staff=True))
        for req in GasolinaRequest.objects.all():
            try:
                admin_url = reverse('admin:flota_vehicular_gasolinarequest_change', args=[req.pk])
            except Exception:
                admin_url = ''

            # Update existing notifications with matching title that lack url
            notis = Notificacion.objects.filter(titulo__icontains='Solicitud de gasolina')
            for n in notis:
                if not n.url:
                    try:
                        n.url = reverse('notificaciones:admin_detalle', args=[n.pk]) + f'?gasolina_id={req.pk}'
                    except Exception:
                        n.url = admin_url
                    n.save()
                    updated += 1

            # Ensure each admin has a notification pointing to this request
            for admin in admins:
                exists = Notificacion.objects.filter(usuario=admin, url=admin_url).exists()
                if not exists:
                    mensaje = f'Solicitud de gasolina de {req.empleado.usuario.get_full_name()} - ${req.precio}. Revisa el comprobante en el admin.'
                    if req.comprobante:
                        # incluir URL absoluta si media disponible
                        try:
                            mensaje += f' Comprobante: {req.comprobante.url}'
                        except Exception:
                            pass
                    noti = Notificacion.objects.create(usuario=admin, titulo='📄 Solicitud de gasolina', mensaje=mensaje, tipo='info', url='')
                    try:
                        noti.url = reverse('notificaciones:admin_detalle', args=[noti.pk]) + f'?gasolina_id={req.pk}'
                        noti.save()
                    except Exception:
                        # fallback a admin change
                        noti.url = admin_url
                        noti.save()
                    created += 1

        self.stdout.write(self.style.SUCCESS(f'Notificaciones creadas: {created}, actualizadas: {updated}'))
