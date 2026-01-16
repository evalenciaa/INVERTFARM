from django.contrib import admin
from .models import Colectivo, ColectivoMedicamento

@admin.register(Colectivo)
class ColectivoAdmin(admin.ModelAdmin):
    list_display = (
        'folio', 
        'tipo_colectivo', 
        'paciente', 
        'servicio', 
        'estado', 
        'fecha_solicitud', 
        'enfermero_solicitante',
        'farmaceutico_asignado'
    )
    list_filter = ('tipo_colectivo', 'estado', 'servicio', 'fecha_solicitud', 'turno')
    search_fields = (
        'folio', 
        'paciente__nombre_completo', 
        'servicio', 
        'numero_cama',
        'enfermero_solicitante__username',
        'farmaceutico_asignado__username'
    )
    readonly_fields = ('folio', 'fecha_solicitud', 'fecha_respuesta_farmacia', 'fecha_completado', 'created_at', 'updated_at')
    date_hierarchy = 'fecha_solicitud'
    ordering = ('-fecha_solicitud',)
    
    fieldsets = (
        ('Identificación', {
            'fields': ('folio', 'tipo_colectivo', 'estado')
        }),
        ('Información del Paciente', {
            'fields': ('paciente', 'numero_cama'),
            'description': 'Solo para colectivos de tipo PACIENTE'
        }),
        ('Información del Servicio', {
            'fields': ('servicio', 'turno'),
            'description': 'El turno solo aplica para colectivos de tipo STOCK'
        }),
        ('Responsables', {
            'fields': ('enfermero_solicitante', 'farmaceutico_asignado')
        }),
        ('Fechas', {
            'fields': ('fecha_solicitud', 'fecha_respuesta_farmacia', 'fecha_completado'),
            'classes': ('collapse',)
        }),
        ('Observaciones', {
            'fields': ('observaciones_enfermeria', 'respuesta_farmacia'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('paciente', 'enfermero_solicitante', 'farmaceutico_asignado')
    
    def has_add_permission(self, request):
        # Prevenir crear colectivos desde el admin
        return False


@admin.register(ColectivoMedicamento)
class ColectivoMedicamentoAdmin(admin.ModelAdmin):
    list_display = (
        'colectivo', 
        'medicamento', 
        'cantidad_solicitada', 
        'cantidad_surtida', 
        'disponible',
        'porcentaje_surtido_display'
    )
    list_filter = ('disponible', 'colectivo__estado', 'colectivo__tipo_colectivo')
    search_fields = (
        'colectivo__folio', 
        'medicamento__clave', 
        'medicamento__descripcion'
    )
    readonly_fields = ('created_at', 'updated_at', 'porcentaje_surtido')
    ordering = ('-created_at',)
    
    def porcentaje_surtido_display(self, obj):
        porcentaje = obj.porcentaje_surtido()
        if porcentaje >= 100:
            emoji = '🟢'
        elif porcentaje >= 50:
            emoji = '🟡'
        else:
            emoji = '🔴'
        return f"{emoji} {porcentaje}%"
    porcentaje_surtido_display.short_description = 'Surtido'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('colectivo', 'medicamento')


# ===== PERSONALIZACIÓN DEL SITIO ADMIN =====
admin.site.site_header = 'INVENTFARM - Administración'
admin.site.site_title = 'INVENTFARM Admin'
admin.site.index_title = 'Panel de Administración del Hospital'
