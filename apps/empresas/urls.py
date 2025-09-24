from django.urls import path
from . import views

app_name = 'empresas'

from django.urls import path
from .views import EmpresasView, EmpresaDetailView

app_name = 'empresas'

urlpatterns = [
    path('', EmpresasView.as_view(), name='index'),
    path('<int:pk>/', EmpresaDetailView.as_view(), name='detalle'),
]