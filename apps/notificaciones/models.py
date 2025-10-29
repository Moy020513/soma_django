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
    tipo = models.CharField(max_length=30, choices=TIPOS_NOTIFICACION, default='info')
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

    @property
    def display_title(self):
        """Return a cleaned title: if this notification was generated as a user response
        like 'Nombre Apellido ha respondido a "Original title"', return 'Respuesta a "Original title"'.
        Otherwise return the original title (possibly truncated by the template)."""
        t = (self.titulo or '')
        # look for quoted section
        first_q = t.find('"')
        if first_q != -1:
            second_q = t.find('"', first_q + 1)
            if second_q != -1:
                inner = t[first_q+1:second_q]
                return f'Respuesta a "{inner}"'
        # fallback: look for pattern 'ha respondido a '
        marker = 'ha respondido a '
        if marker in t:
            try:
                idx = t.index(marker) + len(marker)
                return f'Respuesta a "{t[idx:]}"'
            except Exception:
                pass
        return t

    @property
    def display_user(self):
        """Return a compact username display (username or first+last name fallback)."""
        try:
            # Usuario model may have 'username' or 'email'
            if hasattr(self.usuario, 'username') and self.usuario.username:
                return self.usuario.username
            # Fallback to first + last name or str()
            nombre = getattr(self.usuario, 'first_name', '') or ''
            apellido = getattr(self.usuario, 'last_name', '') or ''
            if nombre or apellido:
                return f"{nombre} {apellido}".strip()
        except Exception:
            pass
        return str(self.usuario)

    @property
    def display_fecha_creacion(self):
        """Return formatted fecha_creacion like 'dd/mm/YYYY HH:MM hrs' using localtime."""
        from django.utils import timezone
        if not self.fecha_creacion:
            return ''
        try:
            local = timezone.localtime(self.fecha_creacion)
            return local.strftime('%d/%m/%Y %H:%M') + ' hrs'
        except Exception:
            return self.fecha_creacion.strftime('%d/%m/%Y %H:%M') + ' hrs'


class RespuestaNotificacion(models.Model):
    notificacion = models.ForeignKey(Notificacion, on_delete=models.CASCADE, related_name='respuestas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    mensaje = models.CharField(max_length=300)
    documento = models.FileField(upload_to='notificaciones/respuestas/', null=True, blank=True)
    fecha_respuesta = models.DateTimeField(auto_now_add=True)
    revisada_admin = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Respuesta a Notificación'
        verbose_name_plural = 'Respuestas a Notificaciones'
        ordering = ['-fecha_respuesta']

    def __str__(self):
        return f"Respuesta de {self.usuario} a {self.notificacion}" 

    # Helpers / display properties