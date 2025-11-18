# tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum
from .models import Lote
from django.utils import timezone
from django.db.models import F, Value, IntegerField
from django.db.models.functions import Coalesce

@shared_task
def verificar_alertas_cpm():
    # Obtener inventario con CPM del medicamento
    inventario = Lote.objects.values(
        'medicamento__id',
        'medicamento__clave',
        'medicamento__descripcion',
    ).annotate(
        existencia_total=Sum('existencia'),
        cpm_medicamento=Coalesce(
            F('medicamento__cpm_medicamento__valor'),
            Value(0),
            output_field=IntegerField()
        )
    )
    
    alertas = []
    
    for item in inventario:
        if item['cpm_medicamento'] > 0 and item['existencia_total'] > 0:
            # Calcular porcentaje (existencia vs CPM)
            porcentaje = (item['existencia_total'] / item['cpm_medicamento']) * 100
            
            # Alerta al 50% del CPM
            if porcentaje <= 50:
                alertas.append({
                    'medicamento': item['medicamento__descripcion'],
                    'clave': item['medicamento__clave'],
                    'existencia': item['existencia_total'],
                    'cpm': item['cpm_medicamento'],
                    'porcentaje': round(porcentaje, 1)
                })
    
    # Enviar correo si hay alertas
    if alertas:
        asunto = f"⚠️ Alertas de Stock Bajo - {timezone.now().strftime('%d/%m/%Y')}"
        
        mensaje = "Se han detectado los siguientes medicamentos con stock bajo:\n\n"
        for alerta in alertas:
            mensaje += f"• {alerta['medicamento']} ({alerta['clave']})\n"
            mensaje += f"  Existencia: {alerta['existencia']} | CPM: {alerta['cpm']} | {alerta['porcentaje']}%\n\n"
        
        mensaje += "\nPor favor, revisar el inventario y realizar los pedidos necesarios."
        
        # Enviar correo (ajusta los destinatarios)
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            ['farmacia@hospital.com', 'almacen@hospital.com'],  # Reemplaza con los correos reales
            fail_silently=False,
        )
        
        return f"Alertas enviadas: {len(alertas)}"
    
    return "No hay alertas de stock"