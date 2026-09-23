"""
farmacia/views/__init__.py
Punto de entrada para todas las vistas de la aplicación farmacia.
Permite importar las vistas desde farmacia.views.nombre_vista
evitando refactorizar inmediatamente urls.py.
"""

from .auth_views import inicio, login_view, logout_view, bienvenida, vista_farmacia, vista_farmacia_g
from .inventario_views import (
    alertas, editar_lote, farmacia_g, 
    tiene_acceso_farmacia, guardar_descripcion, inventario_general,
    editar_cpm_medicamento, eliminar_lote, registro_medicamento,
    actualizar_cpm, eliminar_medicamento, buscar_catalogo_antibiotico, api_reportes_antibioticos_ddd,
    inventario_antibioticos, exportar_inventario_antibioticos_excel,
    exportar_inventario_antibioticos_pdf,
    exportar_inventario_antibioticos_access_pdf,
    exportar_inventario_antibioticos_watch_pdf,
    exportar_inventario_antibioticos_reserve_pdf,
    truncar_texto
)
from .entrada_views import (
    entrada_medicamentos, guardar_entradas,
    buscar_medicamentos, buscar_medicamentos_autocomplete,
    carga_masiva, procesar_carga_masiva, buscar_lote_json
)
from .salida_views import (
    registrar_salida, descargar_comprobante, generar_excel_salidas,
    get_paciente_info_json, get_paciente_by_name
)
from .pdf_views import generar_reporte_pdf, generar_reporte_excel
from .api_views import RegisterAPIView, LoginAPIView, buscar_instituciones_autocomplete
from .colectivo_views import (
    lista_colectivos_farmacia, detalle_colectivo_farmacia, responder_colectivo,
    completar_colectivo, generar_pdf_colectivo,
    lista_colectivos_antibioticos_farmacia,
    detalle_colectivo_antibioticos_farmacia,
    responder_colectivo_antibioticos,
    completar_colectivo_antibioticos,
    generar_pdf_colectivo_antibioticos,
)
from .admin_views import (
    admin_usuarios, admin_usuario_detalle, admin_crear_usuario, admin_eliminar_usuario,
    admin_grupos, admin_grupo_detalle, admin_crear_grupo, admin_eliminar_grupo
)
from .backup_views import (
    panel_backups, crear_backup, limpiar_backups_antiguos, descargar_backup,
    eliminar_backup, restaurar_backup, subir_backup
)
from .reporte_views import (
    exportar_inventario_excel, exportar_inventario_pdf, exportar_inventario_general_excel,
    exportar_inventario_general_pdf, exportar_inventario_general_excedentes_pdf,
    reportes_farmacia, api_reportes_kpis,
    api_reportes_salidas, api_registro_recetas, exportar_registro_recetas_pdf,
    exportar_registro_recetas_excel, api_reportes_medicamentos_top, api_reportes_pacientes_frecuentes,
    api_reportes_tendencias, exportar_proximos_caducar_pdf, api_medicamentos_sin_movimiento, exportar_medicamentos_sin_movimiento_excel, 
    exportar_medicamentos_sin_movimiento_pdf, api_medicamentos_lento_movimiento, exportar_medicamentos_lento_movimiento_pdf, 
    exportar_medicamentos_lento_movimiento_excel,
)

from .salida_transferencia_views import (
    registrar_salida_transferencia, descargar_comprobante_transferencia
)
