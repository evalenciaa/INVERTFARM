from django.contrib import admin
from .models import Colectivo, ColectivoMedicamento

class ColectivoMedicamentoInline(admin.TabularInline):
    model = ColectivoMedicamento
    extra = 1
    fields = ['medicamento', 'cantidad_solicitada', 'cantidad_surtida', 'disponible', 'comentario_farmacia']

@admin.register(Colectivo)
class ColectivoAdmin(admin.ModelAdmin):
    list_display = ['folio', 'paciente', 'enfermero_solicitante', 'estado', 'fecha_solicitud', 'numero_cama']
    list_filter = ['estado', 'fecha_solicitud', 'servicio']
    search_fields = ['folio', 'paciente__nombre', 'paciente__curp', 'numero_cama']
    readonly_fields = ['folio', 'created_at', 'updated_at']
    inlines = [ColectivoMedicamentoInline]
    
    fieldsets = (
        ('Información General', {
            'fields': ('folio', 'estado', 'paciente', 'numero_cama', 'servicio')
        }),
        ('Personal', {
            'fields': ('enfermero_solicitante', 'farmaceutico_asignado')
        }),
        ('Observaciones', {
            'fields': ('observaciones_enfermeria', 'respuesta_farmacia')
        }),
        ('Fechas', {
            'fields': ('fecha_solicitud', 'fecha_respuesta_farmacia', 'fecha_completado', 'created_at', 'updated_at')
        }),
    )

@admin.register(ColectivoMedicamento)
class ColectivoMedicamentoAdmin(admin.ModelAdmin):
    list_display = ['colectivo', 'medicamento', 'cantidad_solicitada', 'cantidad_surtida', 'disponible']
    list_filter = ['disponible', 'colectivo__estado']
    search_fields = ['medicamento__descripcion', 'colectivo__folio']