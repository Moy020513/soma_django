from django.contrib.admin.models import LogEntry
from apps.recursos_humanos.models import Empleado
from apps.flota_vehicular.models import AsignacionVehiculo

def vehiculo_asignado_context(request):
    """Retorna el vehículo asignado del usuario autenticado si existe"""
    if not request.user.is_authenticated:
        return {}
    
    try:
        empleado = Empleado.objects.filter(usuario=request.user).first()
        if empleado:
            asignacion_vehiculo = AsignacionVehiculo.objects.filter(
                empleado=empleado, 
                estado='activa'
            ).select_related('vehiculo').first()
            
            if asignacion_vehiculo:
                return {'vehiculo_menu': asignacion_vehiculo.vehiculo}
        
        return {'vehiculo_menu': None}
    except:
        return {'vehiculo_menu': None}

def recent_admin_actions(request):
    """Retorna las últimas 10 acciones del admin para usuarios staff.
    Se usa en el header (modal de Acciones recientes).
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_staff:
        return {}
    entries = (LogEntry.objects.select_related('user', 'content_type')
               .order_by('-action_time')[:10])
    return {
        'recent_admin_actions': entries
    }
