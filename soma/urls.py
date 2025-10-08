from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .email_views import CustomPasswordResetView

urlpatterns = [
    # Admin login override: debe ir ANTES de admin.site.urls para tomar prioridad
    re_path(r'^admin/login/?$', views.admin_login_anyuser, name='admin_login_anyuser'),
    # Redirección limpia sólo para la raíz exacta /admin/ hacia el Home de la app
    re_path(r'^admin/?$', RedirectView.as_view(pattern_name='home', permanent=False), name='admin_root_redirect'),
    path('admin/', admin.site.urls),
    path('', views.index, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('mi-vehiculo/', views.mi_vehiculo, name='mi_vehiculo'),
    path('acciones-recientes/', views.acciones_recientes, name='acciones_recientes'),
    path('mis-notificaciones/', views.notificaciones_usuario, name='notificaciones_usuario'),
    path('notificaciones/<int:notificacion_id>/leida/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    # API / HTMX helpers
    path('api/notificaciones/conteo/', views.api_conteo_notificaciones, name='api_conteo_notificaciones'),
    path('htmx/notificaciones/dropdown/', views.dropdown_notificaciones, name='dropdown_notificaciones'),
    path('api/notificaciones/<int:notificacion_id>/leer/', views.api_marcar_notificacion_leida, name='api_marcar_notificacion_leida'),
    # Password reset personalizado con email multipart (debe ir ANTES de las URLs estándar)
    path('accounts/password_reset/', 
         CustomPasswordResetView.as_view(
             html_email_template_name='registration/password_reset_email_simple.html'
         ), 
         name='password_reset'),
    path('accounts/', include('django.contrib.auth.urls')),  # URLs de autenticación
    # Redirige a RH para registro de empleados (flujo único)
    path('auth/register/', RedirectView.as_view(pattern_name='rh:registrar_empleado', permanent=False), name='registrar_empleado_redirect'),
    path('usuarios/', include('apps.usuarios.urls')),
    path('rh/', include('apps.recursos_humanos.urls')),
    path('flota/', include('apps.flota_vehicular.urls')),
    path('herramientas/', include('apps.herramientas.urls')),
    path('empresas/', include('apps.empresas.urls')),
    path('notificaciones/', include('apps.notificaciones.urls')),
    path('asignaciones/', include('apps.asignaciones.urls')),
    path('ubicaciones/', include('apps.ubicaciones.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)