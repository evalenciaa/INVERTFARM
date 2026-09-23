from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F, IntegerField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Lote


@shared_task(
    name='farmacia.tasks.enviar_alerta_stock_lote',
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def enviar_alerta_stock_lote(lote_id, cpm_real, existencia_total=None):
    from .models import enviar_alerta_stock

    lote = Lote.objects.select_related('medicamento', 'presentacion').get(pk=lote_id)
    enviar_alerta_stock(lote, cpm_real, existencia_total)
    return f'Alerta enviada para el lote {lote_id}'


@shared_task(name='farmacia.tasks.verificar_alertas_cpm')
def verificar_alertas_cpm():
    from .cpm import actualizar_todos_los_cpm

    # La alerta siempre parte del consumo real de los últimos tres meses.
    actualizar_todos_los_cpm()

    inventario = Lote.objects.values(
        'medicamento__id',
        'medicamento__clave',
        'medicamento__descripcion',
    ).annotate(
        existencia_total=Sum('existencia'),
        cpm_medicamento=Coalesce(
            F('medicamento__cpm_medicamento__valor'),
            Value(0),
            output_field=IntegerField(),
        ),
    )

    alertas = []
    for item in inventario:
        cpm = item['cpm_medicamento']
        existencia = item['existencia_total'] or 0
        if cpm > 0 and existencia <= cpm * 0.5:
            alertas.append({
                'medicamento': item['medicamento__descripcion'],
                'clave': item['medicamento__clave'],
                'existencia': existencia,
                'cpm': cpm,
                'porcentaje': round((existencia / cpm) * 100, 1),
            })

    if not alertas:
        return 'No hay alertas de stock'

    mensaje = 'Se detectaron medicamentos con stock bajo:\n\n'
    for alerta in alertas:
        mensaje += (
            f"- {alerta['medicamento']} ({alerta['clave']})\n"
            f"  Existencia: {alerta['existencia']} | CPM: {alerta['cpm']} | "
            f"{alerta['porcentaje']}%\n\n"
        )

    destinatarios = getattr(settings, 'ALERTAS_STOCK_DESTINATARIOS', [])
    if not destinatarios:
        return f'Alertas detectadas sin destinatarios configurados: {len(alertas)}'

    send_mail(
        f"Alertas de Stock Bajo - {timezone.now().strftime('%d/%m/%Y')}",
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        destinatarios,
        fail_silently=False,
    )
    return f'Alertas enviadas: {len(alertas)}'
