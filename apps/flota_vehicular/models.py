from django.db import models
from apps.recursos_humanos.models import Empleado

class Vehiculo(models.Model):
    TIPOS_VEHICULO = [
        ('sedan', 'Sedán'),
        ('camioneta', 'Camioneta'),
        ('motocicleta', 'Motocicleta'),
        ('camion', 'Camión'),
    ]
    
    ESTADOS_VEHICULO = [
        ('disponible', 'Disponible'),
        ('asignado', 'Asignado'),
        ('mantenimiento', 'Mantenimiento'),
        ('baja', 'Baja'),
    ]
    
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    año = models.IntegerField()
    color = models.CharField(max_length=30)
    placas = models.CharField(max_length=10, unique=True)
    numero_serie = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS_VEHICULO)
    kilometraje_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS_VEHICULO, default='disponible')
    fecha_adquisicion = models.DateField()
    costo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    observaciones = models.TextField(blank=True)
    
    # Documentación
    tarjeta_circulacion = models.FileField(upload_to='vehiculos/documentos/', null=True, blank=True)
    tenencia = models.DateField(null=True, blank=True)
    verificacion_vehicular = models.DateField(null=True, blank=True)
    seguro = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
    
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placas}"

class AsignacionVehiculo(models.Model):
    ESTADOS_ASIGNACION = [
        ('activa', 'Activa'),
        ('finalizada', 'Finalizada'),
        ('pendiente', 'Pendiente'),
    ]
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_asignacion = models.DateField()
    fecha_finalizacion = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_ASIGNACION, default='activa')
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Asignación de Vehículo'
        verbose_name_plural = 'Asignaciones de Vehículos'
    
    def __str__(self):
        return f"{self.vehiculo} - {self.empleado}"

class TransferenciaVehicular(models.Model):
    ESTADOS_TRANSFERENCIA = [
        ('solicitada', 'Solicitada'),
        ('inspeccion', 'En Inspección'),
        ('observaciones', 'Con Observaciones'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('completada', 'Completada'),
    ]
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    empleado_origen = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='transferencias_origen')
    empleado_destino = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='transferencias_destino')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_transferencia = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_TRANSFERENCIA, default='solicitada')
    kilometraje_transferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    observaciones_solicitud = models.TextField(blank=True)
    observaciones_inspeccion = models.TextField(blank=True)
    aprobado_por = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='transferencias_aprobadas')
    
    class Meta:
        verbose_name = 'Transferencia Vehicular'
        verbose_name_plural = 'Transferencias Vehiculares'
    
    def __str__(self):
        return f"Transferencia {self.vehiculo} - {self.empleado_origen} → {self.empleado_destino}"

class RegistroUso(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha = models.DateField()
    kilometraje_inicio = models.DecimalField(max_digits=10, decimal_places=2)
    kilometraje_fin = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    destino = models.CharField(max_length=200)
    proposito = models.TextField()
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Registro de Uso'
        verbose_name_plural = 'Registros de Uso'
    
    def __str__(self):
        return f"{self.vehiculo} - {self.empleado} - {self.fecha}"