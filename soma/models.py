from django.db import models
from django.conf import settings


class FraseAdministradores(models.Model):
    """Frase global que puede asignar cualquier administrador. Solo una puede estar activa."""
    texto = models.TextField(verbose_name='Frase', help_text='Texto que se mostrará encima del login y en perfiles de empleado')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='frases_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Frase de administradores'
        verbose_name_plural = 'Frases de administradores'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return (self.texto[:75] + '...') if len(self.texto) > 75 else self.texto

    def save(self, *args, **kwargs):
        # Si se marca como activo, desactivar las otras
        super_allowed = True
        if self.activo:
            # desactivar las otras frases activas
            qs = FraseAdministradores.objects.filter(activo=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(activo=False)
        super().save(*args, **kwargs)
