"""
farmacia/views/colectivo_views.py
Vistas para la farmacia que gestiona los colectivos de enfermería.
"""
import os
import traceback
from datetime import date
from decimal import Decimal
from html import escape
from io import BytesIO

from openpyxl.styles import Alignment  # No se usa en esta, pero si hiciera un excel
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from enfermeria.models import Colectivo, ColectivoMedicamento
from farmacia.decorators import group_required
from farmacia.models import Lote, Receta, Paciente, RecetaMedicamento
from farmacia.services import surtir_fefo
from farmacia.views.inventario_views import truncar_texto


def ids_colectivos_antibioticos():
    """IDs de colectivos con al menos un medicamento antibiótico o con código ATC."""
    return ColectivoMedicamento.objects.filter(
        Q(medicamento__es_antibiotico=True) |
        (Q(medicamento__codigo_atc__isnull=False) & ~Q(medicamento__codigo_atc=''))
    ).values('colectivo_id')


def colectivos_por_modulo(antibioticos=False):
    """Separa los colectivos generales de los colectivos de antibióticos."""
    colectivos = Colectivo.objects.all()
    if antibioticos:
        return colectivos.filter(id__in=ids_colectivos_antibioticos())
    return colectivos.exclude(id__in=ids_colectivos_antibioticos())


@login_required(login_url='login')
@require_http_methods(['GET'])
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
@permission_required('enfermeria.view_colectivo', raise_exception=True)
def lista_colectivos_farmacia(request, antibioticos=False):
    """Vista de lista de colectivos para farmacia"""
    colectivos_base = colectivos_por_modulo(antibioticos)
    colectivos = colectivos_base.select_related(
        'paciente', 'enfermero_solicitante', 'farmaceutico_asignado'
    ).order_by('-fecha_solicitud')
    
    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')
    
    if estado_filtro:
        colectivos = colectivos.filter(estado=estado_filtro)
    
    if busqueda:
        colectivos = colectivos.filter(
            Q(folio__icontains=busqueda) |
            Q(paciente__nombre_completo__icontains=busqueda) |
            Q(numero_cama__icontains=busqueda) | Q(servicio__icontains=busqueda) |
            Q(enfermero_solicitante__username__icontains=busqueda)
        )
    
    now_local = timezone.localtime(timezone.now())
    hoy_inicio = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    hoy_fin = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    stats = {
        'total': colectivos_base.count(),
        'pendientes': colectivos_base.filter(estado='PENDIENTE').count(),
        'en_revision': colectivos_base.filter(estado='EN_REVISION').count(),
        'respondidos': colectivos_base.filter(estado='RESPONDIDO').count(),
        'completados_hoy': colectivos_base.filter(
            estado='COMPLETADO', fecha_completado__gte=hoy_inicio, fecha_completado__lte=hoy_fin
        ).count(),
    }
    
    template = (
        'lista_colectivos_antibioticos_farmacia.html'
        if antibioticos else 'lista_colectivos_farmacia.html'
    )
    return render(request, template, {
        'colectivos': colectivos, 'stats': stats,
        'estado_filtro': estado_filtro, 'busqueda': busqueda,
        'modulo_antibioticos': antibioticos,
    })


def lista_colectivos_antibioticos_farmacia(request):
    return lista_colectivos_farmacia(request, antibioticos=True)


@never_cache
@login_required(login_url='login')
@require_http_methods(['GET'])
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
@permission_required('enfermeria.view_colectivo', raise_exception=True)
def detalle_colectivo_farmacia(request, colectivo_id, antibioticos=False):
    """Vista de detalle de un colectivo para farmacia"""
    colectivo = get_object_or_404(
        colectivos_por_modulo(antibioticos).select_related(
            'paciente', 'enfermero_solicitante'
        ),
        id=colectivo_id
    )

    if colectivo.estado == 'PENDIENTE':
        colectivo.estado = 'EN_REVISION'
        colectivo.farmaceutico_asignado = request.user
        colectivo.save()

    medicamentos = colectivo.medicamentos.select_related('medicamento').all()
    medicamentos_con_stock = []

    for item in medicamentos:
        lotes_disponibles = (
            Lote.objects
            .filter(medicamento=item.medicamento, existencia__gt=0)
            .order_by('fecha_caducidad')
        )

        stock_total = lotes_disponibles.aggregate(total=Sum('existencia'))['total'] or 0

        medicamentos_con_stock.append({
            'item': item,
            'stock_disponible': stock_total,
            'suficiente': stock_total >= item.cantidad_solicitada,
            'lotes': lotes_disponibles,
        })

    template = (
        'detalle_colectivo_antibioticos_farmacia.html'
        if antibioticos else 'detalle_colectivo_farmacia.html'
    )
    return render(request, template, {
        'colectivo': colectivo,
        'medicamentos_con_stock': medicamentos_con_stock,
        'user': request.user,
        'modulo_antibioticos': antibioticos,
    })


def detalle_colectivo_antibioticos_farmacia(request, colectivo_id):
    return detalle_colectivo_farmacia(request, colectivo_id, antibioticos=True)


@never_cache
@login_required(login_url='login')
@require_http_methods(['POST'])
@permission_required('enfermeria.respond_colectivo', raise_exception=True)
def responder_colectivo(request, colectivo_id, antibioticos=False):
    """Farmacia responde al colectivo indicando disponibilidad"""
    colectivo = get_object_or_404(colectivos_por_modulo(antibioticos), id=colectivo_id)
    detalle_url = (
        'detalle_colectivo_antibioticos_farmacia'
        if antibioticos else 'detalle_colectivo_farmacia'
    )
    lista_url = (
        'lista_colectivos_antibioticos_farmacia'
        if antibioticos else 'lista_colectivos_farmacia'
    )
    if colectivo.estado not in ['PENDIENTE', 'EN_REVISION']:
        messages.error(request, 'Este colectivo ya fue respondido o completado')
        return redirect(detalle_url, colectivo_id=colectivo.id)
    try:
        colectivo.respuesta_farmacia = request.POST.get('respuesta_farmacia', '')
        for medicamento in colectivo.medicamentos.all():
            disponible = request.POST.get(f'disponible_{medicamento.id}') == 'on'
            comentario = request.POST.get(f'comentario_{medicamento.id}', '')
            medicamento.disponible = disponible
            medicamento.comentario_farmacia = comentario
            medicamento.save()
        colectivo.estado = 'RESPONDIDO'
        colectivo.fecha_respuesta_farmacia = timezone.now()
        colectivo.farmaceutico_asignado = request.user
        colectivo.save()
        messages.success(request, f'Respuesta enviada para colectivo {colectivo.folio}')
        return redirect(lista_url)
    except Exception as e:
        messages.error(request, f'Error al responder: {str(e)}')
        return redirect(detalle_url, colectivo_id=colectivo.id)


def responder_colectivo_antibioticos(request, colectivo_id):
    return responder_colectivo(request, colectivo_id, antibioticos=True)


@never_cache
@login_required(login_url='login')
@require_http_methods(['POST'])
@permission_required('enfermeria.complete_colectivo', raise_exception=True)
def completar_colectivo(request, colectivo_id, antibioticos=False):
    """Marca el colectivo como completado y descuenta del inventario"""
    try:
        with transaction.atomic():
            colectivo = get_object_or_404(
                colectivos_por_modulo(antibioticos).select_for_update(),
                id=colectivo_id,
            )
            estados_confirmables = ['EN_REVISION', 'RESPONDIDO']
            if colectivo.estado not in estados_confirmables:
                messages.error(
                    request,
                    'El colectivo debe estar en revisión o contar con una respuesta de farmacia antes de completarse.'
                )
                detalle_url = (
                    'detalle_colectivo_antibioticos_farmacia'
                    if antibioticos else 'detalle_colectivo_farmacia'
                )
                return redirect(detalle_url, colectivo_id=colectivo.id)

            confirmacion_directa = colectivo.estado == 'EN_REVISION'

            for medicamento in colectivo.medicamentos.all():
                if not confirmacion_directa and not medicamento.disponible:
                    raise ValueError(
                        f'{medicamento.medicamento.descripcion} sigue marcado como no disponible.'
                    )
                medicamento.cantidad_surtida = int(
                    request.POST.get(f'cantidad_surtida_{medicamento.id}', 0)
                )
                if medicamento.cantidad_surtida <= 0:
                    raise ValueError('Todas las cantidades surtidas deben ser mayores que cero.')
                if medicamento.cantidad_surtida > medicamento.cantidad_solicitada:
                    raise ValueError(
                        f'No se puede surtir más de lo solicitado para '
                        f'{medicamento.medicamento.descripcion}.'
                    )
                if confirmacion_directa:
                    medicamento.disponible = True
                medicamento.save()
            
            receta = None
            if colectivo.tipo_colectivo == 'PACIENTE':
                if not colectivo.paciente: raise ValueError('Debe tener paciente')
                receta = Receta.objects.create(
                    id_folio=colectivo.folio, paciente=colectivo.paciente,
                    fecha_emision=colectivo.fecha_solicitud.date() if hasattr(colectivo.fecha_solicitud, 'date') else colectivo.fecha_solicitud,
                    fecha_surtido=timezone.now().date(), estado='completa',
                    origen='hospitalizacion_adultos', surtido_por=request.user
                )
            elif colectivo.tipo_colectivo == 'STOCK':
                paciente_stock, _ = Paciente.objects.get_or_create(
                    curp='STCK000000HDFXXX00', defaults={'nombre_completo': f'STOCK - {colectivo.servicio}', 'fecha_nacimiento': date(1900, 1, 1)}
                )
                receta = Receta.objects.create(
                    id_folio=colectivo.folio, paciente=paciente_stock,
                    fecha_emision=colectivo.fecha_solicitud.date() if hasattr(colectivo.fecha_solicitud, 'date') else colectivo.fecha_solicitud,
                    fecha_surtido=timezone.now().date(), estado='completa',
                    origen='hospitalizacion_adultos', surtido_por=request.user
                )

            for medicamento in colectivo.medicamentos.all():
                lote_elegido_id = request.POST.get(f'lote_id_{medicamento.id}')
                lote_usado, precio_acumulado, _ = surtir_fefo(
                    medicamento.medicamento_id,
                    medicamento.cantidad_surtida,
                    lote_elegido_id,
                )

                precio_unitario_promedio = (
                    precio_acumulado / medicamento.cantidad_surtida
                    if medicamento.cantidad_surtida > 0 else Decimal('0.00')
                )

                if receta:
                    RecetaMedicamento.objects.create(
                        receta=receta,
                        medicamento=medicamento.medicamento,
                        lote=lote_usado,
                        cantidad_solicitada=medicamento.cantidad_solicitada,
                        cantidad_surtida=medicamento.cantidad_surtida,
                        precio_unitario=precio_unitario_promedio,
                        precio_total=precio_acumulado
                    )

            colectivo.estado = 'COMPLETADO'
            colectivo.fecha_completado = timezone.now()
            colectivo.farmaceutico_asignado = request.user
            colectivo.save()
        messages.success(request, f'Colectivo {colectivo.folio} completado exitosamente.')
        return redirect(
            'lista_colectivos_antibioticos_farmacia'
            if antibioticos else 'lista_colectivos_farmacia'
        )
    except Exception as e:
        traceback.print_exc()
        messages.error(request, f'Error al completar: {str(e)}')
        return redirect(
            'detalle_colectivo_antibioticos_farmacia'
            if antibioticos else 'detalle_colectivo_farmacia',
            colectivo_id=colectivo_id,
        )


def completar_colectivo_antibioticos(request, colectivo_id):
    return completar_colectivo(request, colectivo_id, antibioticos=True)


@login_required(login_url='login')
@require_http_methods(['GET'])
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia', 'Enfermero', 'Jefe de Enfermería')
@permission_required('enfermeria.view_colectivo', raise_exception=True)
def generar_pdf_colectivo(request, colectivo_id, antibioticos=False):
    """Genera PDF con la información del colectivo completado"""
    colectivo = get_object_or_404(
        colectivos_por_modulo(antibioticos).select_related(
            'paciente', 'enfermero_solicitante', 'farmaceutico_asignado'
        ),
        id=colectivo_id,
    )
    if colectivo.estado != 'COMPLETADO':
        messages.error(request, 'Solo se puede generar PDF de colectivos completados')
        return redirect(
            'detalle_colectivo_antibioticos_farmacia'
            if antibioticos else 'detalle_colectivo_farmacia',
            colectivo_id=colectivo.id,
        )
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.45*inch,
            rightMargin=0.45*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            pageCompression=0,
        )
        elements = []
        styles = getSampleStyleSheet()
        
        logo_path = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')
        if os.path.exists(logo_path):
            try:
                elements.append(Image(logo_path, width=3.5*inch, height=0.5*inch))
                elements.append(Spacer(1, 0.2*inch))
            except: pass
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#750000'), spaceAfter=20, alignment=TA_CENTER)
        titulo = 'Colectivo de Antibióticos' if antibioticos else 'COLECTIVO DE MEDICAMENTOS'
        elements.append(Paragraph(
            f"{escape(titulo)}<br/>{escape(colectivo.folio)}", title_style
        ))
        elements.append(Spacer(1, 0.15*inch))

        info_style = ParagraphStyle(
            'InfoColectivo', parent=styles['Normal'], fontSize=8.5,
            leading=10, alignment=TA_LEFT, wordWrap='CJK',
            splitLongWords=True,
        )
        info_header_style = ParagraphStyle(
            'InfoHeaderColectivo', parent=info_style,
            fontName='Helvetica-Bold', textColor=colors.white,
        )
        
        es_colectivo_stock = colectivo.paciente is None
        if es_colectivo_stock:
            info_data = [
                ['INFO. DEL COLECTIVO', ''],
                ['Tipo:', 'Colectivo para Stock'],
                ['Servicio:', colectivo.servicio or 'N/A'],
                ['Número de Cama:', colectivo.numero_cama or 'N/A'],
                ['', ''],
                ['FECHAS Y RESPONSABLES', ''],
                ['Fecha de Solicitud:', timezone.localtime(colectivo.fecha_solicitud).strftime('%d/%m/%Y %H:%M') if colectivo.fecha_solicitud else 'N/A'],
                ['Fecha de Surtido:', timezone.localtime(colectivo.fecha_completado).strftime('%d/%m/%Y %H:%M') if colectivo.fecha_completado else 'N/A'],
                ['Enfermero(a) Solicitante:', colectivo.enfermero_solicitante.get_full_name() or colectivo.enfermero_solicitante.username if colectivo.enfermero_solicitante else 'N/A'],
                ['Farmacéutico(a) Asignado:', colectivo.farmaceutico_asignado.get_full_name() or colectivo.farmaceutico_asignado.username if colectivo.farmaceutico_asignado else 'N/A'],
            ]
        else:
            info_data = [
                ['INFORMACIÓN DEL PACIENTE', ''],
                ['Nombre:', colectivo.paciente.nombre_completo],
                ['CURP:', colectivo.paciente.curp if colectivo.paciente.curp else 'N/A'],
                ['Fecha Nacimiento:', colectivo.paciente.fecha_nacimiento.strftime('%d/%m/%Y') if colectivo.paciente.fecha_nacimiento else 'N/A'],
                ['Número de Cama:', colectivo.numero_cama or 'N/A'],
                ['Servicio:', colectivo.servicio or 'N/A'],
                ['', ''],
                ['INFO. DEL COLECTIVO', ''],
                ['Fecha Solicitud:', timezone.localtime(colectivo.fecha_solicitud).strftime('%d/%m/%Y %H:%M') if colectivo.fecha_solicitud else 'N/A'],
                ['Fecha Surtido:', timezone.localtime(colectivo.fecha_completado).strftime('%d/%m/%Y %H:%M') if colectivo.fecha_completado else 'N/A'],
                ['Enfermero(a):', colectivo.enfermero_solicitante.get_full_name() or colectivo.enfermero_solicitante.username if colectivo.enfermero_solicitante else 'N/A'],
                ['Farmacéutico(a):', colectivo.farmaceutico_asignado.get_full_name() or colectivo.farmaceutico_asignado.username if colectivo.farmaceutico_asignado else 'N/A'],
            ]
        
        fila_seccion = 5 if es_colectivo_stock else 7
        info_data_formateada = []
        for indice, fila in enumerate(info_data):
            estilo = (
                info_header_style
                if indice in (0, fila_seccion)
                else info_style
            )
            info_data_formateada.append([
                Paragraph(escape(str(celda or '')), estilo)
                for celda in fila
            ])

        info_table = Table(info_data_formateada, colWidths=[2*inch, 4.5*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#750000')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, fila_seccion), (-1, fila_seccion), colors.HexColor('#750000')),
            ('TEXTCOLOR', (0, fila_seccion), (-1, fila_seccion), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, fila_seccion), (-1, fila_seccion), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.2*inch))
        
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10, alignment=TA_LEFT)
        center_style = ParagraphStyle('CenterStyle', parent=styles['Normal'], fontSize=8, leading=10, alignment=TA_CENTER)
        table_header_style = ParagraphStyle(
            'TableHeaderColectivo', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=7.5, leading=8.5,
            alignment=TA_CENTER, textColor=colors.white,
            wordWrap='CJK', splitLongWords=True,
        )
        
        if antibioticos:
            medicamentos_data = [[
                Paragraph('CLAVE', table_header_style),
                Paragraph('DESCRIPCIÓN', table_header_style),
                Paragraph('CATEGORÍA AWaRe', table_header_style),
                Paragraph('CÓDIGO ATC', table_header_style),
            ]]
            for item in colectivo.medicamentos.select_related('medicamento').all():
                medicamento = item.medicamento
                medicamentos_data.append([
                    Paragraph(escape(medicamento.clave or 'N/A'), cell_style),
                    Paragraph(escape(truncar_texto(medicamento.descripcion or 'N/A', 220)), cell_style),
                    Paragraph(escape(medicamento.categoria_aware or 'N/A'), center_style),
                    Paragraph(escape(medicamento.codigo_atc or 'N/A'), center_style),
                ])
            columnas_medicamentos = [1.25*inch, 3.35*inch, 1.25*inch, 1.25*inch]
        else:
            medicamentos_data = [[
                Paragraph('#', table_header_style),
                Paragraph('CLAVE', table_header_style),
                Paragraph('DESCRIPCIÓN', table_header_style),
                Paragraph('SOLICITADO', table_header_style),
                Paragraph('SURTIDO', table_header_style),
            ]]
            for idx, item in enumerate(colectivo.medicamentos.all(), 1):
                medicamentos_data.append([
                    Paragraph(str(idx), center_style),
                    Paragraph(escape(item.medicamento.clave if item.medicamento else 'N/A'), cell_style),
                    Paragraph(
                        escape(truncar_texto(
                            item.medicamento.descripcion if item.medicamento else 'N/A',
                            220,
                        )),
                        cell_style,
                    ),
                    Paragraph(str(item.cantidad_solicitada), center_style),
                    Paragraph(str(item.cantidad_surtida), center_style)
                ])
            columnas_medicamentos = [0.3*inch, 1.2*inch, 3.8*inch, 0.9*inch, 0.9*inch]

        medicamentos_table = Table(
            medicamentos_data,
            colWidths=columnas_medicamentos,
            repeatRows=1,
            splitByRow=1,
            hAlign='CENTER',
        )
        medicamentos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#750000')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(medicamentos_table)
        
        doc.build(elements)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        prefijo_archivo = 'Colectivo_Antibioticos' if antibioticos else 'Colectivo'
        response['Content-Disposition'] = (
            f'attachment; filename="{prefijo_archivo}_{colectivo.folio}.pdf"'
        )
        return response
    except Exception as e:
        messages.error(request, f'Error al generar PDF: {str(e)}')
        return redirect(
            'lista_colectivos_antibioticos_farmacia'
            if antibioticos else 'lista_colectivos_farmacia'
        )


def generar_pdf_colectivo_antibioticos(request, colectivo_id):
    return generar_pdf_colectivo(request, colectivo_id, antibioticos=True)
