from django.core.management.base import BaseCommand
from apps.recursos_humanos.models import Empleado, PeriodoEstatusEmpleado

class Command(BaseCommand):
    help = 'Agrega periodo de estatus "activo" a empleados que no lo tienen.'

    def handle(self, *args, **options):
        empleados_actualizados = 0
        for empleado in Empleado.objects.all():
            if not empleado.periodos_estatus.exists():
                PeriodoEstatusEmpleado.objects.create(
                    empleado=empleado,
                    estatus='activo',
                    fecha_inicio=empleado.fecha_ingreso,
                    observaciones='Registro automático para empleados existentes.'
                )
                empleados_actualizados += 1
        self.stdout.write(self.style.SUCCESS(f'Se actualizaron {empleados_actualizados} empleados.'))