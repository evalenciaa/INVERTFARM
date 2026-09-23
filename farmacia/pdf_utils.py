import os
from html import escape
from io import BytesIO

from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .models import (
    DetalleSalidaTransferencia, MedicamentoNoSurtido, RecetaMedicamento,
)


def _texto(valor, predeterminado='N/A'):
    return escape(str(valor if valor not in (None, '') else predeterminado))


def _estilos_comprobante():
    styles = getSampleStyleSheet()
    return {
        'titulo': ParagraphStyle(
            'TituloComprobante', parent=styles['Title'],
            fontName='Helvetica-Bold', fontSize=15, leading=18,
            alignment=TA_CENTER, spaceAfter=4,
        ),
        'meta': ParagraphStyle(
            'MetaComprobante', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5, leading=10,
            alignment=TA_CENTER,
        ),
        'seccion': ParagraphStyle(
            'SeccionComprobante', parent=styles['Heading2'],
            fontName='Helvetica-Bold', fontSize=11, leading=13,
            textColor=colors.HexColor('#343A40'), spaceBefore=3, spaceAfter=5,
        ),
        'celda': ParagraphStyle(
            'CeldaComprobante', parent=styles['Normal'],
            fontName='Helvetica', fontSize=7.5, leading=9,
            alignment=TA_LEFT, wordWrap='CJK', splitLongWords=True,
        ),
        'centrada': ParagraphStyle(
            'CeldaCentradaComprobante', parent=styles['Normal'],
            fontName='Helvetica', fontSize=7.5, leading=9,
            alignment=TA_CENTER, wordWrap='CJK', splitLongWords=True,
        ),
        'info': ParagraphStyle(
            'InfoComprobante', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5, leading=12,
            alignment=TA_LEFT, wordWrap='CJK', splitLongWords=True,
        ),
    }


def _encabezado(elementos, titulo, responsable, estilos):
    logo_path = os.path.join(
        settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
    )
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=180 * mm, height=25.5 * mm)
        logo.hAlign = 'CENTER'
        elementos.extend([logo, Spacer(1, 3 * mm)])

    elementos.append(Paragraph(_texto(titulo, ''), estilos['titulo']))
    elementos.append(Paragraph(
        f"Fecha de Emisión: {timezone.localtime().strftime('%d/%m/%Y %H:%M')}",
        estilos['meta'],
    ))
    elementos.append(Paragraph(
        f"Generado por: {_texto(responsable)}", estilos['meta']
    ))
    elementos.append(Spacer(1, 5 * mm))


def _tabla(datos, anchos, estilos, color_encabezado='#343A40', filas_repetidas=1):
    tabla = LongTable(
        datos, colWidths=anchos, repeatRows=filas_repetidas,
        splitByRow=1, hAlign='CENTER',
    )
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(color_encabezado)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.white, colors.HexColor('#F8F9FA'),
        ]),
        ('GRID', (0, 0), (-1, -1), 0.45, colors.HexColor('#666666')),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _dibujar_pie(canvas, documento):
    canvas.saveState()
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(colors.HexColor('#666666'))
    canvas.drawCentredString(
        letter[0] / 2, 7 * mm,
        f'INVENTFARM - Página {documento.page}',
    )
    canvas.restoreState()


def _nuevo_documento(buffer, titulo):
    return SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
        title=titulo,
        pageCompression=1,
    )


def generar_pdf_salida(receta):
    """Genera un comprobante de receta con tablas paginables."""
    buffer = BytesIO()
    documento = _nuevo_documento(buffer, 'Comprobante de Salida de Farmacia')
    estilos = _estilos_comprobante()
    elementos = []

    responsable = 'N/A'
    if receta.surtido_por:
        responsable = (
            receta.surtido_por.get_full_name() or receta.surtido_por.username
        )
    _encabezado(
        elementos, 'Comprobante de Salida de Farmacia', responsable, estilos
    )

    fecha_nacimiento = (
        receta.paciente.fecha_nacimiento.strftime('%d/%m/%Y')
        if receta.paciente.fecha_nacimiento else 'N/A'
    )
    fecha_surtido = (
        receta.fecha_surtido.strftime('%d/%m/%Y')
        if receta.fecha_surtido else 'N/A'
    )
    info = Table([
        [
            Paragraph('<b>Datos del Paciente</b>', estilos['seccion']),
            Paragraph('<b>Datos de la Receta</b>', estilos['seccion']),
        ],
        [
            Paragraph(
                f"<b>Paciente:</b> {_texto(receta.paciente.nombre_completo)}<br/>"
                f"<b>CURP:</b> {_texto(receta.paciente.curp)}<br/>"
                f"<b>Fecha Nac.:</b> {_texto(fecha_nacimiento)}",
                estilos['info'],
            ),
            Paragraph(
                f"<b>Folio:</b> {_texto(receta.id_folio)}<br/>"
                f"<b>Origen:</b> {_texto(receta.get_origen_display())}<br/>"
                f"<b>Fecha Surtido:</b> {_texto(fecha_surtido)}",
                estilos['info'],
            ),
        ],
    ], colWidths=[90 * mm, 90 * mm])
    info.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elementos.extend([info, Spacer(1, 5 * mm)])

    elementos.append(Paragraph('Medicamentos Surtidos', estilos['seccion']))
    datos = [[
        Paragraph('Clave', estilos['centrada']),
        Paragraph('Descripción', estilos['centrada']),
        Paragraph('Lote', estilos['centrada']),
        Paragraph('Cant.', estilos['centrada']),
    ]]
    items = (
        RecetaMedicamento.objects.filter(receta=receta)
        .select_related('medicamento', 'lote')
        .order_by('medicamento__descripcion')
    )
    for item in items:
        datos.append([
            Paragraph(_texto(item.medicamento.clave), estilos['centrada']),
            Paragraph(_texto(item.medicamento.descripcion), estilos['celda']),
            Paragraph(
                _texto(item.lote.lote_codigo if item.lote else None),
                estilos['centrada'],
            ),
            Paragraph(str(item.cantidad_surtida), estilos['centrada']),
        ])
    if len(datos) == 1:
        datos.append([
            Paragraph('---', estilos['centrada']),
            Paragraph('No se surtió ningún medicamento', estilos['celda']),
            Paragraph('---', estilos['centrada']),
            Paragraph('0', estilos['centrada']),
        ])
    elementos.append(_tabla(
        datos, [27 * mm, 107 * mm, 28 * mm, 18 * mm], estilos
    ))

    faltantes = MedicamentoNoSurtido.objects.filter(
        receta=receta
    ).order_by('medicamento_descripcion')
    if faltantes.exists():
        elementos.extend([
            Spacer(1, 5 * mm),
            Paragraph('Medicamentos No Disponibles', estilos['seccion']),
        ])
        datos_faltantes = [[
            Paragraph('Medicamento', estilos['centrada']),
            Paragraph('Cant. solicitada', estilos['centrada']),
            Paragraph('Motivo', estilos['centrada']),
        ]]
        for faltante in faltantes:
            datos_faltantes.append([
                Paragraph(_texto(faltante.medicamento_descripcion), estilos['celda']),
                Paragraph(str(faltante.cantidad_solicitada), estilos['centrada']),
                Paragraph(_texto(faltante.motivo), estilos['celda']),
            ])
        tabla_faltantes = _tabla(
            datos_faltantes, [85 * mm, 30 * mm, 65 * mm], estilos, '#D69E00'
        )
        tabla_faltantes.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
                colors.HexColor('#FFF8E1'), colors.HexColor('#FFF3CD'),
            ]),
        ]))
        elementos.append(tabla_faltantes)

    documento.build(
        elementos, onFirstPage=_dibujar_pie, onLaterPages=_dibujar_pie
    )
    buffer.seek(0)
    return buffer


def generar_pdf_transferencia(transferencia):
    """Genera un comprobante de transferencia con tablas paginables."""
    buffer = BytesIO()
    documento = _nuevo_documento(
        buffer, 'Comprobante de Salida por Transferencia'
    )
    estilos = _estilos_comprobante()
    elementos = []

    responsable = 'N/A'
    if transferencia.autorizado_por:
        responsable = (
            transferencia.autorizado_por.get_full_name()
            or transferencia.autorizado_por.username
        )
    _encabezado(
        elementos, 'Comprobante de Salida por Transferencia',
        responsable, estilos,
    )

    fecha_transferencia = timezone.localtime(transferencia.fecha).strftime(
        '%d/%m/%Y %H:%M'
    )
    info = Table([
        [
            Paragraph('<b>Institución Destino</b>', estilos['seccion']),
            Paragraph('<b>Datos de la Transferencia</b>', estilos['seccion']),
        ],
        [
            Paragraph(
                f"<b>Nombre:</b> {_texto(transferencia.institucion_destino.nombre)}<br/>"
                f"<b>Código:</b> {_texto(transferencia.institucion_destino.codigo)}<br/>"
                f"<b>Tipo:</b> {_texto(transferencia.institucion_destino.get_tipo_display())}",
                estilos['info'],
            ),
            Paragraph(
                f"<b>Folio:</b> {_texto(transferencia.folio)}<br/>"
                f"<b>Fecha:</b> {_texto(fecha_transferencia)}",
                estilos['info'],
            ),
        ],
    ], colWidths=[105 * mm, 75 * mm])
    info.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elementos.extend([info, Spacer(1, 5 * mm)])

    elementos.append(Paragraph('Medicamentos Transferidos', estilos['seccion']))
    datos = [[
        Paragraph('Clave', estilos['centrada']),
        Paragraph('Descripción', estilos['centrada']),
        Paragraph('Lote', estilos['centrada']),
        Paragraph('Cant.', estilos['centrada']),
        Paragraph('Costo unit.', estilos['centrada']),
    ]]
    items = (
        DetalleSalidaTransferencia.objects.filter(transferencia=transferencia)
        .select_related('lote', 'lote__medicamento')
        .order_by('lote__medicamento__descripcion')
    )
    for item in items:
        datos.append([
            Paragraph(_texto(item.lote.medicamento.clave), estilos['centrada']),
            Paragraph(_texto(item.lote.medicamento.descripcion), estilos['celda']),
            Paragraph(_texto(item.lote.lote_codigo), estilos['centrada']),
            Paragraph(str(item.cantidad), estilos['centrada']),
            Paragraph(f"${item.costo_unitario:,.2f}", estilos['centrada']),
        ])
    if len(datos) == 1:
        datos.append([
            Paragraph('---', estilos['centrada']),
            Paragraph('No se registraron medicamentos', estilos['celda']),
            Paragraph('---', estilos['centrada']),
            Paragraph('0', estilos['centrada']),
            Paragraph('$0.00', estilos['centrada']),
        ])
    elementos.append(_tabla(
        datos, [25 * mm, 83 * mm, 26 * mm, 18 * mm, 28 * mm], estilos
    ))

    faltantes = transferencia.medicamentos_no_disponibles.all().order_by(
        'medicamento_descripcion'
    )
    if faltantes.exists():
        elementos.extend([
            Spacer(1, 5 * mm),
            Paragraph('Medicamentos No Disponibles', estilos['seccion']),
        ])
        datos_faltantes = [[
            Paragraph('Medicamento', estilos['centrada']),
            Paragraph('Cant. solicitada', estilos['centrada']),
            Paragraph('Motivo', estilos['centrada']),
        ]]
        for faltante in faltantes:
            datos_faltantes.append([
                Paragraph(_texto(faltante.medicamento_descripcion), estilos['celda']),
                Paragraph(str(faltante.cantidad_solicitada), estilos['centrada']),
                Paragraph(_texto(faltante.motivo), estilos['celda']),
            ])
        tabla_faltantes = _tabla(
            datos_faltantes, [85 * mm, 30 * mm, 65 * mm], estilos, '#D69E00'
        )
        tabla_faltantes.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
                colors.HexColor('#FFF8E1'), colors.HexColor('#FFF3CD'),
            ]),
        ]))
        elementos.append(tabla_faltantes)

    if transferencia.observaciones:
        observaciones = _texto(transferencia.observaciones).replace('\n', '<br/>')
        elementos.extend([
            Spacer(1, 5 * mm),
            Paragraph('Observaciones', estilos['seccion']),
            Paragraph(observaciones, estilos['celda']),
        ])

    documento.build(
        elementos, onFirstPage=_dibujar_pie, onLaterPages=_dibujar_pie
    )
    buffer.seek(0)
    return buffer
