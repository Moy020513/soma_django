from .models import Inasistencia, Empleado

from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from .forms import EmpleadoRegistroForm
from .forms_edicion import EmpleadoEdicionForm
from .forms_periodo import NuevoPeriodoEstatusForm
from .forms_inasistencia import InasistenciaForm

def es_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(es_admin)
def editar_empleado(request, empleado_id):
    try:
        empleado_instance = Empleado.objects.get(pk=empleado_id)
    except Empleado.DoesNotExist:
        messages.error(request, 'Empleado no encontrado.')
        return redirect('admin:recursos_humanos_empleado_changelist')

    usuario = empleado_instance.usuario
    initial = {
        'usuario': usuario.pk,
        'nombre': usuario.first_name,
        'apellido_paterno': usuario.last_name.split(' ')[0] if usuario.last_name else '',
        'apellido_materno': ' '.join(usuario.last_name.split(' ')[1:]) if usuario.last_name and len(usuario.last_name.split(' ')) > 1 else '',
        'telefono': usuario.telefono,
        'nss': empleado_instance.nss,
        'curp': empleado_instance.curp,
        'rfc': empleado_instance.rfc,
        'fecha_nacimiento': empleado_instance.fecha_nacimiento.strftime('%Y-%m-%d') if empleado_instance.fecha_nacimiento else '',
        'sexo': empleado_instance.sexo,
        'fecha_ingreso': empleado_instance.fecha_ingreso.strftime('%Y-%m-%d') if empleado_instance.fecha_ingreso else '',
        'puesto': empleado_instance.puesto.pk if empleado_instance.puesto else None,
        'salario_inicial': empleado_instance.salario_inicial,
        'salario_actual': empleado_instance.salario_actual,
    }
    periodo_form = NuevoPeriodoEstatusForm(initial={'empleado_instance': empleado_instance})
    if request.method == 'POST':
        form = EmpleadoEdicionForm(request.POST, initial=initial)
        periodo_form = NuevoPeriodoEstatusForm(request.POST, initial={'empleado_instance': empleado_instance})
        periodo_agregado = False
        if form.is_valid():
            cd = form.cleaned_data
            user = cd['usuario']
            user.first_name = cd['nombre'].strip().title()
            user.last_name = f"{cd['apellido_paterno'].strip().title()} {cd.get('apellido_materno','').strip().title()}".strip()
            user.telefono = cd['telefono']
            if not getattr(user, 'tipo_usuario', None):
                user.tipo_usuario = 'empleado'
            user.save(update_fields=['first_name', 'last_name', 'telefono', 'tipo_usuario'])

            empleado_instance.curp = cd['curp'].upper()
            empleado_instance.rfc = cd.get('rfc','').upper()
            empleado_instance.nss = cd.get('nss','')
            empleado_instance.fecha_nacimiento = cd['fecha_nacimiento']
            empleado_instance.sexo = cd['sexo']
            empleado_instance.telefono_personal = cd['telefono']
            empleado_instance.puesto = cd['puesto']
            empleado_instance.fecha_ingreso = cd['fecha_ingreso']
            # Actualizar salario si viene en el formulario
            try:
                if 'salario_inicial' in cd:
                    empleado_instance.salario_inicial = cd.get('salario_inicial') or 0
            except Exception:
                pass
            try:
                if 'salario_actual' in cd:
                    empleado_instance.salario_actual = cd.get('salario_actual') or 0
            except Exception:
                pass
            empleado_instance.save()
            messages.success(request, f"Empleado actualizado correctamente: {user.username}.")
            periodo_agregado = False
            if periodo_form.is_valid() and periodo_form.cleaned_data.get('estatus'):
                # Actualizar fecha fin del último periodo si no está definida
                ultimo = empleado_instance.periodos_estatus.order_by('-fecha_inicio').first()
                nueva_fecha_inicio = periodo_form.cleaned_data['fecha_inicio']
                nueva_fecha_fin = periodo_form.cleaned_data.get('fecha_fin')
                if ultimo and not ultimo.fecha_fin and nueva_fecha_inicio:
                    from datetime import timedelta
                    ultimo.fecha_fin = nueva_fecha_inicio - timedelta(days=1)
                    ultimo.save()
                # Crear nuevo periodo
                nuevo_periodo = periodo_form.save(commit=False)
                nuevo_periodo.empleado = empleado_instance
                # Si el usuario no puso fecha_fin, dejarla en None
                if not nueva_fecha_fin:
                    nuevo_periodo.fecha_fin = None
                nuevo_periodo.save()
                periodo_agregado = True
                messages.success(request, "Nuevo periodo de estatus agregado correctamente.")
            return redirect('admin:recursos_humanos_empleado_changelist')
    else:
        form = EmpleadoEdicionForm(initial=initial)
        periodo_form = NuevoPeriodoEstatusForm(initial={'empleado_instance': empleado_instance})

    estatus_actual = None
    periodo_actual = None
    if empleado_instance:
        # Usar helper del modelo para obtener el periodo vigente (si lo hay).
        periodo_actual = empleado_instance.get_periodo_actual()
        if periodo_actual:
            estatus_actual = periodo_actual.estatus
        else:
            # No hay periodo vigente -> mostrar "sin estatus"
            estatus_actual = 'sin estatus'
    return render(request, 'recursos_humanos/editar_empleado.html', {
        'form': form,
        'empleado': empleado_instance,
        'periodo_form': periodo_form,
        'estatus_actual': estatus_actual,
        'periodo_actual': periodo_actual,
        'historial_salario': empleado_instance.historial_salario.order_by('fecha') if empleado_instance else [],
    })

# Vista para listar inasistencias
@login_required
@user_passes_test(es_admin)
def listar_inasistencias(request):
    inasistencias = Inasistencia.objects.select_related('empleado', 'registrada_por').order_by('-fecha')
    return render(request, 'recursos_humanos/listar_inasistencias.html', {'inasistencias': inasistencias})


@login_required
@user_passes_test(es_admin)
def registrar_inasistencia(request):
    print('==== Vista registrar_inasistencia ejecutada ====', request.method)
    if request.method == 'POST':
        print('Instanciando InasistenciaForm con POST')
        form = InasistenciaForm(request.POST)
        if form.is_valid():
            inas = form.save(commit=False)
            inas.registrada_por = request.user
            inas.save()
            messages.success(request, 'Inasistencia registrada correctamente.')
            return redirect('rh:listar_inasistencias')
        else:
            messages.error(request, 'Corrige los errores en el formulario.')
    else:
        # permitir filtrar empleado por ?empleado=ID
        empleado_id = request.GET.get('empleado')
        initial = {}
        if empleado_id:
            try:
                emp = Empleado.objects.get(pk=empleado_id)
                initial['empleado'] = emp
            except Empleado.DoesNotExist:
                pass
    print('Instanciando InasistenciaForm con initial:', initial)
    form = InasistenciaForm(initial=initial)
    return render(request, 'recursos_humanos/registrar_inasistencia.html', {'form': form})
@login_required
@user_passes_test(es_admin)
def registrar_empleado(request):
    empleado_id = request.GET.get('edit')
    empleado_instance = None
    initial = {}
    if empleado_id:
        try:
            empleado_instance = Empleado.objects.get(pk=empleado_id)
            usuario = empleado_instance.usuario
            initial = {
                'usuario': usuario.pk,
                'nombre': usuario.first_name,
                'apellido_paterno': usuario.last_name.split(' ')[0] if usuario.last_name else '',
                'apellido_materno': ' '.join(usuario.last_name.split(' ')[1:]) if usuario.last_name and len(usuario.last_name.split(' ')) > 1 else '',
                'telefono': usuario.telefono,
                'nss': empleado_instance.nss,
                'curp': empleado_instance.curp,
                'rfc': empleado_instance.rfc,
                'fecha_nacimiento': empleado_instance.fecha_nacimiento.strftime('%Y-%m-%d') if empleado_instance.fecha_nacimiento else '',
                'sexo': empleado_instance.sexo,
                'fecha_ingreso': empleado_instance.fecha_ingreso.strftime('%Y-%m-%d') if empleado_instance.fecha_ingreso else '',
                'puesto': empleado_instance.puesto.pk if empleado_instance.puesto else None,
                    'salario_inicial': empleado_instance.salario_inicial,
                    'salario_actual': empleado_instance.salario_actual,
            }
        except Empleado.DoesNotExist:
            empleado_instance = None
    periodo_form = NuevoPeriodoEstatusForm()
    if request.method == 'POST':
        form = EmpleadoRegistroForm(request.POST, initial=initial)
        periodo_form = NuevoPeriodoEstatusForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = cd['usuario']
            user.first_name = cd['nombre'].strip().title()
            user.last_name = f"{cd['apellido_paterno'].strip().title()} {cd.get('apellido_materno','').strip().title()}".strip()
            user.telefono = cd['telefono']
            if not getattr(user, 'tipo_usuario', None):
                user.tipo_usuario = 'empleado'
            user.save(update_fields=['first_name', 'last_name', 'telefono', 'tipo_usuario'])

            if empleado_instance:
                empleado_instance.curp = cd['curp'].upper()
                empleado_instance.rfc = cd.get('rfc','').upper()
                empleado_instance.nss = cd.get('nss','')
                empleado_instance.fecha_nacimiento = cd['fecha_nacimiento']
                empleado_instance.sexo = cd['sexo']
                empleado_instance.telefono_personal = cd['telefono']
                empleado_instance.puesto = cd['puesto']
                empleado_instance.fecha_ingreso = cd['fecha_ingreso']
                # Actualizar salarios si vienen en el formulario
                try:
                    if 'salario_inicial' in cd:
                        empleado_instance.salario_inicial = cd.get('salario_inicial') or empleado_instance.salario_inicial or 0
                except Exception:
                    pass
                try:
                    if 'salario_actual' in cd:
                        empleado_instance.salario_actual = cd.get('salario_actual') or empleado_instance.salario_actual or 0
                except Exception:
                    pass
                empleado_instance.save()
                messages.success(request, f"Empleado actualizado correctamente: {user.username}.")
            else:
                empleado = Empleado(
                    usuario=user,
                    numero_empleado='',
                    curp=cd['curp'].upper(),
                    rfc=cd.get('rfc','').upper(),
                    nss=cd.get('nss',''),
                    fecha_nacimiento=cd['fecha_nacimiento'],
                    estado_civil='soltero',
                    tipo_sangre='',
                    sexo=cd['sexo'],
                    telefono_personal=cd['telefono'],
                    telefono_emergencia='',
                    contacto_emergencia='',
                    direccion='',
                    puesto=cd['puesto'],
                    jefe_directo=None,
                    fecha_ingreso=cd['fecha_ingreso'],
                    fecha_baja=None,
                    motivo_baja='',
                    salario_inicial=(cd.get('salario_inicial') or 0),
                    salario_actual=(cd.get('salario_actual') or 0),
                    activo=True,
                )
                empleado.save()
                # Crear periodo de estatus inicial
                if periodo_form.is_valid():
                    periodo = periodo_form.save(commit=False)
                    periodo.empleado = empleado
                    periodo.fecha_fin = None
                    periodo.save()
                messages.success(request, f"Empleado creado correctamente y vinculado al usuario {user.username}.")
            return redirect(reverse('admin:recursos_humanos_empleado_changelist'))
    else:
        form = EmpleadoRegistroForm(initial=initial)
        periodo_form = NuevoPeriodoEstatusForm()

    return render(request, 'recursos_humanos/registrar_empleado.html', {'form': form, 'empleado': empleado_instance, 'periodo_form': periodo_form})