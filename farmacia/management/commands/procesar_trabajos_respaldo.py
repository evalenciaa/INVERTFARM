"""Procesa una solicitud pendiente de respaldos en un proceso separado."""
from django.core.management.base import BaseCommand, CommandError

from farmacia.models import TrabajoRespaldo
from farmacia.views.backup_views import procesar_siguiente_trabajo_respaldo


class Command(BaseCommand):
    help = 'Procesa como máximo un trabajo pendiente de creación o restauración de respaldos.'

    def handle(self, *args, **options):
        trabajo = procesar_siguiente_trabajo_respaldo()
        if trabajo is None:
            self.stdout.write('No hay trabajos pendientes de respaldos.')
            return
        if trabajo.estado == TrabajoRespaldo.Estado.ERROR:
            raise CommandError(
                f'Trabajo {trabajo.identificador} finalizó con error: {trabajo.error}'
            )
        self.stdout.write(self.style.SUCCESS(
            f'Trabajo {trabajo.identificador} completado correctamente.'
        ))
