from django.db import models
from django.conf import settings
from django.utils import timezone

class Bitacora(models.Model):
    ACCIONES = (
        ('CREAR', 'Creación'),
        ('EDITAR', 'Edición'),
        ('ELIMINAR', 'Eliminación'),
        ('ACCESO', 'Login/Acceso'),
        ('SALIDA', 'Logout'),
    )

    # ¿Quién?
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Si borran al usuario, el log queda (vital para auditoría)
        null=True,
        related_name='logs_auditoria'
    )
    usuario_texto = models.CharField(max_length=150, help_text="Respaldo del nombre por si se borra el usuario")

    # ¿Qué hizo?
    accion = models.CharField(max_length=20, choices=ACCIONES)
    modelo_afectado = models.CharField(max_length=100, help_text="Ej: Medicamento, Colectivo")
    id_objeto = models.CharField(max_length=50, null=True, blank=True, help_text="ID del registro afectado")
    
    # ¿Qué cambió? (La carnita del asunto)
    detalles = models.JSONField(default=dict, blank=True, null=True) 
    # Aquí guardaremos: {'campo': 'stock', 'antes': 50, 'despues': 40}

    # ¿Desde dónde y cuándo?
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Bitácora del Sistema'
        ordering = ['-fecha_hora']
        # Índices para búsquedas rápidas en auditorías
        indexes = [
            models.Index(fields=['fecha_hora']),
            models.Index(fields=['usuario']),
            models.Index(fields=['accion']),
        ]

    def __str__(self):
        return f"{self.fecha_hora.strftime('%d/%m/%Y %H:%M')} - {self.usuario_texto} - {self.accion}"