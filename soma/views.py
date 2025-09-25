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
from django.contrib.admin.models import LogEntry
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.template.loader import render_to_string
from apps.asignaciones.models import Asignacion
from django.utils import timezone


@login_required
def index(request):
    """Vista principal del sitio"""
    es_admin = request.user.is_staff or request.user.is_superuser
    from datetime import date
    from apps.asignaciones.models import Asignacion
    asignaciones_hoy = []
    empleado = Empleado.objects.filter(usuario=request.user).first()
    asignaciones_recientes = []
    if empleado:
        qs_emp = (Asignacion.objects
                  .filter(empleado=empleado)
                  .select_related('empresa', 'supervisor')
                  .order_by('-fecha', '-fecha_creacion'))
        asignaciones_hoy = qs_emp.filter(fecha=timezone.localdate())
        if not asignaciones_hoy.exists():
            asignaciones_recientes = qs_emp[:5]
    elif es_admin:
        # Si es admin sin objeto Empleado propio, mostrar asignaciones del día de todos
        asignaciones_hoy = (Asignacion.objects
                            .filter(fecha=timezone.localdate())
                            .select_related('empresa', 'supervisor', 'empleado__usuario')
                            .order_by('empleado__numero_empleado'))
    context = {
        'titulo': 'Sistema SOMA',
        'descripcion': 'Sistema de Gestión Empresarial',
        'es_admin': es_admin,
    'asignaciones_hoy': asignaciones_hoy,
    'asignaciones_recientes': asignaciones_recientes,
        'empleado': empleado,
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
    asignaciones_hoy = []
    empleado = Empleado.objects.filter(usuario=request.user).first()
    asignaciones_recientes = []
    if empleado:
        qs_emp = (Asignacion.objects
                  .filter(empleado=empleado)
                  .select_related('empresa', 'supervisor')
                  .order_by('-fecha', '-fecha_creacion'))
        asignaciones_hoy = qs_emp.filter(fecha=timezone.localdate())
        if not asignaciones_hoy.exists():
            asignaciones_recientes = qs_emp[:5]
    elif request.user.is_staff or request.user.is_superuser:
        asignaciones_hoy = (Asignacion.objects
                            .filter(fecha=timezone.localdate())
                            .select_related('empresa', 'supervisor', 'empleado__usuario')
                            .order_by('empleado__numero_empleado'))
    context = {
        'titulo': 'Mi Perfil',
        'usuario': request.user,
    'asignaciones_hoy': asignaciones_hoy,
    'asignaciones_recientes': asignaciones_recientes,
        'empleado': empleado,
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


@login_required
def api_conteo_notificaciones(request):
    """Devuelve JSON con el conteo de notificaciones no leídas (para polling ligero)."""
    count = Notificacion.objects.filter(usuario=request.user, leida=False).count()
    return JsonResponse({'pendientes': count})


@login_required
def dropdown_notificaciones(request):
    """Devuelve un fragmento HTML (HTMX) con las últimas notificaciones para el dropdown rápido."""
    ultimas = (Notificacion.objects
               .filter(usuario=request.user)
               .order_by('-fecha_creacion')[:5])
    html = render_to_string(
        'partials/_notificaciones_dropdown.html',
        {
            'notificaciones': ultimas,
            'pendientes': Notificacion.objects.filter(usuario=request.user, leida=False).count(),
        },
        request=request
    )
    return HttpResponse(html)


@login_required
def api_marcar_notificacion_leida(request, notificacion_id):
    """Marca una notificación como leída vía AJAX (POST)."""
    if request.method != 'POST':
        return HttpResponseBadRequest('Método no permitido')
    try:
        notif = Notificacion.objects.get(id=notificacion_id, usuario=request.user)
        if not notif.leida:
            notif.leida = True
            notif.save(update_fields=['leida'])
        pendientes = Notificacion.objects.filter(usuario=request.user, leida=False).count()
        return JsonResponse({'ok': True, 'pendientes': pendientes, 'id': notif.id})
    except Notificacion.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No encontrada'}, status=404)


@login_required
def acciones_recientes(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, 'No tienes permisos para ver esta página.')
        return redirect('home')
    acciones = (LogEntry.objects.select_related('user', 'content_type')
                .order_by('-action_time')[:50])
    context = {
        'titulo': 'Acciones recientes',
        'acciones': acciones,
    }
    return render(request, 'acciones_recientes.html', context)