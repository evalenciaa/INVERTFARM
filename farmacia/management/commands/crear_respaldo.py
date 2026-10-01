"""Encola y ejecuta una copia verificable programada en Windows Server."""
from django.core.management.base import BaseCommand, CommandError

from farmacia.models import TrabajoRespaldo
from farmacia.views.backup_views import (
    _solicitar_trabajo, procesar_siguiente_trabajo_respaldo,
)


class Command(BaseCommand):
    help = 'Encola y ejecuta una copia verificable de base de datos y media.'

    def add_arguments(self, parser):
        parser.add_argument('--motivo', default='programado', help='Motivo registrado en la bitácora.')

    def handle(self, *args, **options):
        trabajo, creado = _solicitar_trabajo(
            TrabajoRespaldo.Tipo.CREAR,
            solicitado_por=f"tarea:{options['motivo'][:80]}",
        )
        if not creado:
            raise CommandError(
                f'Ya existe un trabajo de respaldos {trabajo.get_estado_display().lower()}. '
                'No se iniciará una copia simultánea.'
            )
        resultado = procesar_siguiente_trabajo_respaldo()
        if resultado is None:
            raise CommandError('La cola no pudo asignar el respaldo programado.')
        if resultado.estado == TrabajoRespaldo.Estado.ERROR:
            raise CommandError(f'No se pudo crear el respaldo: {resultado.error}')
        self.stdout.write(self.style.SUCCESS(
            f'Respaldo completado: {resultado.detalles.get("base_datos", "sin nombre")}. '
            'La réplica externa fue procesada.'
        ))
