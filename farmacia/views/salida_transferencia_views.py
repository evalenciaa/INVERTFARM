import logging
import traceback

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from farmacia.models import Lote, Institucion, SalidaTransferencia, DetalleSalidaTransferencia, MedicamentoNoDisponibleTransferencia
from farmacia.pdf_utils import generar_pdf_transferencia

logger = logging.getLogger(__name__)


def _generar_folio_transferencia():
    fecha_str = timezone.now().strftime('%Y%m%d')
    ultimo = SalidaTransferencia.objects.filter(
        folio__startswith=f'TRF-{fecha_str}'
    ).order_by('-folio').first()
    num = int(ultimo.folio.split('-')[-1]) + 1 if ultimo else 1
    return f"TRF-{fecha_str}-{num:04d}"


@never_cache
@login_required(login_url='login')
@require_http_methods(['POST'])
@permission_required('farmacia.create_transferencia', raise_exception=True)
def registrar_salida_transferencia(request):
    institucion_id = request.POST.get('institucion_destino')
    institucion_nombre = request.POST.get('institucion_destino_nombre', '').strip()
    observaciones = request.POST.get('observaciones', '')

    if not institucion_id and not institucion_nombre:
        return JsonResponse({"success": False, "error": "Debe indicar una institución destino."}, status=400)

    items_para_guardar = []
    index = 0
    while True:
        lote_id = request.POST.get(f'item_lote_{index}')
        cantidad_str = request.POST.get(f'item_cantidad_{index}')
        if not lote_id or not cantidad_str:
            break
        try:
            lote = Lote.objects.get(id=lote_id)
            cantidad = int(cantidad_str)
            if cantidad <= 0:
                raise Exception(f"Cantidad inválida para {lote.lote_codigo}")
            if cantidad > lote.existencia:
                raise Exception(f"Stock insuficiente para {lote.lote_codigo}")
            items_para_guardar.append({'lote': lote, 'cantidad': cantidad})
            index += 1
        except (Lote.DoesNotExist, ValueError, Exception) as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    medicamentos_faltantes = []
    index = 0
    while True:
        faltante_desc = request.POST.get(f'faltante_desc_{index}')
        faltante_cant_str = request.POST.get(f'faltante_cant_{index}')
        faltante_motivo = request.POST.get(f'faltante_motivo_{index}')

        if not faltante_desc or not faltante_cant_str or not faltante_motivo:
            break

        try:
            medicamentos_faltantes.append({
                'descripcion': faltante_desc,
                'cantidad': int(faltante_cant_str),
                'motivo': faltante_motivo
            })
            index += 1
        except ValueError as e:
            return JsonResponse({
                "success": False,
                "error": f"Cantidad inválida para medicamento faltante: {str(e)}"
            }, status=400)

    if not items_para_guardar and not medicamentos_faltantes:
        return JsonResponse({
            "success": False,
            "error": "No hay medicamentos transferidos ni medicamentos no disponibles registrados."
        }, status=400)

    try:
        with transaction.atomic():
            if institucion_id:
                institucion = get_object_or_404(Institucion, pk=institucion_id)
            else:
                institucion, created = Institucion.objects.get_or_create(
                    nombre__iexact=institucion_nombre,
                    defaults={
                        'nombre': institucion_nombre,
                        'codigo': f"INST-{Institucion.objects.count() + 1:04d}",
                        'tipo': 'OTRO',
                        'activo': True
                    }
                )

            folio = _generar_folio_transferencia()

            transferencia = SalidaTransferencia.objects.create(
                folio=folio,
                institucion_destino=institucion,
                autorizado_por=request.user,
                observaciones=observaciones
            )

            for item in items_para_guardar:
                lote = item['lote']
                cantidad = item['cantidad']

                DetalleSalidaTransferencia.objects.create(
                    transferencia=transferencia,
                    lote=lote,
                    cantidad=cantidad,
                    costo_unitario=lote.costo_unitario
                )

                lote.existencia -= cantidad
                lote.save(update_fields=['existencia'])

            for faltante in medicamentos_faltantes:
                MedicamentoNoDisponibleTransferencia.objects.create(
                    transferencia=transferencia,
                    medicamento_descripcion=faltante['descripcion'],
                    cantidad_solicitada=faltante['cantidad'],
                    motivo=faltante['motivo'],
                    registrado_por=request.user
                )

            pdf_url = reverse('descargar_comprobante_transferencia', args=[transferencia.pk])

            return JsonResponse({
                "success": True,
                "message": f"Transferencia registrada: {folio}",
                "pdf_url": pdf_url,
                "items": len(items_para_guardar),
                "items_faltantes": len(medicamentos_faltantes)
            })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@permission_required('farmacia.view_transferencia', raise_exception=True)
def descargar_comprobante_transferencia(request, transferencia_id):
    try:
        transferencia = get_object_or_404(
            SalidaTransferencia.objects.select_related('institucion_destino', 'autorizado_por'),
            pk=transferencia_id
        )
        pdf_buffer = generar_pdf_transferencia(transferencia)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="transferencia_{transferencia.folio}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect('registrar_salida')