from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('accounts/', include('django.contrib.auth.urls')),  # URLs de autenticación
    path('usuarios/', include('apps.usuarios.urls')),
    path('rh/', include('apps.recursos_humanos.urls')),
    path('flota/', include('apps.flota_vehicular.urls')),
    path('herramientas/', include('apps.herramientas.urls')),
    path('empresas/', include('apps.empresas.urls')),
    path('notificaciones/', include('apps.notificaciones.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)