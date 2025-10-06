from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.flota_vehicular.models import TransferenciaVehicular


class Command(BaseCommand):
    help = 'Limpia transferencias huérfanas y corrige estados inconsistentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría sin hacer cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios'))
        
        # 1. Buscar transferencias con empleados que ya no existen
        transferencias_sin_empleados = TransferenciaVehicular.objects.filter(
            empleado_origen__isnull=True
        ) | TransferenciaVehicular.objects.filter(
            empleado_destino__isnull=True
        )
        
        if transferencias_sin_empleados.exists():
            self.stdout.write(
                f'Encontradas {transferencias_sin_empleados.count()} transferencias con empleados inexistentes'
            )
            if not dry_run:
                transferencias_sin_empleados.update(
                    estado='cancelada',
                    fecha_respuesta=timezone.now(),
                    observaciones_inspeccion='Cancelada automáticamente: empleado no existe'
                )
                self.stdout.write(self.style.SUCCESS('Transferencias canceladas'))
        
        # 2. Buscar transferencias con vehículos que ya no existen
        transferencias_sin_vehiculos = TransferenciaVehicular.objects.filter(
            vehiculo__isnull=True
        )
        
        if transferencias_sin_vehiculos.exists():
            self.stdout.write(
                f'Encontradas {transferencias_sin_vehiculos.count()} transferencias con vehículos inexistentes'
            )
            if not dry_run:
                transferencias_sin_vehiculos.update(
                    estado='cancelada',
                    fecha_respuesta=timezone.now(),
                    observaciones_inspeccion='Cancelada automáticamente: vehículo no existe'
                )
                self.stdout.write(self.style.SUCCESS('Transferencias canceladas'))
        
        # 3. Buscar transferencias muy antiguas en estado 'solicitada'
        limite_tiempo = timezone.now() - timezone.timedelta(days=30)
        transferencias_antiguas = TransferenciaVehicular.objects.filter(
            estado='solicitada',
            fecha_solicitud__lt=limite_tiempo
        )
        
        if transferencias_antiguas.exists():
            self.stdout.write(
                f'Encontradas {transferencias_antiguas.count()} transferencias antiguas (>30 días)'
            )
            if not dry_run:
                transferencias_antiguas.update(
                    estado='cancelada',
                    fecha_respuesta=timezone.now(),
                    observaciones_inspeccion='Cancelada automáticamente: solicitud expirada (>30 días)'
                )
                self.stdout.write(self.style.SUCCESS('Transferencias expiradas canceladas'))
        
        # 4. Mostrar estadísticas
        total_transferencias = TransferenciaVehicular.objects.count()
        por_estado = {}
        for estado, _ in TransferenciaVehicular.ESTADOS_TRANSFERENCIA:
            count = TransferenciaVehicular.objects.filter(estado=estado).count()
            por_estado[estado] = count
        
        self.stdout.write('\n--- ESTADÍSTICAS ---')
        self.stdout.write(f'Total transferencias: {total_transferencias}')
        for estado, count in por_estado.items():
            self.stdout.write(f'{estado}: {count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nEjecuta sin --dry-run para aplicar los cambios'))
        else:
            self.stdout.write(self.style.SUCCESS('\nLimpieza completada'))