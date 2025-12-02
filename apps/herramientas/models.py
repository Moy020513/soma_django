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
    LUGARES = [
        ('GDL', 'GDL'),
        ('MEX', 'MEX'),
        ('CDMX', 'CDMX'),
        ('QRO', 'QRO'),
    ]

    nombre = models.CharField(max_length=200)
    TIPOS = [
        ('MAQ', 'Maquinaria'),
        ('EQU', 'Equipo'),
        ('HER', 'Herramienta'),
    ]
    USO_ENERGIA_CHOICES = [
        ('gasolina', 'Gasolina'),
        ('diesel', 'Diésel'),
        ('luz', 'Luz (eléctrico)'),
        ('gas', 'Gas'),
        ('otro', 'Otro'),
    ]
    tipo = models.CharField(max_length=10, choices=TIPOS, default='HER', verbose_name='Tipo')
    categoria = models.CharField(max_length=3, choices=CATEGORIAS)
    lugar_pertenencia = models.CharField(max_length=4, choices=LUGARES, verbose_name='Lugar de pertenencia')
    marca = models.CharField(max_length=100, blank=True)
    uso_energia = models.CharField(max_length=20, choices=USO_ENERGIA_CHOICES, null=True, blank=True, verbose_name='Uso combustible/energía', help_text='Habilitado solo si Tipo = Maquinaria')
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
        prefix = f"{self.lugar_pertenencia}-{self.categoria}-"
        codigos = (
            Herramienta.objects.select_for_update()
            .filter(lugar_pertenencia=self.lugar_pertenencia, categoria=self.categoria, codigo__startswith=prefix)
            .values_list('codigo', flat=True)
        )
        max_num = 0
        for c in codigos:
            try:
                parts = c.split('-')
                num = int(parts[-1])
                if num > max_num:
                    max_num = num
            except Exception:
                continue
        return f"{prefix}{max_num + 1:03d}"

    def save(self, *args, **kwargs):
        # Determinar si la categoría cambió (solo si ya existe en BD)
        categoria_cambiada = False
        if self.pk:
            try:
                original = Herramienta.objects.get(pk=self.pk)
                if original.categoria != self.categoria or original.lugar_pertenencia != getattr(self, 'lugar_pertenencia', None):
                    categoria_cambiada = True
            except Herramienta.DoesNotExist:
                pass

        # Generar código solo si tenemos categoría y lugar de pertenencia
        tiene_lugar = bool(getattr(self, 'lugar_pertenencia', None))
        if (not self.codigo and self.categoria and tiene_lugar) or (categoria_cambiada and self.categoria and tiene_lugar):
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


class TransferenciaHerramienta(models.Model):
    ESTADOS_TRANSFERENCIA = [
        ('solicitada', 'Solicitada'),
        ('inspeccion', 'En Inspección'),
        ('inspeccion_enviada', 'Inspección Enviada'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('cancelada', 'Cancelada'),
    ]

    herramienta = models.ForeignKey(Herramienta, on_delete=models.CASCADE)
    empleado_origen = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='transferencias_herramientas_origen')
    empleado_destino = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='transferencias_herramientas_destino')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    fecha_transferencia = models.DateTimeField(null=True, blank=True)
    fecha_inspeccion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_TRANSFERENCIA, default='solicitada')
    observaciones_solicitud = models.TextField(blank=True)
    observaciones_respuesta = models.TextField(blank=True)
    observaciones_inspeccion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Transferencia de Herramienta'
        verbose_name_plural = 'Transferencias de Herramientas'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f"Transferencia {self.herramienta.codigo} - {self.empleado_origen} → {self.empleado_destino}"


class CombustibleRequest(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('revisado', 'Revisado'),
        ('rechazado', 'Rechazado'),
        ('parcial', 'Parcialmente comprobado'),
        ('comprobado', 'Comprobante completo'),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    herramienta = models.ForeignKey(Herramienta, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    comprobante = models.FileField(upload_to='herramientas/combustible/', null=True, blank=True)
    observaciones = models.TextField(blank=True)
    monto_comprobado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')

    class Meta:
        verbose_name = 'Solicitud de Combustible'
        verbose_name_plural = 'Solicitudes de Combustible'
        ordering = ['-fecha']

    def __str__(self):
        return f"Solicitud Combustible {self.herramienta} - {self.empleado} ({self.fecha.date()})"

    def monto_restante(self):
        try:
            if self.monto_comprobado is None:
                return self.precio
            restante = self.precio - self.monto_comprobado
            if restante < 0:
                return 0
            return restante
        except Exception:
            return self.precio


class CombustibleComprobante(models.Model):
    combustible_request = models.ForeignKey(CombustibleRequest, on_delete=models.CASCADE, related_name='comprobantes')
    archivo = models.FileField(upload_to='herramientas/combustible/historial/')
    original_name = models.CharField(max_length=255, null=True, blank=True)
    notas = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Comprobante Combustible'
        verbose_name_plural = 'Comprobantes Combustible'
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Comprobante Combustible {self.combustible_request_id} - {self.archivo.name.split('/')[-1]}"

    @property
    def filename(self):
        try:
            if self.original_name:
                return self.original_name
            return self.archivo.name.split('/')[-1]
        except Exception:
            return ''