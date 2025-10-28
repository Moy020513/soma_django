from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.recursos_humanos.models import Empleado
import pytz


class RegistroUbicacion(models.Model):
    """
    Modelo para registrar la ubicación de entrada y salida de empleados
    """
    TIPO_REGISTRO = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ]
    
    empleado = models.ForeignKey(
        Empleado, 
        on_delete=models.CASCADE, 
        related_name='registros_ubicacion',
        verbose_name="Empleado"
    )
    latitud = models.DecimalField(
        max_digits=12, 
        decimal_places=8,
        verbose_name="Latitud",
        help_text="Coordenada de latitud GPS"
    )
    longitud = models.DecimalField(
        max_digits=12, 
        decimal_places=8,
        verbose_name="Longitud", 
        help_text="Coordenada de longitud GPS"
    )
    precision = models.FloatField(
        null=True, 
        blank=True,
        verbose_name="Precisión",
        help_text="Precisión del GPS en metros"
    )
    tipo = models.CharField(
        max_length=10, 
        choices=TIPO_REGISTRO,
        verbose_name="Tipo de registro"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha y hora"
    )
    # Fecha (día) extraída de `timestamp` para permitir constraints por día
    fecha = models.DateField(
        editable=False,
        verbose_name="Fecha"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    
    class Meta:
        verbose_name = "Registro de Ubicación"
        verbose_name_plural = "Registros de Ubicación"
        ordering = ['-timestamp']
        # Índices para mejorar performance
        indexes = [
            models.Index(fields=['empleado', 'tipo', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['fecha']),
        ]
        constraints = [
            # A nivel de base de datos, asegurar único por (empleado, tipo, fecha)
            models.UniqueConstraint(fields=['empleado', 'tipo', 'fecha'], name='unique_registro_per_day'),
        ]
    
    def __str__(self):
        return f"{self.empleado.nombre_completo} - {self.get_tipo_display()} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def fecha_local(self):
        """Convierte el timestamp a zona horaria de México"""
        mexico_tz = pytz.timezone('America/Mexico_City')
        return self.timestamp.astimezone(mexico_tz)
    
    @property
    def coordenadas_str(self):
        """Retorna las coordenadas como string formateado"""
        return f"{self.latitud}, {self.longitud}"
    
    @classmethod
    def ya_registro_hoy(cls, empleado, tipo):
        """Verifica si el empleado ya registró entrada o salida hoy"""
        hoy = timezone.now().date()
        return cls.objects.filter(
            empleado=empleado,
            tipo=tipo,
            fecha=hoy
        ).exists()
    
    @classmethod
    def registros_del_dia(cls, fecha=None):
        """Obtiene todos los registros de un día específico"""
        if fecha is None:
            fecha = timezone.now().date()
        return cls.objects.filter(fecha=fecha)
    
    @classmethod
    def empleados_registrados_hoy(cls, tipo):
        """Obtiene empleados que ya registraron entrada o salida hoy"""
        hoy = timezone.now().date()
        empleados_ids = cls.objects.filter(
            tipo=tipo,
            fecha=hoy
        ).values_list('empleado_id', flat=True)
        return Empleado.objects.filter(id__in=empleados_ids, activo=True)
    
    @classmethod
    def empleados_faltantes_hoy(cls, tipo):
        """Obtiene empleados que NO han registrado entrada o salida hoy"""
        empleados_registrados = cls.empleados_registrados_hoy(tipo)
        return Empleado.objects.filter(activo=True).exclude(
            id__in=empleados_registrados.values_list('id', flat=True)
        )

    def save(self, *args, **kwargs):
        """Asegurarse de tener el campo `fecha` consistente con `timestamp` antes de guardar."""
        # Extraer la fecha desde el timestamp usando la hora local configurada
        # Esto evita que registros cerca de la medianoche queden asignados al día erróneo
        if self.timestamp:
            try:
                # Usa timezone.localtime para convertir a la zona horaria activa en settings
                self.fecha = timezone.localtime(self.timestamp).date()
            except Exception:
                # Fallback simple
                self.fecha = self.timestamp.date()
        else:
            self.fecha = timezone.localtime(timezone.now()).date()
        super().save(*args, **kwargs)