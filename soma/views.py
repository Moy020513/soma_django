from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.recursos_humanos.models import Empleado
from apps.flota_vehicular.models import Vehiculo, TransferenciaVehicular
from apps.herramientas.models import Herramienta
from apps.notificaciones.models import Notificacion


@login_required
def index(request):
    """Vista principal del sitio - requiere autenticación"""
    context = {
        'titulo': 'Sistema SOMA',
        'descripcion': 'Sistema de Gestión Empresarial',
    }
    return render(request, 'index.html', context)

@login_required
def dashboard(request):
    context = {
        'total_empleados': Empleado.objects.filter(activo=True).count(),
        'total_vehiculos': Vehiculo.objects.count(),
        'total_herramientas': Herramienta.objects.count(),
        'notificaciones_pendientes': Notificacion.objects.filter(
            usuario=request.user, 
            leida=False
        ).count(),
        'notificaciones_recientes': Notificacion.objects.filter(
            usuario=request.user
        ).order_by('-fecha_creacion')[:5],
        'transferencias_pendientes': TransferenciaVehicular.objects.filter(
            estado__in=['solicitada', 'inspeccion']
        )[:5],
    }
    return render(request, 'dashboard.html', context)