from django.db import models
from django.conf import settings
from farmacia.models import Medicamento, Paciente
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
import html

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
    Medicamentos incluidos en un colectivo
    """
    colectivo = models.ForeignKey(
        Colectivo, 
        on_delete=models.CASCADE, 
        related_name='medicamentos'  # ← Este es el nombre correcto
    )
    medicamento = models.ForeignKey(
        'farmacia.Medicamento',  # ← Mejor usar string para evitar imports circulares
        on_delete=models.PROTECT
    )
    
    cantidad_solicitada = models.PositiveIntegerField(
        verbose_name='Cantidad Solicitada',
        validators=[MinValueValidator(1)]
    )
    cantidad_surtida = models.PositiveIntegerField(
        default=0,
        verbose_name='Cantidad Surtida',
        validators=[MinValueValidator(0)]
    )
    
    disponible = models.BooleanField(
        default=True,
        verbose_name='Disponible en Farmacia',
        help_text="¿Farmacia tiene este medicamento?"
    )
    
    # ✅ Mantener ambos campos de comentarios por si acaso
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
        help_text="Comentarios generales sobre este medicamento"
    )
    comentario_farmacia = models.TextField(
        blank=True,
        verbose_name='Comentario de Farmacia',
        help_text="Ej: Stock insuficiente, cambiar por..."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['medicamento__descripcion']
        verbose_name = 'Medicamento del Colectivo'
        verbose_name_plural = 'Medicamentos del Colectivo'
        unique_together = ['colectivo', 'medicamento']
    
    def __str__(self):
        return f"{self.medicamento.clave} - {self.cantidad_solicitada} unidades"
    
    def porcentaje_surtido(self):
        """Porcentaje surtido vs solicitado"""
        if self.cantidad_solicitada == 0:
            return 0
        return int((self.cantidad_surtida / self.cantidad_solicitada) * 100)




def enviar_notificacion_colectivo(colectivo):
    """
    Enviar correo de notificación cuando se crea un nuevo colectivo
    """
    # Solo enviar si el colectivo está PENDIENTE (recién creado)
    if colectivo.estado != 'PENDIENTE':
        return
    
    # Determinar color según tipo
    if colectivo.tipo_colectivo == 'PACIENTE':
        color = "#3498db"  # Azul
        icono = "👤"
        tipo_texto = "Colectivo para Paciente"
    else:
        color = "#9b59b6"  # Morado
        icono = "📦"
        tipo_texto = "Colectivo para Stock"
    
    # Escapar datos para HTML
    folio_safe = html.escape(colectivo.folio)
    servicio_safe = html.escape(str(colectivo.servicio))
    enfermero_safe = html.escape(colectivo.enfermero_solicitante.get_full_name() or colectivo.enfermero_solicitante.username)
    
    # Información específica según tipo
    if colectivo.tipo_colectivo == 'PACIENTE':
        paciente_safe = html.escape(colectivo.paciente.nombre_completo)
        cama_safe = html.escape(colectivo.numero_cama)
        info_especifica = f"""
            <div class="info-row">
                <span class="label">Paciente:</span>
                <span class="value">{paciente_safe}</span>
            </div>
            <div class="info-row">
                <span class="label">Número de Cama:</span>
                <span class="value">{cama_safe}</span>
            </div>
        """
    else:
        turno_safe = html.escape(colectivo.get_turno_display())
        info_especifica = f"""
            <div class="info-row">
                <span class="label">Turno Solicitante:</span>
                <span class="value">{turno_safe}</span>
            </div>
        """
    
    # Obtener medicamentos del colectivo
    medicamentos = colectivo.medicamentos.all()
    total_medicamentos = medicamentos.count()
    
    medicamentos_html = ""
    for med in medicamentos:
        med_desc = html.escape(med.medicamento.descripcion)
        med_clave = html.escape(med.medicamento.clave)
        medicamentos_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ecf0f1;">
                    <strong>{med_clave}</strong><br>
                    <small style="color: #7f8c8d;">{med_desc}</small>
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #ecf0f1; text-align: center;">
                    <strong style="color: {color}; font-size: 16px;">{med.cantidad_solicitada}</strong>
                </td>
            </tr>
        """
    
    # Observaciones (si existen)
    observaciones_html = ""
    if colectivo.observaciones_enfermeria:
        obs_safe = html.escape(colectivo.observaciones_enfermeria)
        observaciones_html = f"""
            <div class="info-box">
                <h3>💬 Observaciones</h3>
                <p style="margin: 0; color: #555;">{obs_safe}</p>
            </div>
        """
    
    asunto = f"📋 Nuevo Colectivo: {colectivo.folio} - {colectivo.servicio}"
    
    # Mensaje en texto plano
    mensaje_texto = f"""
    NUEVO COLECTIVO RECIBIDO
    
    Fecha: {now().strftime('%d/%m/%Y %H:%M')}
    
    INFORMACIÓN GENERAL:
    - Folio: {colectivo.folio}
    - Tipo: {tipo_texto}
    - Servicio: {colectivo.servicio}
    - Estado: PENDIENTE
    
    {'PACIENTE: ' + colectivo.paciente.nombre_completo if colectivo.tipo_colectivo == 'PACIENTE' else 'TURNO: ' + colectivo.get_turno_display()}
    {'Cama: ' + colectivo.numero_cama if colectivo.tipo_colectivo == 'PACIENTE' else ''}
    
    MEDICAMENTOS SOLICITADOS: {total_medicamentos}
    {''.join([f'- {m.medicamento.clave}: {m.cantidad_solicitada} unidades\n' for m in medicamentos])}
    
    SOLICITANTE:
    - Enfermero: {colectivo.enfermero_solicitante.get_full_name() or colectivo.enfermero_solicitante.username}
    
    {f'OBSERVACIONES:\n{colectivo.observaciones_enfermeria}' if colectivo.observaciones_enfermeria else ''}
    
    ---
    Sistema de Gestión - Farmacia Hospitalaria
    Por favor procesar este colectivo a la brevedad.
    """
    
    # Mensaje en HTML
    mensaje_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 650px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, {color} 0%, {color}dd 100%);
                color: white;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 26px;
                font-weight: 600;
            }}
            .header .folio {{
                display: inline-block;
                background: rgba(255,255,255,0.2);
                padding: 8px 20px;
                border-radius: 25px;
                margin-top: 15px;
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            .badge {{
                display: inline-block;
                background: rgba(255,255,255,0.3);
                padding: 5px 12px;
                border-radius: 15px;
                font-size: 12px;
                margin-top: 10px;
                font-weight: 600;
            }}
            .content {{
                padding: 25px;
            }}
            .timestamp {{
                text-align: center;
                color: #7f8c8d;
                font-size: 14px;
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 2px solid #ecf0f1;
            }}
            .info-box {{
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                border-radius: 10px;
                border-left: 5px solid {color};
            }}
            .info-box h3 {{
                margin-top: 0;
                color: {color};
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 15px;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #e9ecef;
            }}
            .info-row:last-child {{
                border-bottom: none;
            }}
            .label {{
                font-weight: 600;
                color: #555;
                font-size: 14px;
            }}
            .value {{
                color: #333;
                font-size: 14px;
                text-align: right;
            }}
            .medicamentos-section {{
                margin: 25px 0;
            }}
            .medicamentos-section h3 {{
                color: {color};
                font-size: 18px;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .counter {{
                background: {color};
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            th {{
                background: {color};
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #ecf0f1;
            }}
            tr:last-child td {{
                border-bottom: none;
            }}
            .alert-box {{
                background: #fff3cd;
                border: 2px solid #ffc107;
                padding: 20px;
                border-radius: 10px;
                margin: 25px 0;
                text-align: center;
            }}
            .alert-box strong {{
                color: #856404;
                font-size: 16px;
                display: block;
                margin-bottom: 5px;
            }}
            .alert-box p {{
                color: #856404;
                margin: 0;
                font-size: 14px;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                background: #f8f9fa;
                color: #7f8c8d;
                font-size: 12px;
                border-top: 1px solid #e9ecef;
            }}
            .footer strong {{
                color: #555;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{icono} NUEVO COLECTIVO RECIBIDO</h1>
                <div class="folio">{folio_safe}</div>
                <div class="badge">ESTADO: PENDIENTE</div>
            </div>
            
            <div class="content">
                <div class="timestamp">
                    📅 Recibido el {now().strftime('%d de %B de %Y a las %H:%M hrs')}
                </div>
                
                <div class="info-box">
                    <h3>📋 Información General</h3>
                    <div class="info-row">
                        <span class="label">Tipo de Colectivo:</span>
                        <span class="value">{tipo_texto}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Servicio:</span>
                        <span class="value">{servicio_safe}</span>
                    </div>
                    {info_especifica}
                </div>
                
                <div class="medicamentos-section">
                    <h3>💊 Medicamentos Solicitados <span class="counter">{total_medicamentos}</span></h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Medicamento</th>
                                <th style="text-align: center; width: 120px;">Cantidad</th>
                            </tr>
                        </thead>
                        <tbody>
                            {medicamentos_html}
                        </tbody>
                    </table>
                </div>
                
                {observaciones_html}
                
                <div class="info-box">
                    <h3>👤 Solicitante</h3>
                    <div class="info-row">
                        <span class="label">Enfermero:</span>
                        <span class="value">{enfermero_safe}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Departamento:</span>
                        <span class="value">{servicio_safe}</span>
                    </div>
                </div>
                
                <div class="alert-box">
                    <strong>⚡ ACCIÓN REQUERIDA</strong>
                    <p>Por favor procesar este colectivo a la brevedad</p>
                </div>
            </div>
            
            <div class="footer">
                <strong>Sistema de Gestión - Farmacia Hospitalaria</strong><br>
                Este es un mensaje automático, por favor no responder.
            </div>
        </div>
    </body>
    </html>
    """
    
    # Enviar correo
    try:
        msg = EmailMultiAlternatives(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            ['HMICFarmacia@gmail.com']  # ← Cambia por el correo de farmacia
        )
        msg.attach_alternative(mensaje_html, "text/html")
        msg.send()
        print(f"✅ Notificación enviada para colectivo {colectivo.folio}")
    except Exception as e:
        print(f"❌ Error al enviar notificación: {e}")


'''@receiver(post_save, sender=Colectivo)
def notificar_nuevo_colectivo(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta cuando se crea un nuevo colectivo
    """
    if created:  # Solo cuando se crea por primera vez
        enviar_notificacion_colectivo(instance)'''
