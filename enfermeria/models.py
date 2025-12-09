from django.db import models
from django.conf import settings
from farmacia.models import Medicamento, Paciente
from django.utils import timezone
from django.core.validators import MinValueValidator

# Create your models here.


class Colectivo(models.Model):
    """
    Solicitud de medicamentos de Enfermería a Farmacia
    Puede ser para un paciente específico o para resurtir stock del servicio
    """
    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('EN_REVISION', 'En Revisión'),
        ('RESPONDIDO', 'Respondido'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    )
    
    # ✅ NUEVO: Tipo de colectivo
    TIPO_COLECTIVO = (
        ('PACIENTE', 'Colectivo para Paciente'),
        ('STOCK', 'Colectivo para Stock'),
    )
    
    # ✅ NUEVO: Turnos (solo para stock)
    TURNOS = (
        ('MATUTINO', 'Matutino'),
        ('VESPERTINO', 'Vespertino'),
        ('NOCTURNO', 'Nocturno'),
    )
    
    # Identificación
    folio = models.CharField(max_length=50, unique=True, editable=False)
    
    # ✅ NUEVO: Tipo de colectivo
    tipo_colectivo = models.CharField(
        max_length=20,
        choices=TIPO_COLECTIVO,
        default='PACIENTE',
        verbose_name='Tipo de Colectivo'
    )
    
    # ===== DATOS PARA COLECTIVO DE PACIENTE =====
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name='colectivos',
        null=True,  # ✅ Ahora puede ser NULL si es tipo STOCK
        blank=True
    )
    numero_cama = models.CharField(
        max_length=20,
        blank=True,  # ✅ Solo requerido para tipo PACIENTE
        null=True
    )
    
    # ===== DATOS COMUNES A AMBOS TIPOS =====
    servicio = models.CharField(
        max_length=100,
        help_text="Ej: Urgencias, Piso 2, UCI, Quirófano"
    )
    
    # ===== DATOS PARA COLECTIVO DE STOCK =====
    turno = models.CharField(
        max_length=20,
        choices=TURNOS,
        blank=True,  # ✅ Solo requerido para tipo STOCK
        null=True,
        verbose_name='Turno Solicitante'
    )
    
    # ===== RELACIONES =====
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
    
    # ===== FECHAS Y ESTADO =====
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_respuesta_farmacia = models.DateTimeField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # ===== OBSERVACIONES =====
    observaciones_enfermeria = models.TextField(
        blank=True,
        help_text="Indicaciones especiales"
    )
    respuesta_farmacia = models.TextField(
        blank=True,
        help_text="Comentarios sobre disponibilidad"
    )
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Colectivo'
        verbose_name_plural = 'Colectivos'
        indexes = [
            models.Index(fields=['tipo_colectivo', 'estado']),
            models.Index(fields=['fecha_solicitud']),
        ]
    
    def __str__(self):
        if self.tipo_colectivo == 'PACIENTE':
            return f"{self.folio} - {self.paciente.nombre} ({self.get_estado_display()})"
        else:
            return f"{self.folio} - Stock {self.servicio} - {self.get_turno_display()} ({self.get_estado_display()})"
    
    def save(self, *args, **kwargs):
        if not self.folio:
            # Generar folio con prefijo según tipo
            fecha = timezone.now().strftime('%Y%m%d')
            
            if self.tipo_colectivo == 'STOCK':
                prefijo = 'STK'
            else:
                prefijo = 'COL'
            
            ultimo = Colectivo.objects.filter(
                folio__startswith=f'{prefijo}-{fecha}'
            ).order_by('-folio').first()
            
            if ultimo:
                ultimo_num = int(ultimo.folio.split('-')[-1])
                nuevo_num = ultimo_num + 1
            else:
                nuevo_num = 1
            
            self.folio = f'{prefijo}-{fecha}-{nuevo_num:04d}'
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validaciones personalizadas según el tipo"""
        from django.core.exceptions import ValidationError
        
        if self.tipo_colectivo == 'PACIENTE':
            # Validar campos requeridos para paciente
            if not self.paciente:
                raise ValidationError({
                    'paciente': 'El paciente es obligatorio para colectivos de tipo PACIENTE'
                })
            if not self.numero_cama:
                raise ValidationError({
                    'numero_cama': 'El número de cama es obligatorio para colectivos de tipo PACIENTE'
                })
        
        elif self.tipo_colectivo == 'STOCK':
            # Validar campos requeridos para stock
            if not self.turno:
                raise ValidationError({
                    'turno': 'El turno es obligatorio para colectivos de tipo STOCK'
                })
    
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
    
    def get_icono_tipo(self):
        """Retorna icono según el tipo de colectivo"""
        if self.tipo_colectivo == 'PACIENTE':
            return 'fa-user-injured'
        else:
            return 'fa-boxes'
    
    def total_medicamentos(self):
        """Total de medicamentos solicitados"""
        return self.medicamentos.count()
    
    def medicamentos_disponibles(self):
        """Medicamentos marcados como disponibles"""
        return self.medicamentos.filter(disponible=True).count()


class ColectivoMedicamento(models.Model):
    """
    Relación entre Colectivo y Medicamento con cantidades
    """
    colectivo = models.ForeignKey(
        Colectivo,
        on_delete=models.CASCADE,
        related_name='medicamentos'
    )
    medicamento = models.ForeignKey(
        'farmacia.Medicamento',
        on_delete=models.PROTECT
    )
    cantidad_solicitada = models.PositiveIntegerField(
        verbose_name='Cantidad Solicitada'
    )
    cantidad_surtida = models.PositiveIntegerField(
        default=0,
        verbose_name='Cantidad Surtida'
    )
    disponible = models.BooleanField(
        default=True,
        verbose_name='Disponible en Farmacia'
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Comentarios sobre este medicamento"
    )
    
    class Meta:
        verbose_name = 'Medicamento del Colectivo'
        verbose_name_plural = 'Medicamentos del Colectivo'
        unique_together = ['colectivo', 'medicamento']
    
    def __str__(self):
        return f"{self.medicamento.clave} - {self.cantidad_solicitada} unidades"
    
    def porcentaje_surtido(self):
        """Retorna el porcentaje surtido"""
        if self.cantidad_solicitada == 0:
            return 0
        return int((self.cantidad_surtida / self.cantidad_solicitada) * 100)
    


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