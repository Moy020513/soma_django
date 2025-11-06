from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import UpdateView
from .models import Notificacion, RespuestaNotificacion
from django.views.generic import DetailView
from .forms import RespuestaNotificacionForm

# Vista para que el usuario (empleado) modifique su propia respuesta
class ModificarRespuestaUsuarioView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        from django.contrib import messages
        messages.success(self.request, '¡Tu respuesta ha sido modificada con éxito!')

        # Notificar al admin sobre la modificación
        from apps.usuarios.models import Usuario
        from .models import Notificacion
        # Notificar a todos los superusuarios activos (no sólo al primero)
        superusers = Usuario.objects.filter(is_superuser=True, is_active=True)
        if superusers.exists():
            nombre = self.request.user.first_name
            apellido = self.request.user.last_name.split()[0] if self.request.user.last_name else ''
            from django.urls import reverse
            objetos = []
            for su in superusers:
                admin_notif = Notificacion(
                    usuario=su,
                    titulo=f'{nombre} {apellido} ha modificado su respuesta a "{self.object.notificacion.titulo}"',
                    mensaje=form.instance.mensaje,
                    tipo='info',
                    leida=False
                )
                # guardamos el objeto después de bulk_create; establecemos url en lista
                objetos.append((admin_notif, su))
            # Crear individualmente para que podamos asignar la URL con el PK
            for admin_notif, su in objetos:
                admin_notif.save()
                admin_notif.url = reverse('notificaciones:admin_detalle', args=[admin_notif.pk]) + f'?respuesta_id={self.object.pk}'
                admin_notif.save()
        return response
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notificacion'] = self.object.notificacion if self.object and self.object.notificacion else None
        return context
    model = RespuestaNotificacion
    form_class = RespuestaNotificacionForm
    template_name = 'notificaciones/responder.html'

    def test_func(self):
        # Solo el usuario dueño de la respuesta puede modificarla
        return self.get_object().usuario == self.request.user

    def get_success_url(self):
        notificacion = getattr(self.object, 'notificacion', None)
        if notificacion and notificacion.pk:
            return reverse('notificaciones:detalle_usuario', args=[notificacion.pk])
        return reverse('notificaciones:index')
# from django.views.generic import DetailView
# from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Notificacion, RespuestaNotificacion
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
# Vista para detalle de notificación de usuario/empleado
class DetalleNotificacionUsuarioView(LoginRequiredMixin, DetailView):
    model = Notificacion
    template_name = 'notificaciones/detalle_usuario.html'
    context_object_name = 'notificacion'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Redirección automática para notificaciones de cumpleaños
        if self.object.url and 'cumpleanos' in self.object.url:
            from django.shortcuts import redirect
            return redirect(self.object.url)
        # Redirección automática para notificaciones de inspección de herramienta enviada
        if self.object.titulo.startswith('📤 Inspección de Herramienta Enviada') and self.object.url.endswith('/responder/'):
            from django.shortcuts import redirect
            return redirect(self.object.url)
        # Marcar como leída si no lo está
        if not self.object.leida:
            self.object.leida = True
            self.object.save()
        context = self.get_context_data(object=self.object)
        if request.user.is_superuser:
            # Si hay respuesta_id en la URL, buscar la respuesta globalmente
            respuesta_id = request.GET.get('respuesta_id')
            from .models import RespuestaNotificacion
            if respuesta_id:
                try:
                    respuesta = RespuestaNotificacion.objects.get(pk=respuesta_id)
                except RespuestaNotificacion.DoesNotExist:
                    respuesta = None
                context['todas_respuestas'] = [respuesta] if respuesta else []
            else:
                # Buscar la respuesta más reciente asociada a la notificación original del empleado
                respuesta = RespuestaNotificacion.objects.filter(mensaje=self.object.mensaje).order_by('-fecha_respuesta').first()
                context['todas_respuestas'] = [respuesta] if respuesta else []
        else:
            respuesta_usuario = self.object.respuestas.filter(usuario=self.request.user).first()
            context['respuesta_usuario'] = respuesta_usuario
        return self.render_to_response(context)
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
        # Los administradores NO pueden responder notificaciones según la nueva política.
        # Devolvemos False para que UserPassesTestMixin devuelva 403; además sobreescribimos
        # dispatch para redirigir con mensaje más amable.
        return False

    def dispatch(self, request, *args, **kwargs):
        # Bloquear el acceso a este view para superusers -> devolver 403
        from django.http import HttpResponseForbidden
        if request.user.is_authenticated and request.user.is_superuser:
            return HttpResponseForbidden('Los administradores no pueden responder notificaciones.')
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
        # Bloqueamos modificación de respuestas por parte de administradores
        return False

    def dispatch(self, request, *args, **kwargs):
        from django.http import HttpResponseForbidden
        if request.user.is_authenticated and request.user.is_superuser:
            return HttpResponseForbidden('Los administradores no pueden modificar respuestas a notificaciones.')
        return super().dispatch(request, *args, **kwargs)

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

# Vista para detalle de notificación de cumpleaños
class DetalleCumpleanosNotificacionView(LoginRequiredMixin, DetailView):
    model = Notificacion
    template_name = 'notificaciones/detalle_cumpleanos.html'
    context_object_name = 'notificacion'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.leida:
            self.object.leida = True
            self.object.save()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

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
        # Verificar si el usuario ya respondió
        ya_respondio = RespuestaNotificacion.objects.filter(notificacion=self.notificacion, usuario=request.user).exists()
        if ya_respondio:
            from django.contrib import messages
            messages.warning(request, 'Ya has respondido esta notificación.')
            from django.urls import reverse
            return redirect(reverse('notificaciones:index'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.notificacion = self.notificacion
        form.instance.usuario = self.request.user
        response = super().form_valid(form)
        from django.contrib import messages
        from apps.usuarios.models import Usuario
        from .models import Notificacion
        messages.success(self.request, '¡Respuesta enviada correctamente!')
        superusers = Usuario.objects.filter(is_superuser=True, is_active=True)
        if superusers.exists():
            nombre = self.request.user.first_name
            apellido = self.request.user.last_name.split()[0] if self.request.user.last_name else ''
            from django.urls import reverse
            objetos = []
            for su in superusers:
                admin_notif = Notificacion(
                    usuario=su,
                    titulo=f'{nombre} {apellido} ha respondido a "{self.notificacion.titulo}"',
                    mensaje=form.instance.mensaje,
                    tipo='info',
                    leida=False
                )
                objetos.append((admin_notif, su))
            for admin_notif, su in objetos:
                admin_notif.save()
                admin_notif.url = reverse('notificaciones:admin_detalle', args=[admin_notif.pk]) + f'?respuesta_id={form.instance.pk}'
                admin_notif.save()
        return response

    def get_success_url(self):
        return reverse('notificaciones:detalle_usuario', args=[self.notificacion.id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notificacion'] = self.notificacion
        return context