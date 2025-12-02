from django.urls import path
from . import views

app_name = 'herramientas'

from django.urls import path
from . import views

app_name = 'herramientas'

urlpatterns = [
    path('', views.HerramientasView.as_view(), name='index'),
    path('mis/', views.mis_herramientas, name='mis_herramientas'),  # Lista de herramientas
    path('mi/', views.mi_herramienta, name='mi_herramienta'),  # Mantener para compatibilidad
    path('detalle/<int:herramienta_id>/', views.detalle_herramienta, name='detalle_herramienta'),  # Nueva vista de detalles
    path('pedir-combustible/', views.pedir_combustible, name='pedir_combustible'),
    path('combustible/<int:pk>/subir-comprobante/', views.subir_comprobante_combustible, name='subir_comprobante_combustible'),
    path('transferir/solicitar/', views.solicitar_transferencia_herramienta, name='solicitar_transferencia'),
    path('transferencias/<int:pk>/', views.transferencia_detalle, name='transferencia_detalle'),
    path('transferencias/<int:pk>/responder/', views.responder_transferencia_herramienta, name='responder_transferencia'),
    path('transferencias/<int:pk>/inspeccionar/', views.inspeccionar_herramienta, name='inspeccionar_transferencia'),
    path('transferencias/', views.mis_transferencias_herramientas, name='mis_transferencias'),
]