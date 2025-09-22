from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('', views.NotificacionesView.as_view(), name='index'),
]