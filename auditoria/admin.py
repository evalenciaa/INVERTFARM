from django.contrib import admin
from .models import Bitacora


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    """Consulta de auditoría: deliberadamente inmutable, exclusiva de TI."""
    list_display = (
        'fecha_hora', 'usuario_texto', 'accion', 'modelo_afectado',
        'id_objeto', 'ip_address', 'ruta',
    )
    list_filter = ('accion', 'modelo_afectado', 'fecha_hora')
    search_fields = (
        'usuario_texto', 'usuario__username', 'id_objeto', 'ip_address',
        'correlacion_id', 'ruta',
    )
    # Sin las tablas de zonas horarias de MySQL, date_hierarchy usa
    # CONVERT_TZ() y vuelve inaccesible la lista. El filtro se conserva.
    ordering = ('-fecha_hora',)
    list_select_related = ('usuario',)
    readonly_fields = (
        'usuario', 'usuario_texto', 'accion', 'modelo_afectado', 'id_objeto',
        'detalles', 'ip_address', 'correlacion_id', 'ruta', 'metodo',
        'user_agent', 'fecha_hora',
    )
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
