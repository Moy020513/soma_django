from django.db import models
from django.urls import reverse
from django.core.validators import RegexValidator


class Empresa(models.Model):
    """Modelo para representar una empresa o corporativo"""
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la empresa")
    
    direccion = models.TextField(verbose_name="Dirección")
    logo = models.ImageField(upload_to='empresas/logos/', blank=True, null=True, verbose_name="Logo")
    activa = models.BooleanField(default=True, verbose_name="Empresa activa")
    
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

