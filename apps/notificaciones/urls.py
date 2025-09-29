from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('', views.NotificacionesView.as_view(), name='index'),
    path('responder/<int:notificacion_id>/', views.ResponderNotificacionView.as_view(), name='responder'),
    path('detalle/<int:pk>/', views.DetalleNotificacionUsuarioView.as_view(), name='detalle_usuario'),
    path('admin-detalle/<int:pk>/', views.DetalleNotificacionAdminView.as_view(), name='admin_detalle'),
    path('admin-responder/<int:notificacion_id>/', views.ResponderNotificacionAdminView.as_view(), name='responder_admin'),
    path('admin-modificar-respuesta/<int:pk>/', views.ModificarRespuestaAdminView.as_view(), name='modificar_respuesta'),
]