from django.urls import path
from . import views

app_name = 'asignaciones'

urlpatterns = [
    path('mias/', views.MisAsignacionesView.as_view(), name='mias'),
    path('admin/lista/', views.AsignacionListAdminView.as_view(), name='listar_admin'),
    path('admin/nueva/', views.AsignacionCreateView.as_view(), name='crear'),
    path('admin/<int:pk>/editar/', views.AsignacionUpdateView.as_view(), name='editar'),
    path('<int:pk>/', views.AsignacionDetailView.as_view(), name='detalle'),
]
