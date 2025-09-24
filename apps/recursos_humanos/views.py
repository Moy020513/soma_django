from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse
from .forms import EmpleadoRegistroForm
from apps.usuarios.models import Rol
from .models import Empleado

Usuario = get_user_model()


def es_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(es_admin)
def registrar_empleado(request):
    if request.method == 'POST':
        form = EmpleadoRegistroForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            username = cd['username_sugerido']
            password = cd['password_generada'].upper()

            # Crear usuario
            user = Usuario.objects.create_user(
                username=username,
                first_name=cd['nombre'].strip().title(),
                last_name=f"{cd['apellido_paterno'].strip().title()} {cd.get('apellido_materno','').strip().title()}".strip(),
                password=password,
            )
            user.telefono = cd['telefono']
            user.tipo_usuario = 'supervisor' if cd.get('es_supervisor') else 'empleado'
            # Asignar Rol Supervisor si aplica
            if cd.get('es_supervisor'):
                rol_sup, _ = Rol.objects.get_or_create(nombre__iexact='Supervisor', defaults={
                    'nombre': 'Supervisor',
                    'descripcion': 'Rol de supervisor con permisos intermedios',
                    'permisos': ''
                })
                # get_or_create con nombre__iexact no permite defaults; manejar ambos casos
                if isinstance(rol_sup, Rol):
                    # Si la búsqueda con nombre__iexact devolvió un objeto, úsalo
                    pass
                else:
                    # En caso raro, obtener/crear por nombre exacto
                    rol_sup, _ = Rol.objects.get_or_create(nombre='Supervisor', defaults={
                        'descripcion': 'Rol de supervisor con permisos intermedios',
                        'permisos': ''
                    })
                user.rol = rol_sup
            user.save()

            # Crear empleado
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
                departamento=cd['departamento'],
                puesto=cd['puesto'],
                jefe_directo=None,
                fecha_ingreso=cd['fecha_ingreso'],
                fecha_baja=None,
                motivo_baja='',
                salario_actual=0,
                activo=True,
            )
            empleado.save()

            messages.success(request, f"Empleado creado. Usuario: {username} | Contraseña: {password}")
            return redirect(reverse('admin:recursos_humanos_empleado_changelist'))
    else:
        form = EmpleadoRegistroForm()

    return render(request, 'recursos_humanos/registrar_empleado.html', {'form': form})
from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

# Create your views here.

class ResourcesHumansView(LoginRequiredMixin, ListView):
    template_name = 'recursos_humanos/index.html'
    context_object_name = 'items'
    
    def get_queryset(self):
        return []  # Placeholder hasta crear modelos