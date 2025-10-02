from django.urls import path
from . import views

app_name = 'asignaciones'

urlpatterns = [
    path('mias/', views.MisAsignacionesView.as_view(), name='mias'),
    path('todas/', views.AsignacionesTodasView.as_view(), name='todas'),
    path('admin/lista/', views.AsignacionListAdminView.as_view(), name='listar_admin'),
    path('admin/nueva/', views.AsignacionCreateView.as_view(), name='crear'),
    path('admin/<int:pk>/editar/', views.AsignacionUpdateView.as_view(), name='editar'),
    path('<int:pk>/', views.AsignacionDetailView.as_view(), name='detalle'),
    path('supervisor/<int:pk>/', views.SupervisorAsignacionDetailView.as_view(), name='supervisor_detalle'),
    path('ajax/actividad/<int:actividad_id>/completar/', views.marcar_actividad_completada, name='marcar_actividad_completada'),
    path('admin/exportar-hoy-pdf/', views.exportar_asignaciones_hoy_pdf, name='exportar_hoy_pdf'),
]
