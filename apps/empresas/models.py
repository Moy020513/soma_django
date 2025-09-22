from django.db import models
from django.core.validators import RegexValidator
from django.urls import reverse


class Empresa(models.Model):
    """Modelo para representar una empresa o corporativo"""
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la empresa")
    razon_social = models.CharField(max_length=200, verbose_name="Razón social")
    rfc = models.CharField(
        max_length=13, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$', 'RFC inválido')],
        verbose_name="RFC"
    )
    direccion = models.TextField(verbose_name="Dirección")
    telefono = models.CharField(max_length=15, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    sitio_web = models.URLField(blank=True, verbose_name="Sitio web")
    logo = models.ImageField(upload_to='empresas/logos/', blank=True, null=True, verbose_name="Logo")
    activa = models.BooleanField(default=True, verbose_name="Empresa activa")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    
    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
    
    def get_absolute_url(self):
        return reverse('empresas:detalle', kwargs={'pk': self.pk})


class Sucursal(models.Model):
    """Modelo para representar sucursales de una empresa"""
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='sucursales')
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la sucursal")
    codigo = models.CharField(max_length=10, verbose_name="Código de sucursal")
    direccion = models.TextField(verbose_name="Dirección")
    telefono = models.CharField(max_length=15, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    gerente = models.CharField(max_length=100, blank=True, verbose_name="Gerente")
    activa = models.BooleanField(default=True, verbose_name="Sucursal activa")
    fecha_apertura = models.DateField(verbose_name="Fecha de apertura")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    
    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['empresa__nombre', 'nombre']
        unique_together = ['empresa', 'codigo']
    
    def __str__(self):
        return f"{self.empresa.nombre} - {self.nombre}"
    
    def get_absolute_url(self):
        return reverse('empresas:sucursal_detalle', kwargs={'pk': self.pk})


class Departamento(models.Model):
    """Modelo para representar departamentos dentro de una sucursal"""
    
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='departamentos')
    nombre = models.CharField(max_length=100, verbose_name="Nombre del departamento")
    codigo = models.CharField(max_length=10, verbose_name="Código del departamento")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    jefe_departamento = models.CharField(max_length=100, blank=True, verbose_name="Jefe de departamento")
    presupuesto_anual = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Presupuesto anual"
    )
    activo = models.BooleanField(default=True, verbose_name="Departamento activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    
    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['sucursal__nombre', 'nombre']
        unique_together = ['sucursal', 'codigo']
    
    def __str__(self):
        return f"{self.sucursal.nombre} - {self.nombre}"
    
    def get_absolute_url(self):
        return reverse('empresas:departamento_detalle', kwargs={'pk': self.pk})
    
    @property
    def empresa(self):
        """Retorna la empresa a la que pertenece este departamento"""
        return self.sucursal.empresa