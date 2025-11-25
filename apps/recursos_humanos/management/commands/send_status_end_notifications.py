from django.core.management.base import BaseCommand
from datetime import date
from apps.recursos_humanos.models import PeriodoEstatusEmpleado, notify_status_end_for_today
from apps.usuarios.models import Usuario
from apps.notificaciones.models import Notificacion
import logging
from django.db import models

class Command(BaseCommand):
    help = 'Enviar notificaciones a administradores cuando un periodo de estatus finaliza hoy'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Buscando periodos que finalizan hoy...'))
        created = notify_status_end_for_today()
        self.stdout.write(self.style.SUCCESS(f'Notificaciones creadas: {created}'))
