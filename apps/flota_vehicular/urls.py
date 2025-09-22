from django.urls import path
from . import views

app_name = 'flota'

urlpatterns = [
    path('', views.FlotaVehicularView.as_view(), name='index'),
]