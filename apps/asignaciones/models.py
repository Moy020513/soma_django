from django.db import models
from django.urls import reverse

from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Empresa


class Asignacion(models.Model):
    """Asignación de trabajo diaria para un empleado."""

    fecha = models.DateField(verbose_name="Fecha de asignación")
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asignaciones', verbose_name='Empleado')
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
    completada = models.BooleanField(default=False, verbose_name='Completada')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asignación'
        verbose_name_plural = 'Asignaciones'
        ordering = ['-fecha', 'empleado__numero_empleado']
        indexes = [
            models.Index(fields=['fecha', 'empleado']),
        ]
        unique_together = (
            ('fecha', 'empleado'),
        )

    def __str__(self):
        return f"{self.fecha} - {self.empleado} @ {self.empresa}"

    def get_absolute_url(self):
        return reverse('asignaciones:detalle', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        # Si no se especifica supervisor, intentar obtenerlo
        # 1) desde el jefe directo del empleado
        # 2) desde el puesto superior del empleado (primer empleado activo con ese puesto)
        if self.supervisor is None and self.empleado:
            if self.empleado.jefe_directo_id:
                self.supervisor = self.empleado.jefe_directo
            else:
                puesto_sup = getattr(self.empleado.puesto, 'superior', None)
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
