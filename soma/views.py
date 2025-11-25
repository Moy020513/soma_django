from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from django.urls import reverse
from django.contrib import admin as djadmin
from apps.recursos_humanos.models import Empleado
from apps.flota_vehicular.models import Vehiculo, TransferenciaVehicular, AsignacionVehiculo
try:
    from apps.flota_vehicular.models import AsignacionVehiculoExterno
except Exception:
    AsignacionVehiculoExterno = None
from apps.herramientas.models import Herramienta, AsignacionHerramienta
from apps.notificaciones.models import Notificacion
from apps.flota_vehicular.forms import RegistroUsoForm
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
    
    estatus_actual = None
    periodo_actual = None
    dias_en_estatus_actual = None
    fecha_ingreso = None
    dias_activo = None
    historial_anual = []
    if empleado:
        from datetime import date, timedelta
        # Usar helper del modelo para determinar el periodo vigente
        periodo_actual = empleado.get_periodo_actual()
        if periodo_actual:
            estatus_actual = periodo_actual.estatus
            inicio = periodo_actual.fecha_inicio
            fin = periodo_actual.fecha_fin or date.today()
            if inicio:
                if periodo_actual.estatus == 'vacaciones':
                    dias = 0
                    temp = inicio
                    while temp <= fin:
                        if temp.weekday() != 6:  # 6 = domingo
                            dias += 1
                        temp += timedelta(days=1)
                    dias_en_estatus_actual = dias
                else:
                    dias_en_estatus_actual = (fin - inicio).days + 1
        else:
            # Mostrar explícitamente "sin estatus" cuando no hay periodo vigente
            estatus_actual = 'sin estatus'
        fecha_ingreso = empleado.fecha_ingreso if empleado and empleado.fecha_ingreso else None
        dias_activo = empleado.dias_trabajados() if empleado else None
        historial_anual = []
        if empleado and empleado.fecha_ingreso:
            from datetime import date, timedelta
            import calendar
            primer = empleado.fecha_ingreso.year
            ultimo = date.today().year
            periodos = empleado.periodos_estatus.filter(estatus="activo")
            for anio in range(primer, ultimo+1):
                dias_unicos = set()
                for periodo in periodos:
                    inicio = periodo.fecha_inicio
                    fin = periodo.fecha_fin or date.today()
                    # Si el periodo cruza el año
                    if inicio.year <= anio <= fin.year:
                        ini = max(inicio, date(anio,1,1))
                        fini = min(fin, date(anio,12,31))
                        if ini <= fini:
                            delta = (fini - ini).days + 1
                            for i in range(delta):
                                dias_unicos.add(ini + timedelta(days=i))
                # Limitar al máximo de días del año
                max_dias = 366 if calendar.isleap(anio) else 365
                dias = min(len(dias_unicos), max_dias)
                historial_anual.append({'anio': anio, 'dias': dias})
    context = {
        'titulo': 'Mi Perfil',
        'usuario': request.user,
        'asignaciones_hoy': asignaciones_hoy,
        'asignaciones_recientes': asignaciones_recientes,
        'asignaciones_supervisadas_hoy': asignaciones_supervisadas_hoy if empleado else [],
        'asignaciones_pendientes': asignaciones_supervisadas_pendientes_perfil if empleado else [],
        'empleado': empleado,
        'estatus_actual': estatus_actual,
        'periodo_actual': periodo_actual,
        'dias_en_estatus_actual': dias_en_estatus_actual,
        'vehiculo_asignado': vehiculo_asignado,
        'herramienta_asignada': herramienta_asignada,
        'herramientas_asignadas': herramientas_lista if empleado else [],
        'today': timezone.localdate(),
        'fecha_ingreso': fecha_ingreso,
        'dias_activo': dias_activo,
        'historial_anual': historial_anual,
        'dias_vacaciones_disponibles': empleado.dias_vacaciones_disponibles() if empleado else None,
        'dias_faltan_para_vacaciones': empleado.dias_faltan_para_vacaciones if empleado else None,
    }
    return render(request, 'perfil_usuario.html', context)


@login_required
def mi_vehiculo(request):
    """Vista dedicada para mostrar el vehículo asignado al usuario"""
    empleado = Empleado.objects.filter(usuario=request.user).first()
    vehiculo_asignado = None
    asignacion_vehiculo = None
    es_externo = False
    
    if empleado:
        asignacion_vehiculo = AsignacionVehiculo.objects.filter(
            empleado=empleado, 
            estado='activa'
        ).select_related('vehiculo').first()
        
        if asignacion_vehiculo:
            vehiculo_asignado = asignacion_vehiculo.vehiculo

        # Si no hay asignación interna, comprobar vehículo externo (si el modelo existe)
        if not vehiculo_asignado and AsignacionVehiculoExterno is not None:
            asign_ext = AsignacionVehiculoExterno.objects.filter(
                empleado=empleado,
                estado='activa'
            ).select_related('vehiculo_externo').first()
            if asign_ext:
                vehiculo_asignado = asign_ext.vehiculo_externo
                asignacion_vehiculo = asign_ext
                es_externo = True
    
    # Si no tiene vehículo asignado, redirigir al perfil
    if not vehiculo_asignado:
        messages.info(request, 'No tienes vehículo asignado actualmente.')
        return redirect('perfil_usuario')

    context = {
        'titulo': 'Mi Vehículo',
        'vehiculo': vehiculo_asignado,
        'asignacion': asignacion_vehiculo,
        'empleado': empleado,
        'es_externo': es_externo,
    }

    # Renderizar plantilla simplificada para vehículos externos
    if es_externo:
        return render(request, 'mi_vehiculo_externo.html', context)

    return render(request, 'mi_vehiculo.html', context)


@login_required
def registrar_km(request):
    """Página separada para mostrar y procesar el formulario de registro de kilometraje."""
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('perfil_usuario')

    asignacion_vehiculo = AsignacionVehiculo.objects.filter(
        empleado=empleado,
        estado='activa'
    ).select_related('vehiculo').first()
    if not asignacion_vehiculo:
        messages.info(request, 'No tienes vehículo asignado actualmente.')
        return redirect('perfil_usuario')

    vehiculo_asignado = asignacion_vehiculo.vehiculo

    from django.utils import timezone as _tz
    initial = {'fecha': _tz.localdate()}
    if getattr(vehiculo_asignado, 'kilometraje_actual', None) is not None:
        initial['kilometraje_fin'] = vehiculo_asignado.kilometraje_actual
    registro_form = RegistroUsoForm(initial=initial)

    if request.method == 'POST':
        registro_form = RegistroUsoForm(request.POST)
        if registro_form.is_valid():
            registro = registro_form.save(commit=False)
            registro.vehiculo = vehiculo_asignado
            registro.empleado = empleado
            # Rellenar kilometraje_inicio con el kilometraje actual del vehículo
            ultimo_km = getattr(vehiculo_asignado, 'kilometraje_actual', None)
            registro.kilometraje_inicio = ultimo_km if ultimo_km is not None else 0

            # Validar que el kilometraje informado no sea menor que el último registrado
            if registro.kilometraje_fin is not None and ultimo_km is not None and registro.kilometraje_fin < ultimo_km:
                # Mostrar sólo un flash en rojo y no añadir error dentro del formulario
                messages.error(request, f'El kilometraje no puede ser menor que el último registrado ({ultimo_km}).', extra_tags='danger')
            else:
                # Evitar registros duplicados para la misma fecha y vehículo
                Registro = RegistroUsoForm().Meta.model
                if Registro.objects.filter(vehiculo=vehiculo_asignado, fecha=registro.fecha).exists():
                    # Mostrar flash en rojo y no guardar
                    messages.error(request, 'Ya existe un registro para esta fecha.', extra_tags='danger')
                else:
                    registro.save()
                    # Actualizar kilometraje actual del vehículo si se reportó kilometraje_fin
                    try:
                        if registro.kilometraje_fin and (vehiculo_asignado.kilometraje_actual is None or registro.kilometraje_fin > vehiculo_asignado.kilometraje_actual):
                            vehiculo_asignado.kilometraje_actual = registro.kilometraje_fin
                            vehiculo_asignado.save()
                    except Exception:
                        pass
                    messages.success(request, 'Registro de uso guardado correctamente.')
                    return redirect('mi_vehiculo')

    context = {
        'titulo': 'Registrar Kilometraje',
        'vehiculo': vehiculo_asignado,
        'empleado': empleado,
        'registro_form': registro_form,
    }
    return render(request, 'registrar_km.html', context)


@login_required
def historial_km(request):
    """Página que muestra el historial de registros del vehículo asignado."""
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('perfil_usuario')

    asignacion_vehiculo = AsignacionVehiculo.objects.filter(
        empleado=empleado,
        estado='activa'
    ).select_related('vehiculo').first()
    if not asignacion_vehiculo:
        messages.info(request, 'No tienes vehículo asignado actualmente.')
        return redirect('perfil_usuario')

    vehiculo_asignado = asignacion_vehiculo.vehiculo
    Registro = RegistroUsoForm().Meta.model
    registros = Registro.objects.filter(vehiculo=vehiculo_asignado).order_by('-fecha')
    context = {
        'titulo': 'Historial de Kilometraje',
        'vehiculo': vehiculo_asignado,
        'registros': registros,
        'empleado': empleado,
    }
    return render(request, 'historial_km.html', context)


@login_required
def notificaciones_usuario(request):
    """Vista de notificaciones del usuario"""
    # Soportar filtrado por leídas/no leídas vía query param `f`
    # Por defecto mostramos 'no_leida' cuando el usuario entra a la página sin query params
    filtro = request.GET.get('f')  # valores esperados: 'leida', 'no_leida' o None
    if not filtro:
        filtro = 'no_leida'
    qs = Notificacion.objects.filter(usuario=request.user)
    if filtro == 'leida':
        qs = qs.filter(leida=True)
    elif filtro == 'no_leida':
        qs = qs.filter(leida=False)

    notificaciones = qs.order_by('-fecha_creacion')

    context = {
        'titulo': 'Mis Notificaciones',
        'notificaciones': notificaciones,
        'total_no_leidas': Notificacion.objects.filter(usuario=request.user, leida=False).count(),
        'total_leidas': Notificacion.objects.filter(usuario=request.user, leida=True).count(),
        'filtro_actual': filtro,
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
    # Antes de cargar las notificaciones, generar notificaciones de estatus que finalizan hoy
    try:
        from apps.recursos_humanos.models import notify_status_end_for_today
        notify_status_end_for_today()
    except Exception:
        # No interrumpir si algo falla aquí; las notificaciones seguirán cargando
        pass

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