"""Compatibilidad con importaciones antiguas; usar farmacia.tasks."""
from .tasks import verificar_alertas_cpm

__all__ = ('verificar_alertas_cpm',)
