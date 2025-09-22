from .models import Notificacion

def notificaciones(request):
    if request.user.is_authenticated:
        return {
            'notificaciones_pendientes': Notificacion.objects.filter(
                usuario=request.user, 
                leida=False
            ).count()
        }
    return {'notificaciones_pendientes': 0}