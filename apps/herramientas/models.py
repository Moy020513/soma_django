from django.db import models
from apps.recursos_humanos.models import Empleado

class CategoriaHerramienta(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Categoría de Herramienta'
        verbose_name_plural = 'Categorías de Herramientas'
    
    def __str__(self):
        return self.nombre

class Herramienta(models.Model):
    ESTADOS_HERRAMIENTA = [
        ('disponible', 'Disponible'),
        ('asignada', 'Asignada'),
        ('mantenimiento', 'Mantenimiento'),
        ('baja', 'Baja'),
    ]
    
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaHerramienta, on_delete=models.CASCADE)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_HERRAMIENTA, default='disponible')
    fecha_adquisicion = models.DateField()
    costo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Herramienta'
        verbose_name_plural = 'Herramientas'
    
    def __str__(self):
        return f"{self.nombre} - {self.modelo}"

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