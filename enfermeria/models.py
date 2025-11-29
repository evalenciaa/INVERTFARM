from django.db import models
from django.conf import settings
from farmacia.models import Medicamento, Paciente
from django.utils import timezone
from django.core.validators import MinValueValidator

# Create your models here.


class Colectivo(models.Model):
    """
    Solicitud de medicamentos de Enfermería a Farmacia
    """
    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('EN_REVISION', 'En Revisión'),
        ('RESPONDIDO', 'Respondido'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    )
    
    # Identificación
    folio = models.CharField(max_length=50, unique=True, editable=False)
    
    # Relaciones
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name='colectivos')
    enfermero_solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        related_name='colectivos_solicitados',
        limit_choices_to={'rol': 'ENFERMERIA'}
    )
    farmaceutico_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colectivos_atendidos',
        limit_choices_to={'rol': 'FARMACIA'}
    )
    
    # Información del paciente
    numero_cama = models.CharField(max_length=20)
    servicio = models.CharField(max_length=100, help_text="Ej: Urgencias, Piso 2, UCI")
    
    # Fechas y estado
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_respuesta_farmacia = models.DateTimeField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # Observaciones
    observaciones_enfermeria = models.TextField(blank=True, help_text="Indicaciones especiales")
    respuesta_farmacia = models.TextField(blank=True, help_text="Comentarios sobre disponibilidad")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Colectivo'
        verbose_name_plural = 'Colectivos'
    
    def __str__(self):
        return f"{self.folio} - {self.paciente.nombre} ({self.get_estado_display()})"
    
    def save(self, *args, **kwargs):
        if not self.folio:
            # Generar folio: COL-YYYYMMDD-0001
            fecha = timezone.now().strftime('%Y%m%d')
            ultimo = Colectivo.objects.filter(
                folio__startswith=f'COL-{fecha}'
            ).order_by('-folio').first()
            
            if ultimo:
                ultimo_num = int(ultimo.folio.split('-')[-1])
                nuevo_num = ultimo_num + 1
            else:
                nuevo_num = 1
            
            self.folio = f'COL-{fecha}-{nuevo_num:04d}'
        
        super().save(*args, **kwargs)
    
    def get_color_estado(self):
        """Retorna color para semaforización"""
        colores = {
            'PENDIENTE': '#FFA500',      # Naranja
            'EN_REVISION': '#1E90FF',    # Azul
            'RESPONDIDO': '#FFD700',     # Amarillo/Dorado
            'COMPLETADO': '#28A745',     # Verde
            'CANCELADO': '#DC3545',      # Rojo
        }
        return colores.get(self.estado, '#6C757D')
    
    def total_medicamentos(self):
        """Total de medicamentos solicitados"""
        return self.medicamentos.count()
    
    def medicamentos_disponibles(self):
        """Medicamentos marcados como disponibles"""
        return self.medicamentos.filter(disponible=True).count()


class ColectivoMedicamento(models.Model):
    """
    Medicamentos incluidos en un colectivo
    """
    colectivo = models.ForeignKey(Colectivo, on_delete=models.CASCADE, related_name='medicamentos')
    medicamento = models.ForeignKey(Medicamento, on_delete=models.PROTECT)
    
    cantidad_solicitada = models.IntegerField(validators=[MinValueValidator(1)])
    cantidad_surtida = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    disponible = models.BooleanField(default=True, help_text="¿Farmacia tiene este medicamento?")
    comentario_farmacia = models.TextField(blank=True, help_text="Ej: Stock insuficiente, cambiar por...")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['medicamento__descripcion']
        verbose_name = 'Medicamento del Colectivo'
        verbose_name_plural = 'Medicamentos del Colectivo'
        unique_together = ['colectivo', 'medicamento']
    
    def __str__(self):
        return f"{self.medicamento.descripcion} - {self.cantidad_solicitada} unidades"
    
    def porcentaje_surtido(self):
        """Porcentaje surtido vs solicitado"""
        if self.cantidad_solicitada == 0:
            return 0
        return (self.cantidad_surtida / self.cantidad_solicitada) * 100