from django.db import models
from django.urls import reverse

from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Empresa



class ActividadAsignada(models.Model):
    asignacion = models.ForeignKey('Asignacion', on_delete=models.CASCADE, related_name='actividades')
    nombre = models.CharField(max_length=120, verbose_name='Actividad')
    porcentaje = models.PositiveIntegerField(verbose_name='Porcentaje')
    tiempo_estimado_dias = models.PositiveIntegerField(default=1, verbose_name='Tiempo estimado (días)')
    completada = models.BooleanField(default=False, verbose_name='Completada')
    fecha_completada = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de finalización')
    completada_por = models.ForeignKey(
        'recursos_humanos.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Completada por'
    )

    class Meta:
        verbose_name = 'Actividad asignada'
        verbose_name_plural = 'Actividades asignadas'

    def __str__(self):
        status = "✓" if self.completada else "○"
        dias_texto = f"{self.tiempo_estimado_dias} día{'s' if self.tiempo_estimado_dias != 1 else ''}"
        return f"{status} {self.nombre} ({self.porcentaje}% - {dias_texto})"

class Asignacion(models.Model):
    @property
    def actividades_detalle(self):
        actividades = self.actividades.all()
        if not actividades:
            return []
        return [
            {
                'nombre': a.nombre,
                'porcentaje': a.porcentaje,
                'completada': a.completada,
                'fecha_completada': a.fecha_completada,
                'completada_por': a.completada_por
            } for a in actividades
        ]
    
    @property
    def porcentaje_completado(self):
        actividades = self.actividades.all()
        if not actividades:
            return 0
        total_completado = sum(a.porcentaje for a in actividades if a.completada)
        return total_completado
    
    @property
    def todas_actividades_completadas(self):
        return self.actividades.exists() and not self.actividades.filter(completada=False).exists()
    
    @property
    def actividades_completadas(self):
        """Retorna el número de actividades completadas"""
        return self.actividades.filter(completada=True).count()
    
    @property
    def tiempo_estimado_total(self):
        """Retorna el tiempo total estimado en días para todas las actividades"""
        return self.actividades.aggregate(
            total=models.Sum('tiempo_estimado_dias')
        )['total'] or 0
    
    @property
    def tiempo_estimado_pendiente(self):
        """Retorna el tiempo estimado en días para actividades pendientes"""
        return self.actividades.filter(completada=False).aggregate(
            total=models.Sum('tiempo_estimado_dias')
        )['total'] or 0
    
    @property
    def tiempo_estimado_completado(self):
        """Retorna el tiempo de actividades ya completadas"""
        return self.actividades.filter(completada=True).aggregate(
            total=models.Sum('tiempo_estimado_dias')
        )['total'] or 0
    @property
    def empleado_resumen(self):
        empleados = list(self.empleados.all())
        if not empleados:
            return ''
        primero = empleados[0].nombre_completo if hasattr(empleados[0], 'nombre_completo') else str(empleados[0])
        if len(empleados) == 1:
            return primero
        return f"{primero} + {len(empleados)-1}"
    @property
    def archivo_nombre(self):
        return self.archivos.name.split('/')[-1] if self.archivos else ''

    @property
    def actividades_total(self):
        return self.actividades.count()
    @property
    def empleados_str(self):
        return ', '.join([str(e) for e in self.empleados.all()])
    def get_admin_url(self):
        from django.urls import reverse
        return reverse('admin:asignaciones_asignacion_change', args=[self.pk])
    """Asignación de trabajo diaria para un empleado."""

    fecha = models.DateField(verbose_name="Fecha de asignación")
    empleados = models.ManyToManyField(Empleado, related_name='asignaciones', verbose_name='Empleados')
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='asignaciones', verbose_name='Empresa')
    supervisor = models.ForeignKey(
        Empleado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaciones_supervisadas',
        verbose_name='Supervisor'
    )
    detalles = models.TextField(verbose_name='Detalles de la asignación')
    archivos = models.FileField(upload_to='asignaciones/archivos/', blank=True, null=True, verbose_name='Archivos adjuntos')
    completada = models.BooleanField(default=False, verbose_name='Completada')
    # Campo único para el número de cotización (usar BigIntegerField para
    # representar valores numéricos de cotización). Consolidamos a un solo
    # campo llamado `numero_cotizacion` (numérico) para evitar duplicidad.
    numero_cotizacion = models.BigIntegerField(blank=True, null=True, verbose_name='No. cotización')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asignación'
        verbose_name_plural = 'Asignaciones'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['fecha']),
        ]

    def __str__(self):
        if not self.pk:
            return f"Asignación nueva"
        empleados_str = ', '.join([str(e) for e in self.empleados.all()])
        return f"{self.fecha} - {empleados_str} @ {self.empresa}"

    def get_absolute_url(self):
        return reverse('asignaciones:detalle', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        # Solo ejecutar la lógica de supervisor al crear la asignación
        if self.supervisor is None and not self.pk:
            primer_empleado = self.empleados.first()
            if primer_empleado:
                if primer_empleado.jefe_directo_id:
                    self.supervisor = primer_empleado.jefe_directo
                else:
                    puesto_sup = getattr(primer_empleado.puesto, 'superior', None)
                    if puesto_sup:
                        from apps.recursos_humanos.models import Empleado as Emp
                        cand = (
                            Emp.objects.filter(puesto=puesto_sup, activo=True)
                            .select_related('usuario')
                            .order_by('fecha_ingreso')
                            .first()
                        )
                        if cand:
                            self.supervisor = cand
        super().save(*args, **kwargs)


class HistorialSupervisorAsignacion(models.Model):
    asignacion = models.ForeignKey('Asignacion', on_delete=models.CASCADE, related_name='historial_supervisores')
    supervisor = models.ForeignKey(
        Empleado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Supervisor'
    )
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Historial de Supervisor'
        verbose_name_plural = 'Historial de Supervisores'
        ordering = ['-fecha_inicio']

    def __str__(self):
        sup = self.supervisor.nombre_completo if self.supervisor else 'Sin supervisor'
        return f"{sup} ({self.fecha_inicio.strftime('%d/%m/%Y %H:%M')})"


class HistorialEmpleadoAsignacion(models.Model):
    ACCION_CHOICES = (
        ('agregado', 'Agregado'),
        ('removido', 'Removido'),
    )
    asignacion = models.ForeignKey('Asignacion', on_delete=models.CASCADE, related_name='historial_empleados')
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Empleado'
    )
    accion = models.CharField(max_length=10, choices=ACCION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historial de Empleado'
        verbose_name_plural = 'Historial de Empleados'
        ordering = ['-timestamp']

    def __str__(self):
        emp = self.empleado.nombre_completo if self.empleado else 'Empleado desconocido'
        return f"{emp} - {self.get_accion_display()} @ {self.timestamp.strftime('%d/%m/%Y %H:%M')}"
