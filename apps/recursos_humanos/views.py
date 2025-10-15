from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse
from .forms import EmpleadoRegistroForm
from .forms_edicion import EmpleadoEdicionForm

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
        'fecha_nacimiento': empleado_instance.fecha_nacimiento,
        'sexo': empleado_instance.sexo,
        'fecha_ingreso': empleado_instance.fecha_ingreso.strftime('%Y-%m-%d') if empleado_instance.fecha_ingreso else '',
        'puesto': empleado_instance.puesto.pk if empleado_instance.puesto else None,
    }
    if request.method == 'POST':
        form = EmpleadoEdicionForm(request.POST, initial=initial)
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
            empleado_instance.save()
            messages.success(request, f"Empleado actualizado correctamente: {user.username}.")
            return redirect('admin:recursos_humanos_empleado_changelist')
    else:
        form = EmpleadoEdicionForm(initial=initial)

    return render(request, 'recursos_humanos/editar_empleado.html', {'form': form, 'empleado': empleado_instance})
from .models import Empleado

def es_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

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
                'fecha_nacimiento': empleado_instance.fecha_nacimiento,
                'sexo': empleado_instance.sexo,
                'fecha_ingreso': empleado_instance.fecha_ingreso,
                'puesto': empleado_instance.puesto.pk if empleado_instance.puesto else None,
            }
        except Empleado.DoesNotExist:
            empleado_instance = None
    if request.method == 'POST':
        form = EmpleadoRegistroForm(request.POST, initial=initial)
        if form.is_valid():
            cd = form.cleaned_data
            user = cd['usuario']
            # Actualizar datos básicos del usuario elegido (sin tocar credenciales)
            user.first_name = cd['nombre'].strip().title()
            user.last_name = f"{cd['apellido_paterno'].strip().title()} {cd.get('apellido_materno','').strip().title()}".strip()
            user.telefono = cd['telefono']
            if not getattr(user, 'tipo_usuario', None):
                user.tipo_usuario = 'empleado'
            user.save(update_fields=['first_name', 'last_name', 'telefono', 'tipo_usuario'])

            if empleado_instance:
                # Actualizar empleado existente
                empleado_instance.curp = cd['curp'].upper()
                empleado_instance.rfc = cd.get('rfc','').upper()
                empleado_instance.nss = cd.get('nss','')
                empleado_instance.fecha_nacimiento = cd['fecha_nacimiento']
                empleado_instance.sexo = cd['sexo']
                empleado_instance.telefono_personal = cd['telefono']
                empleado_instance.puesto = cd['puesto']
                empleado_instance.fecha_ingreso = cd['fecha_ingreso']
                empleado_instance.save()
                messages.success(request, f"Empleado actualizado correctamente: {user.username}.")
            else:
                # Crear empleado nuevo
                empleado = Empleado(
                    usuario=user,
                    numero_empleado='',  # se autogenera en save()
                    curp=cd['curp'].upper(),
                    rfc=cd.get('rfc','').upper(),
                    nss=cd.get('nss',''),
                    fecha_nacimiento=cd['fecha_nacimiento'],
                    estado_civil='soltero',  # por defecto
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
                    salario_actual=0,
                    activo=True,
                )
                empleado.save()
                messages.success(request, f"Empleado creado correctamente y vinculado al usuario {user.username}.")
            return redirect(reverse('admin:recursos_humanos_empleado_changelist'))
    else:
        form = EmpleadoRegistroForm(initial=initial)

    return render(request, 'recursos_humanos/registrar_empleado.html', {'form': form, 'empleado': empleado_instance})