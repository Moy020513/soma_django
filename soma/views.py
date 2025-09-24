from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from django.urls import reverse
from django.contrib import admin as djadmin
from apps.recursos_humanos.models import Empleado
from apps.flota_vehicular.models import Vehiculo, TransferenciaVehicular
from apps.herramientas.models import Herramienta
from apps.notificaciones.models import Notificacion


@login_required
def index(request):
    """Vista principal del sitio"""
    es_admin = request.user.is_staff or request.user.is_superuser
    context = {
        'titulo': 'Sistema SOMA',
        'descripcion': 'Sistema de Gestión Empresarial',
        'es_admin': es_admin,
    }
    if es_admin:
        # Proveer listado de apps del admin para renderizar en el Home
        context['app_list'] = djadmin.site.get_app_list(request)
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


def admin_login_anyuser(request):
    """
    Login para /admin/login/ que permite autenticar a cualquier usuario activo.
    - Si es staff/superuser: redirige a la Home (index) con el contenido de administrador.
    - Si NO es staff: redirige a la Home (index) con perfil y notificaciones.
    """
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            # Staff o no staff: enviar al Home (index)
            # Desde Home, los administradores tienen accesos directos al Panel de Admin.
            return redirect('home')
    else:
        form = AuthenticationForm(request)

    context = {
        'form': form,
        # app_path es usado por el template de login del admin para el action
        'app_path': request.get_full_path(),
        'next': next_url,
    }
    # Reutilizamos el template personalizado ya existente del admin
    return render(request, 'admin/login.html', context)


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