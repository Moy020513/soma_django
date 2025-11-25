from django.urls import path
from . import views

app_name = 'flota'

urlpatterns = [
    # Transferencias de vehículos
    path('transferencias/', views.mis_transferencias, name='mis_transferencias'),
    path('transferencias/solicitar/', views.solicitar_transferencia, name='solicitar_transferencia'),
    path('transferencias/<int:pk>/', views.transferencia_detalle, name='transferencia_detalle'),
    path('transferencias/<int:pk>/responder-solicitud/', views.responder_solicitud, name='responder_solicitud'),
    path('transferencias/<int:pk>/inspeccionar/', views.inspeccionar_vehiculo, name='inspeccionar_vehiculo'),
    path('transferencias/<int:pk>/responder/', views.responder_inspeccion, name='responder_inspeccion'),
    # Gasolina
    path('pedir-gasolina/', views.pedir_gasolina, name='pedir_gasolina'),
    path('gasolina/<int:pk>/subir-comprobante/', views.subir_comprobante_gasolina, name='subir_comprobante_gasolina'),
]