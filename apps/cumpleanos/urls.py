from django.urls import path
from . import views

urlpatterns = [
    path('', views.proximos_cumpleanos, name='proximos_cumpleanos'),
]
