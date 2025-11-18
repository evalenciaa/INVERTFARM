from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    UsuarioPersonalizado, PerfilUsuario, Departamento,
    Medicamento, Lote, Paciente, Entrada, 
    Salida, Receta, RecetaMedicamento,Presentacion, Proveedor, Almacen, Institucion, FuenteFinanciamiento
)

class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'rol', 'departamento', 'is_staff', 'is_active')
    list_filter = ('rol', 'departamento', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'telefono')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('rol', 'departamento', 'telefono'),
            'classes': ('collapse',)  # Opcional: para agrupar y colapsar
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('rol', 'departamento', 'telefono'),
        }),
    )
    
class LoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'medicamento', 'fecha_caducidad', 'existencia', 'color_alerta')
    list_filter = ('medicamento', 'fecha_caducidad')
    search_fields = ('id', 'medicamento__descripcion')
    readonly_fields = ('color_alerta', 'alerta_existencia')
    date_hierarchy = 'fecha_caducidad'

class RecetaAdmin(admin.ModelAdmin):
    list_display = ('id_folio', 'paciente', 'fecha_emision', 'origen', 'estado')
    list_filter = ('estado', 'origen')
    search_fields = ('id_folio', 'paciente__nombre_completo')
    raw_id_fields = ('paciente',)  # Para relaciones muchos-a-uno

class RecetaMedicamentoInline(admin.TabularInline):  # o admin.StackedInline
    model = RecetaMedicamento
    extra = 1

class RecetaAdmin(admin.ModelAdmin):
    inlines = [RecetaMedicamentoInline]

class PresentacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'unidades_por_caja')
    search_fields = ('nombre',)
    
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'telefono', 'email', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'rfc')
    ordering = ('nombre',)

class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ('clave', 'descripcion', 'proveedor', 'costo', 'activo')
    list_filter = ('proveedor', 'activo')
    search_fields = ('clave', 'descripcion', 'codigo_barras')
    ordering = ('clave',)

admin.site.register(UsuarioPersonalizado, UsuarioAdmin)
admin.site.register(PerfilUsuario)
admin.site.register(Departamento)
admin.site.register(Medicamento, MedicamentoAdmin)
admin.site.register(Lote, LoteAdmin)
admin.site.register(Paciente)
admin.site.register(Entrada)
admin.site.register(Salida)
admin.site.register(Receta, RecetaAdmin)
admin.site.register(Presentacion)
admin.site.register(Proveedor, ProveedorAdmin)
admin.site.register(Almacen)
admin.site.register(Institucion)
admin.site.register(FuenteFinanciamiento)
