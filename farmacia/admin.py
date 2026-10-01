from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from .access import PERFILES, descripcion_perfil, sincronizar_perfil
from .models import (
    UsuarioPersonalizado, Departamento, Proveedor, Presentacion,
    Medicamento, Lote, Entrada, DetalleEntrada, Salida, Paciente,
    Receta, RecetaMedicamento, CPMMedicamento, Almacen, Institucion,
    FuenteFinanciamiento, MedicamentoNoSurtido, SalidaTransferencia,
    DetalleSalidaTransferencia, MedicamentoNoDisponibleTransferencia,
    CatalogoAntibioticosWHO, TrabajoRespaldo,
)


def _solo_equipo_ti(request):
    """El sitio administrativo completo está reservado a superusuarios de TI."""
    return bool(
        request.user.is_authenticated
        and request.user.is_active
        and request.user.is_superuser
    )


admin.site.has_permission = _solo_equipo_ti

# ===== USUARIO PERSONALIZADO =====
@admin.register(UsuarioPersonalizado)
class UsuarioPersonalizadoAdmin(UserAdmin):
    list_display = ('username', 'email', 'rol', 'departamento', 'is_active', 'is_staff')
    list_filter = ('rol', 'is_active', 'is_staff', 'departamento')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('Cuenta', {'fields': ('username', 'password')}),
        ('Datos personales', {'fields': ('first_name', 'last_name', 'email', 'departamento', 'telefono')}),
        ('Perfil operativo', {
            'fields': ('rol', 'requiere_cambio_contrasena'),
            'description': 'El perfil asigna automáticamente el único grupo y los permisos necesarios. '
                           'No se editan permisos por casillas.',
        }),
        ('Estado', {'fields': ('is_active', 'last_login', 'date_joined')}),
        ('Privilegios de TI', {
            'fields': ('is_staff', 'is_superuser'),
            'description': 'Reservados para integrantes del equipo de TI. Los usuarios operativos no usan Django Admin.',
        }),
    )

    add_fieldsets = (
        ('Cuenta temporal', {
            'fields': ('username', 'password1', 'password2'),
            'description': 'Asigna una contraseña temporal robusta. El usuario deberá reemplazarla al iniciar sesión.',
        }),
        ('Datos personales', {'fields': ('first_name', 'last_name', 'email', 'departamento', 'telefono')}),
        ('Perfil operativo', {
            'fields': ('rol',),
            'description': 'Selecciona un perfil; el sistema asignará sus permisos automáticamente.',
        }),
        ('Estado', {'fields': ('is_active',)}),
    )
    readonly_fields = ('last_login', 'date_joined', 'requiere_cambio_contrasena')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('departamento')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'rol' in form.base_fields and not (obj and obj.is_superuser):
            form.base_fields['rol'].choices = [
                (rol, etiqueta)
                for rol, etiqueta in UsuarioPersonalizado.ROLES
                if rol in PERFILES
            ]
        return form

    def save_model(self, request, obj, form, change):
        if not change and not obj.is_superuser:
            obj.requiere_cambio_contrasena = True
            obj.tokens_validos_desde = timezone.now()
        super().save_model(request, obj, form, change)
        sincronizar_perfil(obj)

    def user_change_password(self, request, id, form_url=''):
        response = super().user_change_password(request, id, form_url)
        if request.method == 'POST' and response.status_code == 302:
            usuario = self.get_object(request, id)
            if usuario and not usuario.is_superuser:
                usuario.requiere_cambio_contrasena = True
                usuario.tokens_validos_desde = timezone.now()
                usuario.save(update_fields=['requiere_cambio_contrasena', 'tokens_validos_desde'])
        return response


# ===== CONFIGURACIÓN MEJORADA DE GRUPOS =====
class GrupoConPermisosAdmin(admin.ModelAdmin):
    """Vista informativa: los perfiles se administran desde el usuario, no por casillas."""
    list_display = ('name', 'perfil', 'cantidad_permisos', 'cantidad_usuarios')
    search_fields = ('name',)
    fields = ('name', 'perfil', 'descripcion', 'permisos_resumen')
    readonly_fields = ('name', 'perfil', 'descripcion', 'permisos_resumen')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def perfil(self, obj):
        for rol, configuracion in PERFILES.items():
            if configuracion['grupo'] == obj.name:
                return dict(UsuarioPersonalizado.ROLES).get(rol, rol)
        return 'Grupo histórico (sin uso operativo)'
    perfil.short_description = 'Perfil'

    def descripcion(self, obj):
        for rol, configuracion in PERFILES.items():
            if configuracion['grupo'] == obj.name:
                return descripcion_perfil(rol)
        return 'No debe asignarse a usuarios operativos.'
    descripcion.short_description = 'Alcance'

    def permisos_resumen(self, obj):
        return ', '.join(
            permiso.name for permiso in obj.permissions.order_by('content_type__app_label', 'codename')
        ) or 'Sin permisos'
    permisos_resumen.short_description = 'Permisos aplicados automáticamente'
    
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


@admin.register(TrabajoRespaldo)
class TrabajoRespaldoAdmin(admin.ModelAdmin):
    """Historial técnico: se consulta, nunca se altera desde Django Admin."""
    list_display = ('tipo', 'estado', 'progreso', 'etapa', 'solicitado_por', 'creado_en', 'finalizado_en')
    list_filter = ('tipo', 'estado', 'creado_en')
    search_fields = ('identificador', 'solicitado_por', 'archivo_base_datos', 'error')
    readonly_fields = (
        'identificador', 'tipo', 'estado', 'solicitado_por', 'archivo_base_datos',
        'progreso', 'etapa', 'detalles', 'error', 'creado_en', 'iniciado_en', 'finalizado_en',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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


class RegistroOperativoSoloLecturaAdmin(admin.ModelAdmin):
    """Impide alterar evidencias generadas por los flujos operativos."""

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Entrada)
class EntradaAdmin(RegistroOperativoSoloLecturaAdmin):
    list_display = ('folio', 'fecha', 'tipo_entrada', 'institucion', 'fuente_financiamiento', 'recibido_por')
    list_filter = ('tipo_entrada', 'fecha', 'institucion', 'fuente_financiamiento')
    search_fields = ('folio', 'contrato', 'proceso')
    ordering = ('-fecha',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('almacen', 'institucion', 'fuente_financiamiento', 'recibido_por')


@admin.register(DetalleEntrada)
class DetalleEntradaAdmin(RegistroOperativoSoloLecturaAdmin):
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
class MedicamentoNoSurtidoAdmin(RegistroOperativoSoloLecturaAdmin):
    list_display = ('receta', 'medicamento_descripcion', 'cantidad_solicitada', 'motivo', 'registrado_por', 'fecha_registro')
    list_filter = ('fecha_registro',)
    search_fields = ('receta__id_folio', 'medicamento_descripcion', 'motivo')
    ordering = ('-fecha_registro',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('receta', 'registrado_por')


@admin.register(SalidaTransferencia)
class SalidaTransferenciaAdmin(RegistroOperativoSoloLecturaAdmin):
    list_display = ('folio', 'institucion_destino', 'fecha', 'autorizado_por')
    list_filter = ('fecha', 'institucion_destino')
    search_fields = ('folio', 'institucion_destino__nombre', 'autorizado_por__username')
    ordering = ('-fecha',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'institucion_destino', 'autorizado_por'
        )


@admin.register(DetalleSalidaTransferencia)
class DetalleSalidaTransferenciaAdmin(RegistroOperativoSoloLecturaAdmin):
    list_display = ('transferencia', 'lote', 'cantidad', 'costo_unitario', 'total')
    search_fields = (
        'transferencia__folio', 'lote__id', 'lote__medicamento__clave',
        'lote__medicamento__descripcion',
    )

    def total(self, obj):
        return f"${obj.total:,.2f}"
    total.short_description = 'Total'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'transferencia__institucion_destino', 'lote__medicamento'
        )


@admin.register(MedicamentoNoDisponibleTransferencia)
class MedicamentoNoDisponibleTransferenciaAdmin(RegistroOperativoSoloLecturaAdmin):
    list_display = (
        'transferencia', 'medicamento_descripcion', 'cantidad_solicitada',
        'registrado_por', 'fecha_registro',
    )
    list_filter = ('fecha_registro',)
    search_fields = ('transferencia__folio', 'medicamento_descripcion', 'motivo')
    ordering = ('-fecha_registro',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'transferencia', 'registrado_por'
        )


@admin.register(CatalogoAntibioticosWHO)
class CatalogoAntibioticosWHOAdmin(admin.ModelAdmin):
    """Catálogo mantenible por TI para clasificar antibióticos AWaRe/ATC."""
    list_display = ('codigo_atc', 'categoria_aware', 'valor_atc', 'fuente_valor_atc')
    list_filter = ('categoria_aware', 'fuente_valor_atc')
    search_fields = ('codigo_atc',)
    ordering = ('codigo_atc',)


# ===== PERSONALIZACIÓN DEL SITIO ADMIN =====
admin.site.site_header = 'INVENTFARM - Administración'
admin.site.site_title = 'INVENTFARM Admin'
admin.site.index_title = 'Panel de Administración del Hospital'
