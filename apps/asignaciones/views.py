from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy

from .models import Asignacion


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
