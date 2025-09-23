from django.contrib.auth.models import AbstractUser
from django.db import models

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    permisos = models.TextField(blank=True)  # JSON de permisos
    
    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
    
    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    TIPOS_USUARIO = [
        ('admin', 'Administrador'),
        ('supervisor', 'Supervisor'),
        ('empleado', 'Empleado'),
    ]
    
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Rol')
    tipo_usuario = models.CharField(max_length=20, choices=TIPOS_USUARIO, default='empleado', verbose_name='Tipo de usuario')
    telefono = models.CharField(max_length=15, blank=True, verbose_name='Teléfono')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.get_full_name()} - {self.username}"
    
    @property
    def es_administrador(self):
        return self.tipo_usuario == 'admin' or self.is_superuser
    
    @property
    def es_supervisor(self):
        return self.tipo_usuario == 'supervisor' or self.es_administrador