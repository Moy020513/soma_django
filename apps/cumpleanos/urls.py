from django.urls import path
from . import views

app_name = 'cumpleanos'

urlpatterns = [
    path('', views.proximos_cumpleanos, name='lista'),
]
