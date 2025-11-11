from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime
from apps.ubicaciones.models import create_week_records_for_all


class Command(BaseCommand):
    help = 'Crea registros SemanaLaboralEmpleado para todos los empleados para una semana dada (por defecto semana actual)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--week-start',
            dest='week_start',
            help='Fecha de inicio de la semana (lunes) en formato YYYY-MM-DD. Si no se proporciona, se tomará el lunes de la semana actual.',
        )

    def handle(self, *args, **options):
        week_start = options.get('week_start')
        if week_start:
            try:
                week_start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Formato inválido para --week-start. Usa YYYY-MM-DD')
        else:
            week_start_date = None

        count = create_week_records_for_all(week_start_date=week_start_date)
        self.stdout.write(self.style.SUCCESS(f'Creados {count} registros de semana laboral.'))
