from django.urls import path
from . import views

app_name = 'empresas'

from django.urls import path
from . import views

app_name = 'empresas'

urlpatterns = [
    path('', views.EmpresasView.as_view(), name='index'),
]