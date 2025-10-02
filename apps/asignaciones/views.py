from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .models import Asignacion, ActividadAsignada


class MisAsignacionesView(LoginRequiredMixin, ListView):
    template_name = 'asignaciones/mis_asignaciones.html'
    context_object_name = 'asignaciones'

    def get_queryset(self):
        user = self.request.user
        from apps.recursos_humanos.models import Empleado
        empleado = Empleado.objects.filter(usuario=user).first()
        if empleado:
                qs = (Asignacion.objects
                      .filter(empleados=empleado)
                      .select_related('empresa', 'supervisor')
                      .order_by('-fecha', '-fecha_creacion'))
                fecha = self.request.GET.get('fecha')
                if fecha:
                    try:
                        from datetime import date
                        y, m, d = map(int, fecha.split('-'))
                        qs = qs.filter(fecha=date(y, m, d))
                    except Exception:
                        pass
                return qs
        return Asignacion.objects.none()


class EsAdminMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_staff or u.is_superuser)


class AsignacionCreateView(LoginRequiredMixin, EsAdminMixin, CreateView):
    model = Asignacion
    fields = ['fecha', 'empresa', 'supervisor', 'detalles']
    success_url = reverse_lazy('asignaciones:listar_admin')
    template_name = 'asignaciones/form.html'


class AsignacionUpdateView(LoginRequiredMixin, EsAdminMixin, UpdateView):
    model = Asignacion
    fields = ['fecha', 'empresa', 'supervisor', 'detalles']
    success_url = reverse_lazy('asignaciones:listar_admin')
    template_name = 'asignaciones/form.html'


class AsignacionListAdminView(LoginRequiredMixin, EsAdminMixin, ListView):
    model = Asignacion
    template_name = 'asignaciones/lista_admin.html'
    context_object_name = 'asignaciones'
    paginate_by = 20
    ordering = ['-fecha']


class AsignacionDetailView(LoginRequiredMixin, DetailView):
    model = Asignacion
    template_name = 'asignaciones/detalle.html'
    context_object_name = 'asignacion'


class AsignacionesTodasView(LoginRequiredMixin, ListView):
    """Listado de todas las asignaciones visibles para cualquier usuario autenticado.
    - Usuarios estándar: ven todas las asignaciones, ordenadas por fecha desc.
    - Admins: igual, con paginación.
    Futuro: se pueden añadir filtros por fecha/empleado.
    """
    model = Asignacion
    template_name = 'asignaciones/todas.html'
    context_object_name = 'asignaciones'
    paginate_by = 20

    def get_queryset(self):
            qs = (Asignacion.objects
                  .select_related('empresa', 'supervisor')
                  .order_by('-fecha', '-fecha_creacion'))
            # Filtros opcionales por querystring
            empleado_id = self.request.GET.get('empleado')
            fecha = self.request.GET.get('fecha')
            if empleado_id:
                qs = qs.filter(empleados__id=empleado_id)
            if fecha:
                # Formato esperado YYYY-MM-DD
                try:
                    from datetime import date
                    y, m, d = map(int, fecha.split('-'))
                    qs = qs.filter(fecha=date(y, m, d))
                except Exception:
                    pass
            return qs


@csrf_exempt
@require_POST
@login_required
def marcar_actividad_completada(request, actividad_id):
    """
    Vista AJAX para marcar una actividad como completada por el supervisor.
    """
    try:
        # Obtener empleado del usuario actual
        from apps.recursos_humanos.models import Empleado
        empleado = get_object_or_404(Empleado, usuario=request.user)
        
        # Obtener la actividad asignada
        actividad = get_object_or_404(ActividadAsignada, id=actividad_id)
        
        # Verificar que el usuario es el supervisor de la asignación
        if actividad.asignacion.supervisor != empleado:
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para completar esta actividad'
            }, status=403)
        
        # Obtener el estado del request
        data = json.loads(request.body)
        completada = data.get('completada', False)
        
        # Actualizar la actividad
        actividad.completada = completada
        if completada:
            actividad.fecha_completada = timezone.now()
            actividad.completada_por = empleado
        else:
            actividad.fecha_completada = None
            actividad.completada_por = None
        actividad.save()
        
        # Enviar notificación al admin si la actividad se marca como completada
        if completada:
            print(f"Enviando notificación para actividad completada: {actividad.nombre}")
            enviar_notificacion_admin_actividad_completada(actividad, empleado)
        else:
            print(f"Actividad marcada como pendiente: {actividad.nombre}")
        
        return JsonResponse({
            'success': True,
            'completada': actividad.completada,
            'fecha_completada': actividad.fecha_completada.isoformat() if actividad.fecha_completada else None,
            'porcentaje_asignacion': actividad.asignacion.porcentaje_completado
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def enviar_notificacion_admin_actividad_completada(actividad, supervisor):
    """
    Envía notificación al admin cuando se completa una actividad.
    """
    print(f"=== INICIANDO ENVÍO DE NOTIFICACIÓN ===")
    print(f"Actividad: {actividad.nombre}")
    print(f"Supervisor: {supervisor.nombre_completo}")
    
    try:
        from apps.notificaciones.models import Notificacion
        from apps.usuarios.models import Usuario
        
        # Obtener todos los usuarios admin (usando el modelo personalizado Usuario)
        admins = Usuario.objects.filter(is_staff=True, is_active=True)
        print(f"Admins encontrados: {admins.count()}")
        
        titulo = f"✅ Actividad completada por {supervisor.nombre_completo}"
        mensaje = f"La actividad '{actividad.nombre}' de la asignación del {actividad.asignacion.fecha.strftime('%d/%m/%Y')} para la empresa {actividad.asignacion.empresa.nombre} ha sido marcada como completada por {supervisor.nombre_completo}."
        
        # Crear notificación para cada admin
        notificaciones_creadas = 0
        for admin in admins:
            notificacion = Notificacion.objects.create(
                usuario=admin,
                titulo=titulo,
                mensaje=mensaje,
                tipo='success'
            )
            notificaciones_creadas += 1
            print(f"✅ Notificación #{notificacion.id} creada para {admin.username}")
            
        print(f"🎉 Total notificaciones enviadas: {notificaciones_creadas}")
        return True
            
    except Exception as e:
        print(f"❌ Error enviando notificación: {e}")
        import traceback
        traceback.print_exc()
        return False


class SupervisorAsignacionDetailView(LoginRequiredMixin, DetailView):
    """
    Vista detallada de una asignación para el supervisor,
    que permite marcar actividades como completadas.
    """
    model = Asignacion
    template_name = 'asignaciones/supervisor_detalle.html'
    context_object_name = 'asignacion'
    
    def get_queryset(self):
        # Solo permitir ver asignaciones donde el usuario es supervisor
        from apps.recursos_humanos.models import Empleado
        empleado = Empleado.objects.filter(usuario=self.request.user).first()
        if empleado:
            return Asignacion.objects.filter(supervisor=empleado)
        return Asignacion.objects.none()
