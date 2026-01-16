from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from .models import (
    UsuarioPersonalizado, Departamento, Proveedor, Presentacion,
    Medicamento, Lote, Entrada, DetalleEntrada, Salida, Paciente,
    Receta, RecetaMedicamento, CPMMedicamento, Almacen, Institucion,
    FuenteFinanciamiento, MedicamentoNoSurtido
)

# ===== USUARIO PERSONALIZADO =====
@admin.register(UsuarioPersonalizado)
class UsuarioPersonalizadoAdmin(UserAdmin):
    list_display = ('username', 'email', 'rol', 'departamento', 'is_active', 'is_staff')
    list_filter = ('rol', 'is_active', 'is_staff', 'departamento')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información del Hospital', {
            'fields': ('rol', 'departamento', 'telefono')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información del Hospital', {
            'fields': ('rol', 'departamento', 'telefono')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('departamento')


# ===== CONFIGURACIÓN MEJORADA DE GRUPOS =====
class GrupoConPermisosAdmin(admin.ModelAdmin):
    """Admin mejorado para facilitar la asignación de permisos a grupos"""
    list_display = ('name', 'cantidad_permisos', 'cantidad_usuarios')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    
    def cantidad_permisos(self, obj):
        return obj.permissions.count()
    cantidad_permisos.short_description = 'Permisos Asignados'
    
    def cantidad_usuarios(self, obj):
        return obj.user_set.count()
    cantidad_usuarios.short_description = 'Usuarios en el Grupo'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('permissions', 'user_set')

# Desregistrar Group por defecto y registrar el personalizado
admin.site.unregister(Group)
admin.site.register(Group, GrupoConPermisosAdmin)


# ===== MODELOS DE FARMACIA =====
@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'telefono', 'email', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'rfc', 'email')
    list_editable = ('activo',)


@admin.register(Presentacion)
class PresentacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'unidades_por_caja', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    list_editable = ('activo',)


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ('clave', 'descripcion', 'presentacion', 'costo', 'proveedor', 'activo')
    list_filter = ('activo', 'presentacion', 'proveedor')
    search_fields = ('clave', 'descripcion', 'codigo_barras')
    list_editable = ('activo',)
    ordering = ('clave',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('presentacion', 'proveedor')


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'medicamento', 'lote_codigo', 'fecha_caducidad', 'existencia', 'costo_unitario', 'color_alerta')
    list_filter = ('fecha_caducidad', 'presentacion')
    search_fields = ('id', 'lote_codigo', 'medicamento__clave', 'medicamento__descripcion')
    readonly_fields = ('id',)
    ordering = ('-fecha_caducidad',)
    
    def color_alerta(self, obj):
        color = obj.color_alerta()
        color_map = {
            'rojo': '🔴 Caducado/Próximo',
            'amarillo': '🟡 Advertencia',
            'verde': '🟢 Normal',
            'sin-fecha': '⚪ Sin fecha'
        }
        return color_map.get(color, color)
    color_alerta.short_description = 'Estado'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('medicamento', 'presentacion')


@admin.register(Entrada)
class EntradaAdmin(admin.ModelAdmin):
    list_display = ('folio', 'fecha', 'tipo_entrada', 'institucion', 'fuente_financiamiento', 'recibido_por')
    list_filter = ('tipo_entrada', 'fecha', 'institucion', 'fuente_financiamiento')
    search_fields = ('folio', 'contrato', 'proceso')
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('almacen', 'institucion', 'fuente_financiamiento', 'recibido_por')


@admin.register(DetalleEntrada)
class DetalleEntradaAdmin(admin.ModelAdmin):
    list_display = ('entrada', 'medicamento', 'lote', 'caducidad', 'cantidad', 'precio_unitario', 'total')
    list_filter = ('caducidad', 'presentacion')
    search_fields = ('entrada__folio', 'medicamento__clave', 'medicamento__descripcion', 'lote')
    readonly_fields = ('total',)
    
    def total(self, obj):
        return f"${obj.total:,.2f}"
    total.short_description = 'Total'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('entrada', 'medicamento', 'presentacion')


@admin.register(Salida)
class SalidaAdmin(admin.ModelAdmin):
    list_display = ('id', 'lote', 'cantidad', 'fecha_hora', 'dia_semana')
    list_filter = ('fecha_hora',)
    search_fields = ('lote__id', 'lote__medicamento__descripcion')
    date_hierarchy = 'fecha_hora'
    ordering = ('-fecha_hora',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('lote__medicamento')


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'curp', 'fecha_nacimiento')
    search_fields = ('nombre_completo', 'curp')
    ordering = ('nombre_completo',)


@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    list_display = ('id_folio', 'paciente', 'fecha_emision', 'fecha_surtido', 'estado', 'origen', 'surtido_por')
    list_filter = ('estado', 'origen', 'fecha_surtido')
    search_fields = ('id_folio', 'paciente__nombre_completo')
    date_hierarchy = 'fecha_surtido'
    ordering = ('-fecha_surtido',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('paciente', 'surtido_por')


@admin.register(RecetaMedicamento)
class RecetaMedicamentoAdmin(admin.ModelAdmin):
    list_display = ('receta', 'medicamento', 'cantidad_solicitada', 'cantidad_surtida', 'precio_unitario', 'precio_total')
    list_filter = ('receta__fecha_surtido',)
    search_fields = ('receta__id_folio', 'medicamento__descripcion')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('receta', 'medicamento', 'lote')


@admin.register(CPMMedicamento)
class CPMMedicamentoAdmin(admin.ModelAdmin):
    list_display = ('medicamento', 'valor', 'actualizado_en', 'actualizado_por')
    search_fields = ('medicamento__clave', 'medicamento__descripcion')
    list_filter = ('actualizado_en',)
    ordering = ('-actualizado_en',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('medicamento', 'actualizado_por')


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')
    list_editable = ('activo',)


@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'telefono', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('codigo', 'nombre')
    list_editable = ('activo',)


@admin.register(FuenteFinanciamiento)
class FuenteFinanciamientoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')
    list_editable = ('activo',)


@admin.register(MedicamentoNoSurtido)
class MedicamentoNoSurtidoAdmin(admin.ModelAdmin):
    list_display = ('receta', 'medicamento_descripcion', 'cantidad_solicitada', 'motivo', 'registrado_por', 'fecha_registro')
    list_filter = ('fecha_registro',)
    search_fields = ('receta__id_folio', 'medicamento_descripcion', 'motivo')
    date_hierarchy = 'fecha_registro'
    ordering = ('-fecha_registro',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('receta', 'registrado_por')


# ===== PERSONALIZACIÓN DEL SITIO ADMIN =====
admin.site.site_header = 'INVENTFARM - Administración'
admin.site.site_title = 'INVENTFARM Admin'
admin.site.index_title = 'Panel de Administración del Hospital'
