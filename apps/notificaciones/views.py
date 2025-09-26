from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Notificacion, RespuestaNotificacion
from .forms import RespuestaNotificacionForm
# Vista para que el admin responda a una respuesta de notificación
class ResponderNotificacionAdminView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = RespuestaNotificacion
    form_class = RespuestaNotificacionForm
    template_name = 'notificaciones/responder_admin.html'

    def test_func(self):
        return self.request.user.is_superuser

    def dispatch(self, request, *args, **kwargs):
        self.notificacion = get_object_or_404(Notificacion, pk=kwargs['notificacion_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Buscar si el admin ya respondió a esta notificación
        respuesta_admin = RespuestaNotificacion.objects.filter(notificacion=self.notificacion, usuario=self.request.user).first()
        context['notificacion'] = self.notificacion
        context['ya_respondio'] = bool(respuesta_admin) and not self.request.GET.get('otra')
        context['respuesta_admin'] = respuesta_admin
        return context

    def form_valid(self, form):
        form.instance.notificacion = self.notificacion
        form.instance.usuario = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('notificaciones:admin_detalle', args=[self.notificacion.pk])

# Vista para modificar respuesta del admin
class ModificarRespuestaAdminView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = RespuestaNotificacion
    form_class = RespuestaNotificacionForm
    template_name = 'notificaciones/responder_admin.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_success_url(self):
        return reverse('notificaciones:admin_detalle', args=[self.object.notificacion.pk])

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from .models import Notificacion, RespuestaNotificacion
from .forms import RespuestaNotificacionForm

# Vista para que el admin vea el detalle de la notificación recibida
class DetalleNotificacionAdminView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Notificacion
    template_name = 'notificaciones/detalle_admin.html'
    context_object_name = 'notificacion'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        respuesta_id = self.request.GET.get('respuesta_id')
        respuesta = None
        if respuesta_id:
            from .models import RespuestaNotificacion
            try:
                respuesta = RespuestaNotificacion.objects.get(pk=respuesta_id)
            except RespuestaNotificacion.DoesNotExist:
                respuesta = None
        context['respuesta'] = respuesta
        return context

# Create your views here.

class NotificacionesView(LoginRequiredMixin, ListView):
    template_name = 'notificaciones/index.html'
    context_object_name = 'items'
    
    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user).order_by('-fecha_creacion')


class ResponderNotificacionView(LoginRequiredMixin, CreateView):
    model = RespuestaNotificacion
    form_class = RespuestaNotificacionForm
    template_name = 'notificaciones/responder.html'

    def dispatch(self, request, *args, **kwargs):
        self.notificacion = get_object_or_404(Notificacion, pk=kwargs['notificacion_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.notificacion = self.notificacion
        form.instance.usuario = self.request.user
        response = super().form_valid(form)
        from django.contrib import messages
        from apps.usuarios.models import Usuario
        from .models import Notificacion
        messages.success(self.request, '¡Respuesta enviada correctamente!')
        superuser = Usuario.objects.filter(is_superuser=True, is_active=True).first()
        if superuser:
            # Creamos la notificación para el admin, guardando el ID de la respuesta en la url
            nombre = self.request.user.first_name
            apellido = self.request.user.last_name.split()[0] if self.request.user.last_name else ''
            admin_notif = Notificacion.objects.create(
                usuario=superuser,
                titulo=f'{nombre} {apellido} ha respondido a "{self.notificacion.titulo}"',
                mensaje=form.instance.mensaje,
                tipo='info',
                leida=False
            )
            # La url apunta al detalle y pasa el id de la respuesta
            from django.urls import reverse
            admin_notif.url = reverse('notificaciones:admin_detalle', args=[admin_notif.pk]) + f'?respuesta_id={form.instance.pk}'
            admin_notif.save()
        return response

    def get_success_url(self):
        return reverse('notificaciones:index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notificacion'] = self.notificacion
        return context