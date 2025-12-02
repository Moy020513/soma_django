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
    observaciones = models.TextField(blank=True)
    
    # Documentación
    tarjeta_circulacion = models.FileField(upload_to='vehiculos/documentos/', null=True, blank=True)

    aseguradora = models.CharField(max_length=100, null=True, blank=True, verbose_name='Nombre de la aseguradora')
    contacto_aseguradora = models.CharField(max_length=30, null=True, blank=True, verbose_name='Número de contacto de la aseguradora')
    numero_seguro = models.CharField(max_length=50, null=True, blank=True, verbose_name='Número de póliza de seguro')
    
    class Meta:
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
    
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placas}"


class VehiculoExterno(models.Model):
    """Vehículos que no pertenecen a la flota pero pueden ser registrados y asignados a empleados.

    Campos mínimos: placas, modelo, numero_seguro (opcional). Se mantiene un estado para saber si
    está asignado o disponible.
    """
    ESTADOS_VEHICULO = [
        ('disponible', 'Disponible'),
        ('asignado', 'Asignado'),
        ('mantenimiento', 'Mantenimiento'),
        ('baja', 'Baja'),
    ]

    placas = models.CharField(max_length=20, unique=True)
    modelo = models.CharField(max_length=100)
    numero_seguro = models.CharField(max_length=100, null=True, blank=True, verbose_name='No. seguro')
    estado = models.CharField(max_length=20, choices=ESTADOS_VEHICULO, default='disponible')
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Vehículo Externo'
        verbose_name_plural = 'Vehículos Externos'

    def __str__(self):
        return f"{self.modelo} - {self.placas}"


class AsignacionVehiculoExterno(models.Model):
    ESTADOS_ASIGNACION = [
        ('activa', 'Activa'),
        ('finalizada', 'Finalizada'),
        ('pendiente', 'Pendiente'),
    ]

    vehiculo_externo = models.ForeignKey(VehiculoExterno, on_delete=models.CASCADE, related_name='asignaciones')
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_asignacion = models.DateField()
    fecha_finalizacion = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_ASIGNACION, default='activa')
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Asignación Vehículo Externo'
        verbose_name_plural = 'Asignaciones Vehículos Externos'

    def __str__(self):
        return f"{self.vehiculo_externo} - {self.empleado}"


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
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    empleado_origen = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='transferencias_origen')
    empleado_destino = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='transferencias_destino')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_transferencia = models.DateTimeField(null=True, blank=True)
    fecha_inspeccion = models.DateTimeField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=30, choices=ESTADOS_TRANSFERENCIA, default='solicitada')
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
    proposito = models.TextField()
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Registro de Uso'
        verbose_name_plural = 'Registros de Uso'
    
    def __str__(self):
        return f"{self.vehiculo} - {self.empleado} - {self.fecha}"


class TenenciaVehicular(models.Model):
    ESTADOS_TENENCIA = [
        ('vigente', 'Vigente'),
        ('vencida', 'Vencida'),
        ('pendiente', 'Pendiente de Pago'),
        ('exenta', 'Exenta'),
    ]
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='tenencias')
    # Mapea a la columna existente 'año' en la base de datos para mantener compatibilidad
    año_fiscal = models.IntegerField(db_column='año')
    fecha_vencimiento = models.DateField()
    fecha_pago = models.DateField(null=True, blank=True)
    # Campo legacy 'pagada' presente en la base de datos en algunas instalaciones.
    # Mapeamoslo aquí para asegurar compatibilidad y evitar errores de integridad.
    pagada = models.BooleanField(default=False, db_column='pagada')
    # monto y folio eliminados
    estado = models.CharField(max_length=20, choices=ESTADOS_TENENCIA, default='pendiente')
    # comprobante_pago: archivo adjunto del pago/recibo de tenencia
    comprobante = models.FileField(upload_to='vehiculos/tenencia/', null=True, blank=True, verbose_name='Comprobante de tenencia')
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Tenencia Vehicular'
        verbose_name_plural = 'Tenencias Vehiculares'
        unique_together = [['vehiculo', 'año_fiscal']]
        ordering = ['-año_fiscal']
    
    def __str__(self):
        return f"Tenencia {self.año_fiscal} - {self.vehiculo}"


class VerificacionVehicular(models.Model):
    TIPOS_VERIFICACION = [
        ('primera', 'Primera Verificación'),
        ('segunda', 'Segunda Verificación'),
        ('extraordinaria', 'Verificación Extraordinaria'),
    ]
    
    ESTADOS_VERIFICACION = [
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('pendiente', 'Pendiente'),
        ('vencida', 'Vencida'),
    ]
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='verificaciones')
    tipo_verificacion = models.CharField(max_length=20, choices=TIPOS_VERIFICACION)
    fecha_verificacion = models.DateField()
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS_VERIFICACION, default='pendiente')
        # número_certificado, centro_verificacion, costo y certificado eliminados
    # Número o folio de verificación (opcional)
    numero_verificacion = models.CharField(max_length=50, null=True, blank=True)
    # Documento adjunto de la verificación (PDF, imagen, etc.)
    documento_verificacion = models.FileField(upload_to='vehiculos/verificaciones/', null=True, blank=True)
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Verificación Vehicular'
        verbose_name_plural = 'Verificaciones Vehiculares'
        ordering = ['-fecha_verificacion']
    
    def __str__(self):
        return f"Verificación {self.get_tipo_verificacion_display()} - {self.vehiculo} ({self.fecha_verificacion.year})"


class GasolinaRequest(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('revisado', 'Revisado'),
        ('rechazado', 'Rechazado'),
        ('parcial', 'Parcialmente comprobado'),
        ('comprobado', 'Comprobante completo'),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, null=True, blank=True)
    vehiculo_externo = models.ForeignKey('VehiculoExterno', on_delete=models.CASCADE, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    # El comprobante ahora es opcional al crear la solicitud. Se sube
    # tras la aprobación/revisión del admin.
    comprobante = models.FileField(upload_to='flota/gasolina/', null=True, blank=True)
    observaciones = models.TextField(blank=True)
    # Monto que el admin ha comprobado del precio solicitado (puede ser parcial)
    monto_comprobado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')

    class Meta:
        verbose_name = 'Solicitud de Gasolina'
        verbose_name_plural = 'Solicitudes de Gasolina'
        ordering = ['-fecha']

    def __str__(self):
        v = self.vehiculo or self.vehiculo_externo
        return f"Solicitud Gasolina {v} - {self.empleado} ({self.fecha.date()})"

    def monto_restante(self):
        """Retorna cuánto falta por comprobar (precio - monto_comprobado). Si no hay monto_comprobado devuelve el precio."""
        try:
            if self.monto_comprobado is None:
                return self.precio
            restante = self.precio - self.monto_comprobado
            if restante < 0:
                return 0
            return restante
        except Exception:
            return self.precio


class GasolinaComprobante(models.Model):
    """Historial de comprobantes subidos para una solicitud de gasolina.

    Cada vez que el empleado sube un comprobante se crea una instancia en este modelo.
    Esto permite mantener un historial y mostrar los comprobantes anteriores en el admin
    y en las notificaciones sin depender de parsing de mensajes.
    """
    gasolina_request = models.ForeignKey(GasolinaRequest, on_delete=models.CASCADE, related_name='comprobantes')
    archivo = models.FileField(upload_to='flota/gasolina/historial/')
    # Nombre original del archivo tal como lo subió el usuario (p.ej. 'CHIDO.jpeg')
    original_name = models.CharField(max_length=255, null=True, blank=True)
    notas = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Comprobante Gasolina'
        verbose_name_plural = 'Comprobantes Gasolina'
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Comprobante {self.gasolina_request_id} - {self.archivo.name.split('/')[-1]}"

    @property
    def url(self):
        try:
            return self.archivo.url
        except Exception:
            return ''

    @property
    def filename(self):
        try:
            # Preferir el nombre original subido por el usuario si está disponible
            if self.original_name:
                return self.original_name
            # sino, devolver sólo el nombre del archivo sin la ruta
            return self.archivo.name.split('/')[-1]
        except Exception:
            return ''