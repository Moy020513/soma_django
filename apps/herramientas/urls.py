from django.urls import path
from . import views

app_name = 'herramientas'

from django.urls import path
from . import views

app_name = 'herramientas'

urlpatterns = [
    path('', views.HerramientasView.as_view(), name='index'),
]