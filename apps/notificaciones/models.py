from django.db import models
from apps.usuarios.models import Usuario

class Notificacion(models.Model):
    TIPOS_NOTIFICACION = [
        ('info', 'Información'),
        ('warning', 'Advertencia'),
        ('success', 'Éxito'),
        ('danger', 'Urgente'),
    ]
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS_NOTIFICACION, default='info')
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    url = models.URLField(blank=True)
    
    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario}"
    
    def marcar_como_leida(self):
        self.leida = True
        self.save()