"""
URL configuration for inventfarm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views
from .views import RegisterAPIView, LoginAPIView

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('login/', views.login_view, name='login'),
    path('farmacia/', views.vista_farmacia, name='farmacia'),
    path('principal/', views.bienvenida, name='principal'),
    path('logout/', views.logout_view, name='logout'),
    path('alertas/', views.alertas, name='alertas'),
    path('medicamentos/nuevo/', views.registro_medicamento, name='registro_medicamento'),
    path('editar_lote/<str:lote_id>/', views.editar_lote, name='editar_lote'),
    path('api/medicamentos/buscar/', views.buscar_medicamentos_autocomplete, name='buscar_medicamentos_autocomplete'),
    path('farmacia/gestion-lotes/', views.farmacia_g, name='farmacia_g'),
    path('api/lote/<str:lote_id>/eliminar/', views.eliminar_lote, name='eliminar_lote'),
    path('guardar_descripcion/', views.guardar_descripcion, name='guardar_descripcion'),# Corregido: nombre único
    path('inventario-general/', views.inventario_general, name='inv_gene_f'),
    path('editar-cpm/', views.editar_cpm_medicamento, name='editar_cpm_medicamento'),
    path('api/register/', views.RegisterAPIView.as_view(), name='api_register'),
    path('api/login/', views.LoginAPIView.as_view(), name='api_login'),
    path('salidas/', views.registrar_salida, name='registrar_salida'),
    path('salidas/comprobante/<int:receta_id>/', views.descargar_comprobante, name='descargar_comprobante'),
    path('api/medicamentos/buscar/', views.buscar_medicamentos, name='buscar_medicamentos'),
    path('api/get_paciente_by_name/<str:nombre>/', views.get_paciente_by_name, name='get_paciente_by_name'),
    path('api/entradas/guardar/', views.guardar_entradas, name='guardar_entradas'),
    path('entrada-medicamentos/', views.entrada_medicamentos, name='entrada_medicamentos'),
    path('api/generar-reporte-pdf/', views.generar_reporte_pdf, name='generar_reporte_pdf'),
    path('api/generar-reporte-excel/', views.generar_reporte_excel, name='generar_reporte_excel'),
    path('reportes/generar_excel_salidas/', views.generar_excel_salidas, name='generar_excel_salidas'),
    path('exportar/excel/', views.exportar_inventario_excel, name='exportar_excel'),
    path('exportar/pdf/', views.exportar_inventario_pdf, name='exportar_pdf'),
    path('api/buscar_lote/<str:query>/', views.buscar_lote_json, name='buscar_lote_json'),
    path('api/get_paciente_info/<str:curp>/', views.get_paciente_info_json, name='get_paciente_info_json'),
    path('carga-masiva/', views.carga_masiva, name='carga_masiva'),
    path('api/carga-masiva/procesar/', views.procesar_carga_masiva, name='procesar_carga_masiva'),
]



