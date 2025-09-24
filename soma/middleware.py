from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import translation


class NonStaffAccessRestrictionMiddleware:
    """
    Restringe a usuarios autenticados NO-staff/NO-superuser a un conjunto de rutas permitidas.
    Si intentan acceder a otras rutas, se les redirige al dashboard con un mensaje.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Prefijos y rutas permitidas para usuarios no-staff
        self.allowed_prefixes = (
            '/',  # home
            '/dashboard/',
            '/perfil/',
            '/mis-notificaciones/',
            '/notificaciones/',  # incluye detalle/acciones
            '/flota/',  # transferencias u otros listados relacionados
            '/accounts/',  # auth endpoints (logout, password reset urls si se usan)
            '/admin/login/',  # permitir ver formulario login admin
            '/admin/logout/',
            '/static/',  # assets
            '/media/',   # media
        )

        # Rutas exactas adicionales a permitir
        self.allowed_exact = (
            '/favicon.ico',
        )

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path

        if user and user.is_authenticated and not (user.is_staff or user.is_superuser):
            # Validar si la ruta está permitida
            allowed = path in self.allowed_exact or any(
                path.startswith(prefix) for prefix in self.allowed_prefixes
            )

            if not allowed:
                messages.warning(request, 'No tienes permisos para acceder a esa sección.')
                return redirect(reverse('dashboard'))

        response = self.get_response(request)
        return response


class ForceSpanishLocaleMiddleware:
    """
    Fuerza el idioma español para toda la aplicación, independientemente del
    header Accept-Language del navegador. Útil para asegurar que el admin y
    los mensajes de Django se muestren en español.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        translation.activate('es')
        request.LANGUAGE_CODE = 'es'
        response = self.get_response(request)
        response.setdefault('Content-Language', 'es')
        translation.deactivate()
        return response
