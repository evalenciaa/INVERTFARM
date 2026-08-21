"""
farmacia/views/salida_views.py
Vistas para registrar salidas, buscar pacientes y descargar comprobantes PDF/Excel.
"""
import json
import logging
import traceback
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from farmacia.decorators import group_required
from farmacia.forms import SalidaForm
from farmacia.models import (
    Lote, Paciente, Receta, RecetaMedicamento, MedicamentoNoSurtido, Institucion
)
from farmacia.pdf_utils import generar_pdf_salida

logger = logging.getLogger(__name__)


@never_cache
@login_required(login_url='login')
@permission_required('farmacia.create_salida', raise_exception=True)
def registrar_salida(request):
    if request.method == 'POST':
        curp = request.POST.get('paciente_curp', '').strip().upper()
        nombre = request.POST.get('paciente_nombre')
        nacimiento_str = request.POST.get('paciente_nacimiento')
        origen = request.POST.get('receta_origen')
        folio = request.POST.get('receta_folio')

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
            return JsonResponse({"success": False, "error": "No hay medicamentos en la lista ni medicamentos faltantes registrados."}, status=400)

        try:
            with transaction.atomic():
                try:
                    nacimiento_obj = datetime.strptime(nacimiento_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    return JsonResponse({"success": False, "error": "Fecha de nacimiento inválida."}, status=400)

                if curp:
                    paciente, _ = Paciente.objects.update_or_create(
                        curp=curp, defaults={'nombre_completo': nombre, 'fecha_nacimiento': nacimiento_obj}
                    )
                else:
                    paciente, _ = Paciente.objects.get_or_create(
                        nombre_completo=nombre, fecha_nacimiento=nacimiento_obj, defaults={'curp': None}
                    )

                if medicamentos_faltantes and items_para_guardar:
                    estado_receta = 'parcial'
                elif medicamentos_faltantes and not items_para_guardar:
                    estado_receta = 'no_surtida'
                else:
                    estado_receta = 'completa'

                if not folio:
                    fecha_str = timezone.now().strftime('%Y%m%d')
                    ultimo = Receta.objects.filter(id_folio__startswith=f'REC-{fecha_str}').order_by('-id_folio').first()
                    if ultimo:
                        ultimo_num = int(ultimo.id_folio.split('-')[-1])
                        folio = f"REC-{fecha_str}-{ultimo_num + 1:04d}"
                    else:
                        folio = f"REC-{fecha_str}-0001"

                receta_salida = Receta.objects.create(
                    id_folio=folio, paciente=paciente,
                    fecha_emision=timezone.now().date(), fecha_surtido=timezone.now().date(),
                    estado=estado_receta, origen=origen, surtido_por=request.user
                )

                for item in items_para_guardar:
                    lote = item['lote']
                    cantidad = item['cantidad']
                    precio_unitario = (lote.costo_unitario if lote else Decimal('0.00'))
                    precio_total = Decimal(cantidad) * precio_unitario
                    RecetaMedicamento.objects.create(
                        receta=receta_salida, medicamento=lote.medicamento,
                        lote=lote, cantidad_solicitada=cantidad, cantidad_surtida=cantidad,
                        precio_unitario=precio_unitario, precio_total=precio_total,
                    )
                    lote.existencia -= cantidad
                    lote.save(update_fields=['existencia'])

                for faltante in medicamentos_faltantes:
                    MedicamentoNoSurtido.objects.create(
                        receta=receta_salida, medicamento_descripcion=faltante['descripcion'],
                        cantidad_solicitada=faltante['cantidad'], motivo=faltante['motivo'],
                        registrado_por=request.user
                    )

            pdf_url = reverse('descargar_comprobante', args=[receta_salida.pk])
            mensaje_estado = {
                'completa': '✓ Todos los medicamentos fueron surtidos.',
                'parcial': '⚠ Surtido parcial. Algunos medicamentos no estaban disponibles.',
                'no_surtida': '✗ Ningún medicamento pudo ser surtido.'
            }
            return JsonResponse({
                "success": True, "message": f"Salida registrada: {folio}", "pdf_url": pdf_url,
                "estado": estado_receta, "mensaje_estado": mensaje_estado.get(estado_receta, ''),
                "items_surtidos": len(items_para_guardar), "items_faltantes": len(medicamentos_faltantes)
            })

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    form = SalidaForm()
    context = {
        'form': form,
        'instituciones': Institucion.objects.filter(activo=True),
        'titulo_pagina': 'Registro de Salidas'
    }
    return render(request, 'salida_medicamentos.html', context)


@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def descargar_comprobante(request, receta_id):
    try:
        receta = get_object_or_404(Receta.objects.select_related('paciente', 'surtido_por'), pk=receta_id)
        pdf_buffer = generar_pdf_salida(receta)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="salida_{receta.id_folio}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect('registrar_salida')


@login_required
@require_http_methods(['POST'])
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def generar_excel_salidas(request):
    try:
        data = json.loads(request.body)
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')

        if not fecha_inicio:
            fecha_inicio = timezone.now().replace(hour=0, minute=0, second=0)
        if not fecha_fin:
            fecha_fin = timezone.now().replace(hour=23, minute=59, second=59)

        salidas = RecetaMedicamento.objects.filter(
            receta__fecha_surtido__range=(fecha_inicio, fecha_fin)
        ).order_by('receta__fecha_surtido', 'lote__medicamento__descripcion')

        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte de Salidas"

        titulos = ['Fecha Surtido', 'Área', 'Médico/Quien Solicita', 'Clave', 'Medicamento', 'Lote', 'Cantidad Surtida']
        ws.append(titulos)

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for item in salidas:
            ws.append([
                item.receta.fecha_surtido.strftime('%d/%m/%Y %H:%M'),
                item.receta.area.nombre if item.receta.area else 'N/A',
                item.receta.medico, item.lote.medicamento.clave,
                item.lote.medicamento.descripcion, item.lote.lote_codigo,
                item.cantidad_surtida
            ])

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="REPORTE_SALIDAS_{fecha_inicio}_{fecha_fin}.xlsx"'
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_paciente_info_json(request, curp):
    if request.method == "GET":
        try:
            paciente = Paciente.objects.get(curp=curp.upper())
            data = {
                'id': paciente.id, 'nombre_completo': paciente.nombre_completo,
                'curp': paciente.curp, 'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%Y-%m-%d'),
            }
            return JsonResponse(data)
        except Paciente.DoesNotExist:
            return JsonResponse({'error': 'Paciente no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


def get_paciente_by_name(request, nombre):
    if request.method == "GET":
        try:
            paciente = Paciente.objects.filter(nombre_completo__iexact=nombre).first()
            if paciente:
                data = {
                    'id': paciente.id, 'nombre_completo': paciente.nombre_completo,
                    'curp': paciente.curp or '', 'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%Y-%m-%d'),
                }
                return JsonResponse(data)
            else:
                return JsonResponse({'error': 'Paciente no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)
