from django.db import models, transaction
from apps.recursos_humanos.models import Empleado

# Eliminado el modelo CategoriaHerramienta. Las categorías ahora son choices fijos dentro de Herramienta.

class Herramienta(models.Model):
    ESTADOS_HERRAMIENTA = [
        ('disponible', 'Disponible'),
        ('asignada', 'Asignada'),
        ('mantenimiento', 'Mantenimiento'),
        ('baja', 'Baja'),
    ]

    CATEGORIAS = [
        ('LIM', 'Limpieza'),
        ('JAR', 'Jardinería'),
        ('CON', 'Construcción'),
        ('ELE', 'Electricidad'),
        ('PIN', 'Pintura'),
        ('HER', 'Herrería'),
        ('CAR', 'Carpintería'),
        ('OTR', 'Otros'),
    ]

    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=3, choices=CATEGORIAS)
    marca = models.CharField(max_length=100, blank=True)
    codigo = models.CharField(max_length=20, unique=True, blank=True, help_text="Se genera automáticamente según la categoría")
    estado = models.CharField(max_length=20, choices=ESTADOS_HERRAMIENTA, default='disponible')

    class Meta:
        verbose_name = 'Herramienta'
        verbose_name_plural = 'Herramientas'

    def __str__(self):
        return f"{self.nombre} - {self.marca}" if self.marca else self.nombre

    def _generar_siguiente_codigo(self):
        """Obtiene el siguiente código incremental dentro de la categoría actual."""
        # Bloquea filas relevantes para evitar colisiones concurrentes
        ultimo = (
            Herramienta.objects.select_for_update()
            .filter(categoria=self.categoria, codigo__startswith=self.categoria)
            .order_by('-codigo')
            .values_list('codigo', flat=True)
            .first()
        )
        if ultimo:
            try:
                num_actual = int(ultimo[len(self.categoria):])
            except ValueError:
                num_actual = 0
        else:
            num_actual = 0
        return f"{self.categoria}{num_actual + 1:03d}"

    def save(self, *args, **kwargs):
        # Determinar si la categoría cambió (solo si ya existe en BD)
        categoria_cambiada = False
        if self.pk:
            try:
                original = Herramienta.objects.get(pk=self.pk)
                if original.categoria != self.categoria:
                    categoria_cambiada = True
            except Herramienta.DoesNotExist:
                pass

        if (not self.codigo and self.categoria) or (categoria_cambiada and self.categoria):
            with transaction.atomic():
                self.codigo = self._generar_siguiente_codigo()
                super().save(*args, **kwargs)
                return
        super().save(*args, **kwargs)

class AsignacionHerramienta(models.Model):
    herramienta = models.ForeignKey(Herramienta, on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_asignacion = models.DateField()
    fecha_devolucion = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Asignación de Herramienta'
        verbose_name_plural = 'Asignaciones de Herramientas'

    def __str__(self):
        return f"{self.herramienta} - {self.empleado}"