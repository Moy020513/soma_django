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
        if hasattr(user, 'empleado'):
            from datetime import date
            hoy = date.today()
            return (
                Asignacion.objects
                .filter(empleado=user.empleado, fecha=hoy)
                .select_related('empresa', 'supervisor', 'empleado')
                .order_by('-fecha')
            )
        return Asignacion.objects.none()


class EsAdminMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_staff or u.is_superuser)


class AsignacionCreateView(LoginRequiredMixin, EsAdminMixin, CreateView):
    model = Asignacion
    fields = ['fecha', 'empleado', 'empresa', 'supervisor', 'detalles']
    success_url = reverse_lazy('asignaciones:listar_admin')
    template_name = 'asignaciones/form.html'


class AsignacionUpdateView(LoginRequiredMixin, EsAdminMixin, UpdateView):
    model = Asignacion
    fields = ['fecha', 'empleado', 'empresa', 'supervisor', 'detalles']
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
