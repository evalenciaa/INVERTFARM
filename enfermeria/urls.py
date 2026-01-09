from django.urls import path
from . import views

urlpatterns = [
    # Vista principal
    path('', views.enfermeria_principal, name='enfermeria_principal'),
    
    # Colectivos - Enfermería
    path('colectivos/', views.lista_colectivos_enfermeria, name='lista_colectivos_enfermeria'),
    path('colectivos/crear/', views.crear_colectivo, name='crear_colectivo'),
    path('colectivos/<int:colectivo_id>/', views.detalle_colectivo_enfermeria, name='detalle_colectivo_enfermeria'),
    path('colectivos/<int:colectivo_id>/cancelar/', views.cancelar_colectivo, name='cancelar_colectivo'),
    path('colectivos/<int:colectivo_id>/editar/', views.editar_colectivo, name='editar_colectivo'),
    path('colectivos/<int:colectivo_id>/editar-reenviar/', views.editar_reenviar_colectivo, name='editar_reenviar_colectivo'),
    
    # APIs
    path('api/buscar-medicamentos/', views.api_buscar_medicamentos, name='api_buscar_medicamentos'),
    path('api/buscar-pacientes/', views.api_buscar_pacientes, name='api_buscar_pacientes'),
    path('api/buscar-pacientes-autocomplete/', views.buscar_pacientes_autocomplete, name='buscar_pacientes_autocomplete'),
]