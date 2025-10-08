from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import AsignacionHerramienta, Herramienta


@receiver(post_save, sender=AsignacionHerramienta)
def actualizar_estado_herramienta_asignacion(sender, instance, created, **kwargs):
    """
    Actualiza el estado de la herramienta cuando se crea o modifica una asignación.
    - Si se crea una asignación activa (sin fecha_devolucion), marca la herramienta como 'asignada'
    - Si se agrega fecha_devolucion, marca la herramienta como 'disponible'
    """
    herramienta = instance.herramienta
    
    # Verificar si hay asignaciones activas para esta herramienta
    asignaciones_activas = AsignacionHerramienta.objects.filter(
        herramienta=herramienta, 
        fecha_devolucion__isnull=True
    ).count()
    
    if asignaciones_activas > 0:
        # Hay al menos una asignación activa, marcar como asignada
        if herramienta.estado != 'asignada':
            herramienta.estado = 'asignada'
            herramienta.save(update_fields=['estado'])
    else:
        # No hay asignaciones activas, marcar como disponible (si no está en mantenimiento o baja)
        if herramienta.estado == 'asignada':
            herramienta.estado = 'disponible'
            herramienta.save(update_fields=['estado'])


@receiver(post_delete, sender=AsignacionHerramienta)
def actualizar_estado_herramienta_eliminacion(sender, instance, **kwargs):
    """
    Actualiza el estado de la herramienta cuando se elimina una asignación.
    """
    herramienta = instance.herramienta
    
    # Verificar si quedan asignaciones activas para esta herramienta
    asignaciones_activas = AsignacionHerramienta.objects.filter(
        herramienta=herramienta, 
        fecha_devolucion__isnull=True
    ).count()
    
    if asignaciones_activas == 0:
        # No hay asignaciones activas, marcar como disponible (si estaba asignada)
        if herramienta.estado == 'asignada':
            herramienta.estado = 'disponible'
            herramienta.save(update_fields=['estado'])