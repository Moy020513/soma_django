from django.urls import path
from . import views

app_name = 'rh'

urlpatterns = [
    path('', views.ResourcesHumansView.as_view(), name='index'),
    path('registrar/', views.registrar_empleado, name='registrar_empleado'),
]