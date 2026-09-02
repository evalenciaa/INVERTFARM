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
    path('api/catalogo-antibioticos/buscar/', views.buscar_catalogo_antibiotico, name='buscar_catalogo_antibiotico'),
    path('editar_lote/<str:lote_id>/', views.editar_lote, name='editar_lote'),
    path('api/medicamentos/buscar/', views.buscar_medicamentos_autocomplete, name='buscar_medicamentos_autocomplete'),
    path('farmacia/gestion-lotes/', views.farmacia_g, name='farmacia_g'),
    path('api/lote/<str:lote_id>/eliminar/', views.eliminar_lote, name='eliminar_lote'),
    path('guardar_descripcion/', views.guardar_descripcion, name='guardar_descripcion'),
    path('inventario-general/', views.inventario_general, name='inv_gene_f'),
    path('editar-cpm/', views.editar_cpm_medicamento, name='editar_cpm_medicamento'),
    path('actualizar_cpm/', views.actualizar_cpm, name='actualizar_cpm'),
    path('eliminar_medicamento/', views.eliminar_medicamento, name='eliminar_medicamento'),
    path('api/register/', views.RegisterAPIView.as_view(), name='api_register'),
    path('api/login/', views.LoginAPIView.as_view(), name='api_login'),
    path('salidas/', views.registrar_salida, name='registrar_salida'),
    path('salidas/comprobante/<int:receta_id>/', views.descargar_comprobante, name='descargar_comprobante'),
    path('salidas/transferencia/', views.registrar_salida_transferencia, name='registrar_salida_transferencia'),
    path('salidas/transferencia/comprobante/<int:transferencia_id>/', views.descargar_comprobante_transferencia, name='descargar_comprobante_transferencia'),
    path('api/buscar-instituciones-autocomplete/', views.buscar_instituciones_autocomplete, name='buscar_instituciones_autocomplete'),
    path('api/medicamentos/buscar/', views.buscar_medicamentos, name='buscar_medicamentos'),
    path('api/get_paciente_by_name/<str:nombre>/', views.get_paciente_by_name, name='get_paciente_by_name'),
    path('api/entradas/guardar/', views.guardar_entradas, name='guardar_entradas'),
    path('entrada-medicamentos/', views.entrada_medicamentos, name='entrada_medicamentos'),
    path('api/generar-reporte-pdf/', views.generar_reporte_pdf, name='generar_reporte_pdf'),
    path('api/generar-reporte-excel/', views.generar_reporte_excel, name='generar_reporte_excel'),
    path('reportes/', views.reportes_farmacia, name='reportes_farmacia'),
    path('reportes/generar_excel_salidas/', views.generar_excel_salidas, name='generar_excel_salidas'),
    path('exportar/excel/', views.exportar_inventario_excel, name='exportar_excel'),
    path('exportar/pdf/', views.exportar_inventario_pdf, name='exportar_pdf'),
    path('exportar/pdf/proximos-caducar/', views.exportar_proximos_caducar_pdf, name='exportar_proximos_caducar_pdf'),
    path('exportar_inventario_general_excel/', views.exportar_inventario_general_excel, name='exportar_inventario_general_excel'),
    path('exportar_inventario_general_pdf/', views.exportar_inventario_general_pdf, name='exportar_inventario_general_pdf'),
    path('api/reportes/salidas/', views.api_reportes_salidas, name='api_reportes_salidas'),
    path('api/reportes/medicamentos-top/', views.api_reportes_medicamentos_top, name='api_reportes_medicamentos_top'),
    path('reportes/medicamentos-sin-movimiento/excel/', views.exportar_medicamentos_sin_movimiento_excel, name='exportar_medicamentos_sin_movimiento_excel'),
    path('reportes/medicamentos-sin-movimiento/pdf/', views.exportar_medicamentos_sin_movimiento_pdf, name='exportar_medicamentos_sin_movimiento_pdf'),
    path('api/reportes/pacientes-frecuentes/', views.api_reportes_pacientes_frecuentes, name='api_reportes_pacientes_frecuentes'),
    path('api/reportes/tendencias/', views.api_reportes_tendencias, name='api_reportes_tendencias'),
    path('api/reportes/kpis/', views.api_reportes_kpis, name='api_reportes_kpis'),
    path('api/reportes/medicamentos-sin-movimiento/', views.api_medicamentos_sin_movimiento, name='api_medicamentos_sin_movimiento'),
    path('api/medicamentos-lento-movimiento/', views.api_medicamentos_lento_movimiento, name='api_medicamentos_lento_movimiento'),
    path('reportes/medicamentos-lento-movimiento/pdf/', views.exportar_medicamentos_lento_movimiento_pdf, name='exportar_medicamentos_lento_movimiento_pdf'),
    path('reportes/medicamentos-lento-movimiento/excel/', views.exportar_medicamentos_lento_movimiento_excel, name='exportar_medicamentos_lento_movimiento_excel'),
    path('api/buscar_lote/<str:query>/', views.buscar_lote_json, name='buscar_lote_json'),
    path('api/get_paciente_info/<str:curp>/', views.get_paciente_info_json, name='get_paciente_info_json'),
    path('carga-masiva/', views.carga_masiva, name='carga_masiva'),
    path('api/carga-masiva/procesar/', views.procesar_carga_masiva, name='procesar_carga_masiva'),
    
    # Rutas de Colectivos - Enfermeria
    path('colectivos-farmacia/', views.lista_colectivos_farmacia, name='lista_colectivos_farmacia'),
    path('colectivos-farmacia/<int:colectivo_id>/', views.detalle_colectivo_farmacia, name='detalle_colectivo_farmacia'),
    path('colectivos-farmacia/<int:colectivo_id>/responder/', views.responder_colectivo, name='responder_colectivo'),
    path('colectivos-farmacia/<int:colectivo_id>/completar/', views.completar_colectivo, name='completar_colectivo'),
    path('colectivos-farmacia/<int:colectivo_id>/pdf/', views.generar_pdf_colectivo, name='generar_pdf_colectivo'),
    
    
    # ===== ADMINISTRACIÓN DE USUARIOS Y GRUPOS =====
    path('admin-usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin-usuarios/crear/', views.admin_crear_usuario, name='admin_crear_usuario'),
    path('admin-usuarios/<int:user_id>/', views.admin_usuario_detalle, name='admin_usuario_detalle'),
    path('admin-usuarios/eliminar/<int:user_id>/', views.admin_eliminar_usuario, name='admin_eliminar_usuario'),

    path('admin-grupos/', views.admin_grupos, name='admin_grupos'),
    path('admin-grupos/crear/', views.admin_crear_grupo, name='admin_crear_grupo'),
    path('admin-grupos/<int:grupo_id>/', views.admin_grupo_detalle, name='admin_grupo_detalle'),
    path('admin-grupos/eliminar/<int:grupo_id>/', views.admin_eliminar_grupo, name='admin_eliminar_grupo'),
    
    
    # BACKUPS
    path('backups/', views.panel_backups, name='panel_backups'),
    path('backups/crear/', views.crear_backup, name='crear_backup'),
    path('backups/subir/', views.subir_backup, name='subir_backup'),
    path('backups/descargar/<str:filename>/', views.descargar_backup, name='descargar_backup'),
    path('backups/eliminar/<str:filename>/', views.eliminar_backup, name='eliminar_backup'),
    path('backups/restaurar/', views.restaurar_backup, name='restaurar_backup'),
]



