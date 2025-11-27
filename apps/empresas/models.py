from django.db import models
from django.urls import reverse
from django.core.validators import RegexValidator
from django.db.models import SET_NULL


class Empresa(models.Model):
    """Modelo para representar una empresa o corporativo"""
    
    nombre = models.CharField(max_length=200, verbose_name="Empresa")
    
    direccion = models.TextField(verbose_name="Dirección")
    logo = models.ImageField(upload_to='empresas/logos/', blank=True, null=True, verbose_name="Logo")
    activa = models.BooleanField(default=True, verbose_name="ACTIVA")
    
    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
    
    def get_absolute_url(self):
        return reverse('empresas:detalle', kwargs={'pk': self.pk})

class Contacto(models.Model):
    """Contacto asociado a una empresa"""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='contactos', verbose_name='Empresa')
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    apellidos = models.CharField(max_length=200, verbose_name='Apellidos', blank=True)
    telefono = models.CharField(
        max_length=10,
        verbose_name='Teléfono',
        blank=True,
        validators=[RegexValidator(r'^\d{10}$', 'El teléfono debe contener exactamente 10 dígitos.')]
    )
    correo = models.EmailField(verbose_name='Correo electrónico', blank=True)
    fecha_nacimiento = models.DateField(verbose_name='Fecha de nacimiento', blank=True, null=True)

    class Meta:
        verbose_name = 'Contacto'
        verbose_name_plural = 'Contactos'
        ordering = ['nombre', 'apellidos']

    def __str__(self):
        full = f"{self.nombre} {self.apellidos}".strip()
        return full or self.nombre

    @property
    def nombre_completo(self):
        return (f"{self.nombre} {self.apellidos}").strip()


class CTZ(models.Model):
    """Formato SOMA: CTZ (cotización simplificada)

    Campos:
      - empresa: FK a Empresa
      - proveedor: costo del proveedor (int)
      - mo_soma: mano de obra SOMA (int)
      - otros_materiales: otros materiales (int)
      - porcentaje_pu: multiplicador para calcular TOTAL_PU (decimal), p.ej. 1.25
      - pu: suma de proveedor + mo_soma + otros_materiales (int, calculado)
      - total_pu: pu * porcentaje_pu (int, calculado)
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ctzs')
    proveedor = models.IntegerField(default=0, verbose_name='Proveedor')
    mo_soma = models.IntegerField(default=0, verbose_name='MO SOMA')
    otros_materiales = models.IntegerField(default=0, verbose_name='Otros materiales')
    porcentaje_pu = models.DecimalField(max_digits=6, decimal_places=3, default=1.25, verbose_name='Porcentaje PU')
    # Campos calculados (guardamos como int para facilitar reportes)
    pu = models.IntegerField(default=0, verbose_name='PU')
    total_pu = models.IntegerField(default=0, verbose_name='TOTAL PU')
    # Identificador manual (editable por el usuario). No confundir con la PK automática `id`.
    id_manual = models.CharField(max_length=50, blank=True, null=True, verbose_name='ID')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'CTZ'
        verbose_name_plural = 'CTZs'

    def __str__(self):
        # Mostrar el id manual si existe, sino la PK
        ident = self.id_manual or str(self.pk)
        return f"CTZ {ident} - {self.empresa}"

    def calcular_pu(self):
        try:
            # Calcular PU combinando los campos individuales y cualquier ítem relacionado.
            # Esto asegura que en la lista (y en los cálculos) se refleje la suma total
            # del campo base más los ítems adicionales añadidos por el usuario.
            proveedor_sum = int(self.proveedor or 0)
            mo_sum = int(self.mo_soma or 0)
            otros_sum = int(self.otros_materiales or 0)
            try:
                if self.pk:
                    items = self.items.all()
                    if items.exists():
                        proveedor_sum += int(sum(i.cantidad for i in items.filter(tipo='proveedor')))
                        mo_sum += int(sum(i.cantidad for i in items.filter(tipo='mo_soma')))
                        otros_sum += int(sum(i.cantidad for i in items.filter(tipo='otros_materiales')))
            except Exception:
                # Si algo falla al leer items, seguimos con los valores base
                pass
            pu = proveedor_sum + mo_sum + otros_sum
        except Exception:
            pu = 0
        return pu

    def calcular_total_pu(self, pu_value=None):
        if pu_value is None:
            pu_value = self.calcular_pu()
        try:
            mult = float(self.porcentaje_pu or 1)
            total = int(round(pu_value * mult))
        except Exception:
            total = pu_value
        return total

    def save(self, *args, **kwargs):
        # Recalcular campos antes de guardar
        self.pu = self.calcular_pu()
        self.total_pu = self.calcular_total_pu(self.pu)
        super().save(*args, **kwargs)


class CTZItem(models.Model):
    """Item asociado a una CTZ para permitir múltiples entradas por tipo (proveedor, MO SOMA, otros materiales)."""
    TIPOS = [
        ('proveedor', 'Proveedor'),
        ('mo_soma', 'MO SOMA'),
        ('otros_materiales', 'Otros materiales'),
    ]
    ctz = models.ForeignKey(CTZ, on_delete=models.CASCADE, related_name='items')
    tipo = models.CharField(max_length=30, choices=TIPOS)
    descripcion = models.CharField(max_length=200, blank=True)
    cantidad = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Ítem CTZ'
        verbose_name_plural = 'Ítems CTZ'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cantidad}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Al guardar un item, forzar recálculo de su CTZ padre
        try:
            self.ctz.pu = self.ctz.calcular_pu()
            self.ctz.total_pu = self.ctz.calcular_total_pu(self.ctz.pu)
            self.ctz.save()
        except Exception:
            pass


class CTZFormato(models.Model):
    """Detalle de formato asociado a una(s) CTZ(s): partidas/conceptos con cantidad, unidad, PU y totales.
    Ahora soporta vincular múltiples CTZs (campo `ctzs`) para permitir ingresar una cantidad distinta
    por cada CTZ y calcular subtotales agregados.
    """
    ctz = models.ForeignKey(CTZ, on_delete=models.CASCADE, related_name='formatos', verbose_name='CTZ', null=True, blank=True)
    # Nuevo: permitir seleccionar múltiples CTZs en el formulario. No sustituye `ctz` para compatibilidad.
    ctzs = models.ManyToManyField(CTZ, blank=True, related_name='formatos_multi', verbose_name='CTZs')
    partida = models.CharField(max_length=100, verbose_name='Partida')
    concepto = models.TextField(verbose_name='Concepto')
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, default=1, verbose_name='Cantidad')
    unidad = models.CharField(max_length=30, verbose_name='Unidad', blank=True)
    pu = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='PU')
    # Antes: `total` (cantidad * pu). Ahora lo llamamos `subtotal` y añadimos IVA y TOTAL.
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Subtotal')
    iva = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='IVA')
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='TOTAL')
    # Fecha manual editable por el usuario (puede dejarse en blanco)
    fecha_manual = models.DateField(blank=True, null=True, verbose_name='Fecha')
    # Texto libre para la redacción propuesta (aprox. media cuartilla). Opcional.
    propuesta_redaccion = models.TextField(blank=True, null=True, verbose_name='Propuesta Redacción')
    # Notas u observaciones adicionales sobre la propuesta. Opcional.
    notas_observaciones = models.TextField(blank=True, null=True, verbose_name='Notas / Observaciones')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    # Contacto relacionado para este formato (opcional). Se ofrece en el admin para
    # seleccionar un contacto perteneciente a la empresa asociada a las CTZs seleccionadas.
    contacto = models.ForeignKey(Contacto, on_delete=SET_NULL, blank=True, null=True, related_name='formatos', verbose_name='Contacto')

    class Meta:
        verbose_name = 'CTZ Formato'
        verbose_name_plural = 'CTZs Formato'

    def __str__(self):
        return f"{self.partida} — {self.concepto[:40]}"

    def save(self, *args, **kwargs):
        # Si la instancia tiene la marca `_skip_recalc`, no recalculamos subtotal/iva/total
        # porque probablemente vinieron calculados externamente (p. ej. desde el admin
        # cuando se manejan múltiples CTZs). Esto permite que el admin asigne valores
        # agregados sin que sean sobrescritos por la lógica por defecto.
        if getattr(self, '_skip_recalc', False):
            return super().save(*args, **kwargs)

        # Si se vinculó una CTZ y no se especificó PU manualmente, usar total_pu de la CTZ
        try:
            if self.ctz and (not self.pu or float(self.pu) == 0):
                # usar total_pu del CTZ como PU por unidad
                self.pu = float(self.ctz.total_pu or 0)
        except Exception:
            pass
        # Calcular subtotal = cantidad * pu
        try:
            self.subtotal = float(self.cantidad or 0) * float(self.pu or 0)
        except Exception:
            self.subtotal = 0
        # Calcular IVA = 16% del subtotal
        try:
            self.iva = round(float(self.subtotal or 0) * 0.16, 2)
        except Exception:
            self.iva = 0
        # Calcular total = subtotal + iva
        try:
            self.total = round(float(self.subtotal or 0) + float(self.iva or 0), 2)
        except Exception:
            self.total = self.subtotal
        super().save(*args, **kwargs)


class CTZFormatoDetalle(models.Model):
    """Detalle por CTZ dentro de un CTZFormato: guarda cantidad, PU y total para
    cada CTZ seleccionada al crear/editar un CTZFormato."""
    formato = models.ForeignKey(CTZFormato, on_delete=models.CASCADE, related_name='detalles')
    ctz = models.ForeignKey(CTZ, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    pu = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Concepto específico para esta CTZ dentro del formato
    concepto = models.TextField(verbose_name='Concepto CTZ', blank=True, default='')
    # Unidad específica para esta CTZ dentro del formato
    unidad = models.CharField(max_length=30, verbose_name='Unidad CTZ', blank=True, default='')

    class Meta:
        verbose_name = 'Detalle CTZ Formato'
        verbose_name_plural = 'Detalles CTZ Formato'

    def __str__(self):
        return f"{self.formato.partida} - {getattr(self.ctz, 'id_manual', self.ctz.pk)}: {self.cantidad} x {self.pu} = {self.total}"

    def save(self, *args, **kwargs):
        try:
            self.total = round(float(self.cantidad or 0) * float(self.pu or 0), 2)
        except Exception:
            self.total = 0
        super().save(*args, **kwargs)


