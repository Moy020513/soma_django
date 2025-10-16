from django.urls import path
from . import views

app_name = 'rh'

urlpatterns = [
    ## path('', views.ResourcesHumansView.as_view(), name='index'),
    path('registrar/', views.registrar_empleado, name='registrar_empleado'),
    path('editar/<int:empleado_id>/', views.editar_empleado, name='editar_empleado'),
    path('inasistencias/', views.listar_inasistencias, name='listar_inasistencias'),
    path('inasistencias/registrar/', views.registrar_inasistencia, name='registrar_inasistencia'),
]