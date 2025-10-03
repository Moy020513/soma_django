from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.flota_vehicular.models import TransferenciaVehicular, AsignacionVehiculo
from apps.notificaciones.models import Notificacion


class Command(BaseCommand):
    help = 'Cancela transferencias huérfanas (de vehículos que ya no están asignados al empleado origen)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué transferencias se cancelarían, sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Buscar transferencias pendientes/en inspección
        transferencias_activas = TransferenciaVehicular.objects.filter(
            estado__in=['solicitada', 'inspeccion']
        ).select_related('empleado_origen', 'empleado_destino', 'vehiculo')
        
        transferencias_a_cancelar = []
        
        for transferencia in transferencias_activas:
            # Verificar si el empleado origen aún tiene asignado el vehículo
            asignacion_activa = AsignacionVehiculo.objects.filter(
                empleado=transferencia.empleado_origen,
                vehiculo=transferencia.vehiculo,
                estado='activa'
            ).exists()
            
            if not asignacion_activa:
                transferencias_a_cancelar.append(transferencia)
        
        if not transferencias_a_cancelar:
            self.stdout.write(
                self.style.SUCCESS('✅ No se encontraron transferencias huérfanas.')
            )
            return
        
        self.stdout.write(
            f'🔍 Se encontraron {len(transferencias_a_cancelar)} transferencias huérfanas:'
        )
        
        for transferencia in transferencias_a_cancelar:
            self.stdout.write(
                f'   • ID {transferencia.pk}: {transferencia.vehiculo} '
                f'({transferencia.empleado_origen} → {transferencia.empleado_destino}) '
                f'[{transferencia.get_estado_display()}]'
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  Modo dry-run: No se realizaron cambios reales.')
            )
            return
        
        # Cancelar las transferencias huérfanas
        canceladas = 0
        notificaciones_enviadas = 0
        
        for transferencia in transferencias_a_cancelar:
            # Actualizar la transferencia
            transferencia.estado = 'cancelada'
            transferencia.fecha_respuesta = timezone.now()
            transferencia.observaciones_inspeccion = (
                'Cancelada automáticamente: el vehículo fue reasignado a otro empleado.'
            )
            transferencia.save()
            canceladas += 1
            
            # Crear notificación para el empleado destino
            try:
                Notificacion.objects.create(
                    usuario=transferencia.empleado_destino.usuario,
                    titulo='Transferencia cancelada',
                    mensaje=f'La transferencia del vehículo {transferencia.vehiculo} ha sido cancelada porque fue reasignado.',
                    tipo='warning',
                    url='/flota/transferencias/'
                )
                notificaciones_enviadas += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error al enviar notificación: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Proceso completado: '
                f'{canceladas} transferencias canceladas, '
                f'{notificaciones_enviadas} notificaciones enviadas.'
            )
        )