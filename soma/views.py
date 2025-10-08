from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from django.urls import reverse
from django.contrib import admin as djadmin
from apps.recursos_humanos.models import Empleado
from apps.flota_vehicular.models import Vehiculo, TransferenciaVehicular, AsignacionVehiculo
from apps.herramientas.models import Herramienta, AsignacionHerramienta
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
    asignaciones_supervisadas_hoy = []
    asignaciones_supervisadas_pendientes = []
    
    if es_admin:
        # Si es admin, mostrar todas las asignaciones del día sin duplicados
        asignaciones_hoy = list(Asignacion.objects
                               .filter(fecha=timezone.localdate())
                               .select_related('empresa', 'supervisor')
                               .prefetch_related('empleados__usuario')
                               .distinct()
                               .order_by('empresa__nombre', 'id'))
    elif empleado:
        # Si no es admin pero tiene registro de empleado
        # Asignaciones como empleado
        qs_emp = (Asignacion.objects
                  .filter(empleados=empleado)
                  .select_related('empresa', 'supervisor')
                  .order_by('-fecha', '-fecha_creacion'))
        asignaciones_empleado_hoy = list(qs_emp.filter(fecha=timezone.localdate()))
        
        # Asignaciones como supervisor
        qs_sup = (Asignacion.objects
                  .filter(supervisor=empleado)
                  .select_related('empresa', 'supervisor')
                  .prefetch_related('empleados')
                  .order_by('-fecha', '-fecha_creacion'))
        
        # Asignaciones supervisadas de hoy
        asignaciones_supervisadas_hoy = list(qs_sup.filter(fecha=timezone.localdate()))
        
        # Asignaciones supervisadas pendientes de días anteriores (no completadas al 100%)
        asignaciones_supervisadas_pendientes = []
        asignaciones_anteriores = qs_sup.filter(fecha__lt=timezone.localdate())[:10]  # Últimas 10
        for asig in asignaciones_anteriores:
            if asig.porcentaje_completado < 100:
                asignaciones_supervisadas_pendientes.append(asig)
            if len(asignaciones_supervisadas_pendientes) >= 5:  # Máximo 5
                break
        
        # Combinar todas las listas eliminando duplicados por ID
        asignaciones_ids_vistas = set()
        asignaciones_hoy = []
        
        # Priorizar: hoy + pendientes de días anteriores
        todas_asignaciones = asignaciones_empleado_hoy + asignaciones_supervisadas_hoy + asignaciones_supervisadas_pendientes
        
        for asignacion in todas_asignaciones:
            if asignacion.id not in asignaciones_ids_vistas:
                asignaciones_ids_vistas.add(asignacion.id)
                asignaciones_hoy.append(asignacion)
        
        if not asignaciones_hoy:
            # Para recientes también evitar duplicados
            asignaciones_recientes_ids = set()
            asignaciones_recientes = []
            for asignacion in list(qs_emp[:3]) + list(qs_sup[:2]):
                if asignacion.id not in asignaciones_recientes_ids:
                    asignaciones_recientes_ids.add(asignacion.id)
                    asignaciones_recientes.append(asignacion)
    context = {
        'titulo': 'Servicios Industriales SOMA',
        'descripcion': 'Sistema de Gestión Empresarial',
        'es_admin': es_admin,
        'asignaciones_hoy': asignaciones_hoy,
        'asignaciones_recientes': asignaciones_recientes,
        'asignaciones_supervisadas_hoy': asignaciones_supervisadas_hoy if empleado else [],
        'asignaciones_pendientes': asignaciones_supervisadas_pendientes if empleado else [],
        'empleado': empleado,
        'today': timezone.localdate(),
    }
    # app_list ahora se maneja automáticamente por el context processor admin_app_list
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
    asignaciones_supervisadas_hoy = []
    asignaciones_supervisadas_pendientes_perfil = []
    vehiculo_asignado = None
    herramienta_asignada = None
    herramientas_lista = []
    
    if empleado:
        # Asignaciones como empleado
        qs_emp = (Asignacion.objects
                  .filter(empleados=empleado)
                  .select_related('empresa', 'supervisor')
                  .order_by('-fecha', '-fecha_creacion'))
        asignaciones_empleado_hoy = list(qs_emp.filter(fecha=timezone.localdate()))
        
        # Asignaciones como supervisor
        qs_sup = (Asignacion.objects
                  .filter(supervisor=empleado)
                  .select_related('empresa', 'supervisor')
                  .prefetch_related('empleados')
                  .order_by('-fecha', '-fecha_creacion'))
        
        # Asignaciones supervisadas de hoy
        asignaciones_supervisadas_hoy = list(qs_sup.filter(fecha=timezone.localdate()))
        
        # Asignaciones supervisadas pendientes de días anteriores (no completadas al 100%)
        asignaciones_supervisadas_pendientes_perfil = []
        asignaciones_anteriores_perfil = qs_sup.filter(fecha__lt=timezone.localdate())[:10]  # Últimas 10
        for asig in asignaciones_anteriores_perfil:
            if asig.porcentaje_completado < 100:
                asignaciones_supervisadas_pendientes_perfil.append(asig)
            if len(asignaciones_supervisadas_pendientes_perfil) >= 5:  # Máximo 5
                break
        
        # Combinar todas las listas eliminando duplicados por ID
        asignaciones_ids_vistas = set()
        asignaciones_hoy = []
        
        # Priorizar: hoy + pendientes de días anteriores
        todas_asignaciones_perfil = asignaciones_empleado_hoy + asignaciones_supervisadas_hoy + asignaciones_supervisadas_pendientes_perfil
        
        for asignacion in todas_asignaciones_perfil:
            if asignacion.id not in asignaciones_ids_vistas:
                asignaciones_ids_vistas.add(asignacion.id)
                asignaciones_hoy.append(asignacion)
        
        if not asignaciones_hoy:
            # Para recientes también evitar duplicados
            asignaciones_recientes_ids = set()
            asignaciones_recientes = []
            for asignacion in list(qs_emp[:3]) + list(qs_sup[:2]):
                if asignacion.id not in asignaciones_recientes_ids:
                    asignaciones_recientes_ids.add(asignacion.id)
                    asignaciones_recientes.append(asignacion)
    elif request.user.is_staff or request.user.is_superuser:
        asignaciones_hoy = (Asignacion.objects
                            .filter(fecha=timezone.localdate())
                            .select_related('empresa', 'supervisor')
                            .prefetch_related('empleados__usuario')
                            .order_by('empleados__numero_empleado'))
    
    # Obtener vehículo asignado activo si el usuario tiene empleado
    if empleado:
        asignacion_vehiculo = AsignacionVehiculo.objects.filter(
            empleado=empleado, 
            estado='activa'
        ).select_related('vehiculo').first()
        if asignacion_vehiculo:
            vehiculo_asignado = asignacion_vehiculo.vehiculo
        # Obtener herramientas asignadas (sin fecha_devolucion)
        asignaciones_herramientas = AsignacionHerramienta.objects.filter(
            empleado=empleado,
            fecha_devolucion__isnull=True
        ).select_related('herramienta').order_by('herramienta__categoria', 'herramienta__codigo')
        
        # Extraer las herramientas de las asignaciones
        herramientas_lista = [asignacion.herramienta for asignacion in asignaciones_herramientas]
        
        # Para compatibilidad con template, usar primera herramienta si solo hay una
        if len(herramientas_lista) == 1:
            herramienta_asignada = herramientas_lista[0]
        elif len(herramientas_lista) > 1:
            # Múltiples herramientas, se manejará en template
            herramienta_asignada = None
    
    context = {
        'titulo': 'Mi Perfil',
        'usuario': request.user,
        'asignaciones_hoy': asignaciones_hoy,
        'asignaciones_recientes': asignaciones_recientes,
        'asignaciones_supervisadas_hoy': asignaciones_supervisadas_hoy if empleado else [],
        'asignaciones_pendientes': asignaciones_supervisadas_pendientes_perfil if empleado else [],
        'empleado': empleado,
        'vehiculo_asignado': vehiculo_asignado,
        'herramienta_asignada': herramienta_asignada,
        'herramientas_asignadas': herramientas_lista if empleado else [],
        'today': timezone.localdate(),
    }
    return render(request, 'perfil_usuario.html', context)


@login_required
def mi_vehiculo(request):
    """Vista dedicada para mostrar el vehículo asignado al usuario"""
    empleado = Empleado.objects.filter(usuario=request.user).first()
    vehiculo_asignado = None
    asignacion_vehiculo = None
    
    if empleado:
        asignacion_vehiculo = AsignacionVehiculo.objects.filter(
            empleado=empleado, 
            estado='activa'
        ).select_related('vehiculo').first()
        
        if asignacion_vehiculo:
            vehiculo_asignado = asignacion_vehiculo.vehiculo
    
    # Si no tiene vehículo asignado, redirigir al perfil
    if not vehiculo_asignado:
        messages.info(request, 'No tienes vehículo asignado actualmente.')
        return redirect('perfil_usuario')
    
    context = {
        'titulo': 'Mi Vehículo',
        'vehiculo': vehiculo_asignado,
        'asignacion': asignacion_vehiculo,
        'empleado': empleado,
    }
    return render(request, 'mi_vehiculo.html', context)


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