from django.contrib.admin.models import LogEntry
from apps.recursos_humanos.models import Empleado
from apps.flota_vehicular.models import AsignacionVehiculo
from apps.herramientas.models import AsignacionHerramienta

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


def herramienta_asignada_context(request):
    """Retorna información de herramientas asignadas para el menú: una (herramienta_menu) o varias (herramientas_menu, herramientas_count)."""
    if not request.user.is_authenticated:
        return {}
    try:
        empleado = Empleado.objects.filter(usuario=request.user).first()
        if not empleado:
            return {'herramienta_menu': None, 'herramientas_menu': [], 'herramientas_count': 0}
        asignaciones = (AsignacionHerramienta.objects
                         .filter(empleado=empleado, fecha_devolucion__isnull=True)
                         .select_related('herramienta')
                         .order_by('herramienta__categoria', 'herramienta__codigo'))
        count = asignaciones.count()
        if count == 0:
            return {'herramienta_menu': None, 'herramientas_menu': [], 'herramientas_count': 0}
        if count == 1:
            return {'herramienta_menu': asignaciones[0].herramienta, 'herramientas_menu': [], 'herramientas_count': 1}
        # Múltiples
        return {
            'herramienta_menu': None,
            'herramientas_menu': [a.herramienta for a in asignaciones],
            'herramientas_count': count
        }
    except Exception:
        return {'herramienta_menu': None, 'herramientas_menu': [], 'herramientas_count': 0}

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


def admin_app_list(request):
    """Retorna la lista de aplicaciones del admin para usuarios staff.
    Esto asegura que siempre esté disponible en el sidebar administrativo.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_staff:
        return {}
    
    try:
        from django.contrib import admin as djadmin
        app_list = djadmin.site.get_app_list(request)
        return {'app_list': app_list}
    except Exception:
        return {'app_list': []}
