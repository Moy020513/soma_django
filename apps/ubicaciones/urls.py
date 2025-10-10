from django.urls import path
from . import views

app_name = 'ubicaciones'

urlpatterns = [
    # Vista principal para empleados - registro de ubicación
    path('registrar/', views.RegistrarUbicacionView.as_view(), name='registrar'),
    
    # API endpoint para el registro desde JavaScript
    path('api/registrar/', views.RegistrarUbicacionAPIView.as_view(), name='api_registrar'),
    
    # Dashboard para administradores
    path('list/', views.DashboardUbicacionesView.as_view(), name='dashboard'),
    
    # Vista filtrada por fecha
    path('list/<str:fecha>/', views.DashboardUbicacionesView.as_view(), name='dashboard_fecha'),
    
    # API para limpiar todas las ubicaciones
    path('api/limpiar/', views.LimpiarUbicacionesAPIView.as_view(), name='api_limpiar'),
    
    # Vista de mapa individual
    path('mapa/<int:registro_id>/', views.MapaUbicacionView.as_view(), name='mapa_detalle'),
    
    # Empleados sin entrada y sin salida
    path('sin-entrada/', views.EmpleadosSinEntradaView.as_view(), name='sin_entrada'),
    path('sin-salida/', views.EmpleadosSinSalidaView.as_view(), name='sin_salida'),
]