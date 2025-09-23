from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.recursos_humanos.models import Empleado
from apps.flota_vehicular.models import Vehiculo, TransferenciaVehicular
from apps.herramientas.models import Herramienta
from apps.notificaciones.models import Notificacion


@login_required
def index(request):
    """Vista principal del sitio"""
    context = {
        'titulo': 'Sistema SOMA',
        'descripcion': 'Sistema de Gestión Empresarial',
        'es_admin': request.user.is_staff or request.user.is_superuser,
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


@login_required
def perfil_usuario(request):
    """Vista del perfil del usuario"""
    context = {
        'titulo': 'Mi Perfil',
        'usuario': request.user,
    }
    return render(request, 'perfil_usuario.html', context)


@login_required
def notificaciones_usuario(request):
    """Vista de notificaciones del usuario"""
    notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    
    context = {
        'titulo': 'Mis Notificaciones',
        'notificaciones': notificaciones,
        'total_no_leidas': notificaciones.filter(leida=False).count(),
    }
    return render(request, 'notificaciones_usuario.html', context)


@login_required
def marcar_notificacion_leida(request, notificacion_id):
    """Marcar una notificación como leída"""
    try:
        notificacion = Notificacion.objects.get(id=notificacion_id, usuario=request.user)
        notificacion.marcar_como_leida()
        messages.success(request, 'Notificación marcada como leída.')
    except Notificacion.DoesNotExist:
        messages.error(request, 'Notificación no encontrada.')
    
    return redirect('notificaciones_usuario')