"""
farmacia/views/reporte_views.py
Vistas para reportes estadísticos y exportación de inventarios a PDF y Excel.
"""
import os
from datetime import datetime, timedelta
from io import BytesIO
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from collections import defaultdict
from django.db.models import Sum, Count, Q, F, Value, IntegerField, Max, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import make_aware
from farmacia.decorators import group_required
from farmacia.models import Lote, Receta, RecetaMedicamento, DetalleSalidaTransferencia


@login_required
def exportar_inventario_excel(request):
    """Exportar inventario a Excel con formato y semaforización correcta"""
    try:
        import os
        from io import BytesIO
        from datetime import datetime, date
        import xlsxwriter

        lotes = (
            Lote.objects
            .select_related('medicamento', 'presentacion')
            .all()
            .order_by('fecha_caducidad', 'medicamento__clave')
        )

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Inventario')

        header_format = workbook.add_format({
            'bg_color': '#8B0000',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11,
            'text_wrap': True
        })

        title_format = workbook.add_format({
            'bg_color': '#8B0000',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14
        })

        date_format = workbook.add_format({
            'italic': True,
            'align': 'left',
            'font_size': 10
        })

        text_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10
        })

        number_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10,
            'num_format': '#,##0'
        })

        money_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10,
            'num_format': '$#,##0.00'
        })

        red_format = workbook.add_format({
            'bg_color': '#FF0000',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bold': True,
            'num_format': 'dd/mm/yyyy'
        })

        yellow_format = workbook.add_format({
            'bg_color': '#FFFF00',
            'font_color': 'black',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bold': True,
            'num_format': 'dd/mm/yyyy'
        })

        green_format = workbook.add_format({
            'bg_color': '#00B050',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bold': True,
            'num_format': 'dd/mm/yyyy'
        })

        # Ajuste de columnas
        worksheet.set_column('A:A', 16)   # Clave
        worksheet.set_column('B:B', 55)   # Descripción
        worksheet.set_column('C:C', 18)   # Lote
        worksheet.set_column('D:D', 18)   # Presentación
        worksheet.set_column('E:E', 12)   # Existencia
        worksheet.set_column('F:F', 14)   # Costo Unit.
        worksheet.set_column('G:G', 16)   # Costo Total
        worksheet.set_column('H:H', 16)   # Caducidad
        worksheet.set_column('I:I', 18)   # Tipo de entrada / Origen
        worksheet.set_column('J:J', 22)   # Fuente financiamiento
        worksheet.set_column('K:K', 22)   # No. de Contrato

        logo_path = os.path.join(
            settings.BASE_DIR,
            'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            try:
                worksheet.insert_image('A1', logo_path, {'x_scale': 0.8, 'y_scale': 0.8})
            except Exception:
                pass

        worksheet.merge_range('A3:K3', 'REPORTE DE INVENTARIO DE MEDICAMENTOS POR LOTE', title_format)
        worksheet.merge_range('A4:K4', f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", date_format)

        headers = [
            'Clave',
            'Descripción',
            'Lote',
            'Presentación',
            'Existencia',
            'Costo Unit.',
            'Costo Total',
            'Caducidad',
            'Tipo de entrada',
            'Fuente de financiamiento',
            'No. de Contrato',
        ]

        for col, header in enumerate(headers):
            worksheet.write(5, col, header, header_format)

        worksheet.set_row(5, 28)

        hoy = date.today()
        row = 6

        for lote in lotes:
            costo_unitario = float(lote.costo_unitario or 0)
            existencia = int(lote.existencia or 0)
            costo_total = costo_unitario * existencia

            worksheet.write(row, 0, lote.medicamento.clave, text_format)
            worksheet.write(row, 1, lote.medicamento.descripcion, text_format)
            worksheet.write(row, 2, lote.lote_codigo, text_format)
            worksheet.write(row, 3, lote.presentacion.nombre if lote.presentacion else 'N/A', text_format)
            worksheet.write_number(row, 4, existencia, number_format)
            worksheet.write_number(row, 5, costo_unitario, money_format)
            worksheet.write_number(row, 6, costo_total, money_format)

            dias_restantes = (lote.fecha_caducidad - hoy).days

            if dias_restantes <= 180:
                semaforo_format = red_format
            elif dias_restantes <= 365:
                semaforo_format = yellow_format
            else:
                semaforo_format = green_format

            worksheet.write_datetime(
                row,
                7,
                datetime.combine(lote.fecha_caducidad, datetime.min.time()),
                semaforo_format
            )

            worksheet.write(row, 8, getattr(lote, 'origen', '') or 'N/A', text_format)
            worksheet.write(row, 9, getattr(lote, 'fuente_financiamiento', '') or 'N/A', text_format)
            worksheet.write(row, 10, getattr(lote, 'contrato', '') or 'N/A', text_format)

            worksheet.set_row(row, 20)
            row += 1

        worksheet.merge_range(row + 1, 0, row + 1, 10,
                              'Documento generado automáticamente por INVENTFARM',
                              date_format)

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="Inventario_{datetime.now().strftime("%d%m%Y")}.xlsx"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)


def truncar_texto(valor, limite=80):
    texto = str(valor or "").strip()
    if len(texto) <= limite:
        return texto
    return texto[:limite - 3] + "..."


@login_required
def exportar_inventario_pdf(request):
    """Exportar inventario por lotes a PDF en orientación horizontal"""
    try:
        import os
        from io import BytesIO
        from datetime import datetime

        from django.conf import settings
        from django.http import HttpResponse

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        )

        lotes = (
            Lote.objects
            .select_related('medicamento', 'presentacion')
            .all()
            .order_by('fecha_caducidad', 'medicamento__descripcion', 'lote_codigo')
        )

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=8 * mm,
            rightMargin=8 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )

        styles = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            name="TituloReporte",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=1,
            spaceAfter=4,
        )

        estilo_meta = ParagraphStyle(
            name="MetaReporte",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=1,
            spaceAfter=2,
        )

        estilo_header = ParagraphStyle(
            name="HeaderTabla",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.0,
            leading=6.5,
            alignment=1,
            textColor=colors.whitesmoke,
        )

        estilo_celda = ParagraphStyle(
            name="CeldaTabla",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=5.7,
            leading=6.2,
            alignment=0,
            wordWrap='LTR',
        )

        estilo_celda_centrada = ParagraphStyle(
            name="CeldaTablaCentrada",
            parent=estilo_celda,
            alignment=1,
        )
        
        estilo_celda_derecha = ParagraphStyle(
            name="CeldaTablaDerecha",
            parent=estilo_celda,
            alignment=2,
        )

        elementos = []

        logo_path = os.path.join(
            settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=170 * mm, height=24 * mm)
            logo.hAlign = 'CENTER'
            elementos.append(logo)
            elementos.append(Spacer(1, 3 * mm))

        elementos.append(Paragraph(
            "REPORTE DE INVENTARIO POR LOTES DE MEDICAMENTOS",
            estilo_titulo
        ))

        fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
        nombre_usuario = (request.user.get_full_name() or request.user.username).strip()

        elementos.append(Paragraph(
            f"Fecha de Generación: {fecha_generacion}",
            estilo_meta
        ))
        elementos.append(Paragraph(
            f"Generado por: {nombre_usuario}",
            estilo_meta
        ))
        elementos.append(Spacer(1, 4 * mm))

        data_tabla = [[
            Paragraph("Clave", estilo_header),
            Paragraph("Descripción", estilo_header),
            Paragraph("Lote", estilo_header),
            Paragraph("Pres.", estilo_header),
            Paragraph("Exist.", estilo_header),
            Paragraph("C. Unit.", estilo_header),
            Paragraph("Cad.", estilo_header),
            Paragraph("T. Entrada", estilo_header),
            Paragraph("Contrato", estilo_header),
            Paragraph("F. Financ.", estilo_header),
            Paragraph("C. total", estilo_header),
        ]]

        for lote in lotes:
            fuente_financiamiento = getattr(lote, 'fuente_financiamiento', None)
            if hasattr(fuente_financiamiento, 'nombre'):
                fuente_texto = fuente_financiamiento.nombre
            else:
                fuente_texto = str(fuente_financiamiento or "N/A")

            costo_total = float(lote.existencia or 0) * float(lote.costo_unitario or 0)
            
            data_tabla.append([
                Paragraph(lote.medicamento.clave or "N/A", estilo_celda_centrada),
                Paragraph(truncar_texto(lote.medicamento.descripcion or "N/A", 260), estilo_celda),
                Paragraph(lote.lote_codigo or "N/A", estilo_celda_centrada),
                Paragraph(lote.presentacion.nombre if lote.presentacion else "N/A", estilo_celda_centrada),
                Paragraph(str(lote.existencia or 0), estilo_celda_centrada),
                Paragraph(f"${float(lote.costo_unitario or 0):,.2f}", estilo_celda_derecha),
                Paragraph(
                    lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else "N/A",
                    estilo_celda_centrada
                ),
                Paragraph(str(getattr(lote, 'origen', None) or "N/A"), estilo_celda),
                Paragraph(str(getattr(lote, 'contrato', None) or "N/A"), estilo_celda),
                Paragraph(fuente_texto, estilo_celda),
                Paragraph(f"${costo_total:,.2f}", estilo_celda_derecha),
            ])

        col_widths = [
            18 * mm,   # Clave
            82 * mm,   # Descripción
            16 * mm,   # Lote
            12 * mm,   # Pres.
            12 * mm,   # Exist.
            16 * mm,   # C. Unit.
            18 * mm,   # Cad.
            19 * mm,   # T. Entrada
            18 * mm,   # Contrato
            20 * mm,   # F. Financ.
            18 * mm,   # C. total
        ]

        tabla = Table(
            data_tabla,
            colWidths=col_widths,
            repeatRows=1,
            splitByRow=1,
            hAlign='LEFT',
        )

        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8B0000")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6.8),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),

            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F4F4")]),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),

            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),

            ('ALIGN', (0, 1), (0, -1), 'CENTER'),    # Clave
            ('ALIGN', (2, 1), (4, -1), 'CENTER'),    # Lote, Pres., Exist.
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),     # C. Unit.
            ('ALIGN', (6, 1), (6, -1), 'CENTER'),    # Cad.
            ('ALIGN', (10, 1), (10, -1), 'RIGHT'),   # C. total
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(
            f"Documento generado por INVENTFARM - {nombre_usuario}",
            estilo_meta
        ))

        doc.build(elementos)

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="Inventario_{datetime.now().strftime("%d%m%Y")}.pdf"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)


@login_required
def exportar_proximos_caducar_pdf(request):
    """Exportar PDF de medicamentos próximos a caducar (< 6 meses)"""
    try:
        import os
        from io import BytesIO
        from datetime import datetime, timedelta

        from django.conf import settings
        from django.http import HttpResponse

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        )

        hoy = datetime.now().date()
        fecha_limite = hoy + timedelta(days=180)

        lotes = (
            Lote.objects
            .select_related('medicamento', 'presentacion')
            .filter(
                fecha_caducidad__gte=hoy,
                fecha_caducidad__lte=fecha_limite
            )
            .order_by('fecha_caducidad', 'medicamento__descripcion', 'lote_codigo')
        )

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=8 * mm,
            rightMargin=8 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )

        styles = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            name="TituloReporte",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=1,
            spaceAfter=4,
        )

        estilo_meta = ParagraphStyle(
            name="MetaReporte",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=1,
            spaceAfter=2,
        )

        estilo_header = ParagraphStyle(
            name="HeaderTabla",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.0,
            leading=6.5,
            alignment=1,
            textColor=colors.whitesmoke,
        )

        estilo_celda = ParagraphStyle(
            name="CeldaTabla",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=5.7,
            leading=6.2,
            alignment=0,
            wordWrap='LTR',
        )

        estilo_celda_centrada = ParagraphStyle(
            name="CeldaTablaCentrada",
            parent=estilo_celda,
            alignment=1,
        )

        estilo_celda_derecha = ParagraphStyle(
            name="CeldaTablaDerecha",
            parent=estilo_celda,
            alignment=2,
        )

        elementos = []

        logo_path = os.path.join(
            settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=170 * mm, height=24 * mm)
            logo.hAlign = 'CENTER'
            elementos.append(logo)
            elementos.append(Spacer(1, 3 * mm))

        elementos.append(Paragraph(
            "REPORTE DE MEDICAMENTOS PRÓXIMOS A CADUCAR",
            estilo_titulo
        ))

        fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
        nombre_usuario = (request.user.get_full_name() or request.user.username).strip()

        elementos.append(Paragraph(
            f"Fecha de Generación: {fecha_generacion}",
            estilo_meta
        ))
        elementos.append(Paragraph(
            f"Generado por: {nombre_usuario}",
            estilo_meta
        ))
        elementos.append(Paragraph(
            f"Rango considerado: {hoy.strftime('%d/%m/%Y')} al {fecha_limite.strftime('%d/%m/%Y')}",
            estilo_meta
        ))
        elementos.append(Spacer(1, 4 * mm))

        data_tabla = [[
            Paragraph("Clave", estilo_header),
            Paragraph("Descripción", estilo_header),
            Paragraph("Lote", estilo_header),
            Paragraph("Pres.", estilo_header),
            Paragraph("Exist.", estilo_header),
            Paragraph("C. Unit.", estilo_header),
            Paragraph("Cad.", estilo_header),
            Paragraph("T. Entrada", estilo_header),
            Paragraph("Contrato", estilo_header),
            Paragraph("F. Financ.", estilo_header),
            Paragraph("C. total", estilo_header),
        ]]

        for lote in lotes:
            fuente_financiamiento = getattr(lote, 'fuente_financiamiento', None)
            if hasattr(fuente_financiamiento, 'nombre'):
                fuente_texto = fuente_financiamiento.nombre
            else:
                fuente_texto = str(fuente_financiamiento or "N/A")

            costo_total = float(lote.existencia or 0) * float(lote.costo_unitario or 0)

            data_tabla.append([
                Paragraph(lote.medicamento.clave or "N/A", estilo_celda_centrada),
                Paragraph(truncar_texto(lote.medicamento.descripcion or "N/A", 260), estilo_celda),
                Paragraph(lote.lote_codigo or "N/A", estilo_celda_centrada),
                Paragraph(lote.presentacion.nombre if lote.presentacion else "N/A", estilo_celda_centrada),
                Paragraph(str(lote.existencia or 0), estilo_celda_centrada),
                Paragraph(f"${float(lote.costo_unitario or 0):,.2f}", estilo_celda_derecha),
                Paragraph(
                    lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else "N/A",
                    estilo_celda_centrada
                ),
                Paragraph(str(getattr(lote, 'origen', None) or "N/A"), estilo_celda),
                Paragraph(str(getattr(lote, 'contrato', None) or "N/A"), estilo_celda),
                Paragraph(fuente_texto, estilo_celda),
                Paragraph(f"${costo_total:,.2f}", estilo_celda_derecha),
            ])

        if len(data_tabla) == 1:
            data_tabla.append([
                Paragraph("-", estilo_celda_centrada),
                Paragraph("Sin medicamentos próximos a caducar", estilo_celda),
                Paragraph("-", estilo_celda_centrada),
                Paragraph("-", estilo_celda_centrada),
                Paragraph("-", estilo_celda_centrada),
                Paragraph("$0.00", estilo_celda_derecha),
                Paragraph("-", estilo_celda_centrada),
                Paragraph("-", estilo_celda),
                Paragraph("-", estilo_celda),
                Paragraph("-", estilo_celda),
                Paragraph("$0.00", estilo_celda_derecha),
            ])

        col_widths = [
            18 * mm,   # Clave
            82 * mm,   # Descripción
            16 * mm,   # Lote
            12 * mm,   # Pres.
            12 * mm,   # Exist.
            16 * mm,   # C. Unit.
            18 * mm,   # Cad.
            19 * mm,   # T. Entrada
            18 * mm,   # Contrato
            20 * mm,   # F. Financ.
            18 * mm,   # C. total
        ]

        tabla = Table(
            data_tabla,
            colWidths=col_widths,
            repeatRows=1,
            splitByRow=1,
            hAlign='LEFT',
        )

        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8B0000")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6.8),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),

            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF1F1")]),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),

            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),

            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (4, -1), 'CENTER'),
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
            ('ALIGN', (6, 1), (6, -1), 'CENTER'),
            ('ALIGN', (10, 1), (10, -1), 'RIGHT'),
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(
            f"Documento generado por INVENTFARM - {nombre_usuario}",
            estilo_meta
        ))

        doc.build(elementos)

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="Proximos_Caducar_{datetime.now().strftime("%d%m%Y")}.pdf"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)

@login_required
def exportar_inventario_general_excel(request):
    """Exportar inventario general a Excel"""
    try:
        import xlsxwriter
        inventario = Lote.objects.values('medicamento__id', 'medicamento__clave', 'medicamento__descripcion').annotate(
            existencia_total=Sum('existencia'),
            cpm_medicamento=Coalesce(F('medicamento__cpm_medicamento__valor'), Value(0), output_field=IntegerField())
        ).filter(existencia_total__gt=0).order_by('medicamento__descripcion')
        
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Inventario General')
        
        header_format = workbook.add_format({'bg_color': '#8B0000', 'font_color': 'white', 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 11})
        title_format = workbook.add_format({'bg_color': '#8B0000', 'font_color': 'white', 'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14})
        date_format = workbook.add_format({'italic': True, 'align': 'left', 'font_size': 10})
        data_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10})
        critico_format = workbook.add_format({'bg_color': '#FF0000', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True})
        bajo_format = workbook.add_format({'bg_color': '#FF4444', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        yellow_format = workbook.add_format({'bg_color': '#FFFF00', 'font_color': 'black', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        green_format = workbook.add_format({'bg_color': '#00B050', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        
        worksheet.set_column('A:A', 18)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 18)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        
        logo_path = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')
        if os.path.exists(logo_path):
            try: worksheet.insert_image('A1', logo_path, {'x_scale': 0.8, 'y_scale': 0.8})
            except: pass
        
        worksheet.merge_range('A3:E3', 'REPORTE DE INVENTARIO GENERAL', title_format)
        worksheet.merge_range('A4:E4', f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", date_format)
        
        headers = ['Clave', 'Descripción', 'Existencia Total', 'CPM', 'Estado']
        for col, header in enumerate(headers): worksheet.write(5, col, header, header_format)
        worksheet.set_row(5, 20)
        
        row = 6
        for item in inventario:
            worksheet.write(row, 0, item['medicamento__clave'], data_format)
            worksheet.write(row, 1, item['medicamento__descripcion'], data_format)
            worksheet.write(row, 2, item['existencia_total'], data_format)
            worksheet.write(row, 3, item['cpm_medicamento'], data_format)
            
            existencia = item['existencia_total']
            estado_text, estado_format = 'Adecuado', green_format
            if existencia <= 10: estado_text, estado_format = 'Crítico', critico_format
            elif existencia <= 50: estado_text, estado_format = 'Bajo', bajo_format
            elif existencia <= 100: estado_text, estado_format = 'Medio', yellow_format
            
            worksheet.write(row, 4, estado_text, estado_format)
            worksheet.set_row(row, 18)
            row += 1
            
        worksheet.merge_range(row + 1, 0, row + 1, 4, 'Documento generado automáticamente por INVENTFARM', date_format)
        workbook.close()
        
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Inventario_General_{datetime.now().strftime("%d%m%Y")}.xlsx"'
        return response
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)


@login_required
def exportar_inventario_general_pdf(request):
    """Exportar inventario general a PDF (descripción con wrap)"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT

        inventario = Lote.objects.values('medicamento__id', 'medicamento__clave', 'medicamento__descripcion').annotate(
            existencia_total=Sum('existencia'),
            cpm_medicamento=Coalesce(F('medicamento__cpm_medicamento__valor'), Value(0), output_field=IntegerField())
        ).filter(existencia_total__gt=0).order_by('medicamento__descripcion')

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)

        logo_path = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')
        logo_width, logo_height = 7.0 * inch, 1.0 * inch
        x_logo = (width - logo_width) / 2
        y_logo = height - (0.75 * inch) - logo_height

        if os.path.exists(logo_path):
            try: p.drawImage(logo_path, x_logo, y_logo, width=logo_width, height=logo_height, preserveAspectRatio=True)
            except: pass

        y_actual = y_logo - (0.25 * inch)
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width / 2.0, y_actual, "REPORTE DE INVENTARIO GENERAL DE MEDICAMENTOS")
        y_actual -= 20
        p.setFont("Helvetica", 10)
        p.drawCentredString(width / 2.0, y_actual, f"Fecha del Reporte: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y_actual -= 20
        nombre_usuario = (request.user.get_full_name() or request.user.username).strip()
        p.drawCentredString(width / 2.0, y_actual, f"Generado por: {nombre_usuario}")
        y_actual -= 16
        p.line(inch, y_actual, width - inch, y_actual)
        y_actual -= 20

        styles = getSampleStyleSheet()
        desc_style = ParagraphStyle("desc", parent=styles["Normal"], fontName="Helvetica", fontSize=7, leading=8, alignment=TA_LEFT)

        data_tabla = [['Clave', 'Descripción', 'Existencia', 'CPM', 'Estado']]
        for item in inventario:
            existencia = item['existencia_total']
            estado = 'Adecuado'
            if existencia <= 10: estado = 'Crítico'
            elif existencia <= 50: estado = 'Bajo'
            elif existencia <= 100: estado = 'Medio'
            data_tabla.append([item['medicamento__clave'], Paragraph(item['medicamento__descripcion'] or "", desc_style), str(existencia), str(item['cpm_medicamento']), estado])

        ancho_disponible = width - (2 * inch)
        pesos = {"clave": 1.2, "descripcion": 6.0, "existencia": 1.1, "cpm": 0.9, "estado": 1.1}
        total_pesos = sum(pesos.values())
        col_widths = [ancho_disponible * (p / total_pesos) for p in pesos.values()]

        tabla = Table(data_tabla, colWidths=col_widths)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('LEFTPADDING', (1, 1), (1, -1), 4),
            ('RIGHTPADDING', (1, 1), (1, -1), 4),
        ]))

        wrap_height = tabla.wrapOn(p, width - 2*inch, height)[1]
        y_tabla = y_actual - wrap_height - 20
        if y_tabla < (inch * 2.5):
            p.showPage()
            y_tabla = height - inch - wrap_height

        tabla.drawOn(p, inch, y_tabla)
        p.setFont("Helvetica", 9)
        p.drawCentredString(width / 2.0, inch * 0.5, "Documento generado por INVENTFARM")

        p.showPage()
        p.save()
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Inventario_General_{datetime.now().strftime("%d%m%Y")}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)


@login_required
@permission_required('farmacia.view_reportes', raise_exception=True)
def reportes_farmacia(request):
    return render(request, 'reportes.html', {'user': request.user})


def obtener_medicamentos_sin_movimiento(fecha_inicio, fecha_fin):
    subquery_recetas = RecetaMedicamento.objects.filter(
        receta__fecha_surtido__range=[fecha_inicio, fecha_fin]
    ).values_list('medicamento_id', flat=True)

    subquery_transferencias = DetalleSalidaTransferencia.objects.filter(
        transferencia__fecha__date__range=[fecha_inicio, fecha_fin]
    ).values_list('lote__medicamento_id', flat=True)

    return (
        Lote.objects
        .filter(
            existencia__gt=0,
            medicamento__activo=True
        )
        .exclude(medicamento_id__in=subquery_recetas)
        .exclude(medicamento_id__in=subquery_transferencias)
        .values(
            'medicamento__id',
            'medicamento__clave',
            'medicamento__descripcion'
        )
        .annotate(
            existencia_total=Coalesce(Sum('existencia'), 0, output_field=IntegerField())
        )
        .order_by('medicamento__descripcion')
    )

@login_required
def api_reportes_kpis(request):
    try:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)
        if request.GET.get('fecha_inicio'): fecha_inicio = datetime.strptime(request.GET.get('fecha_inicio'), '%Y-%m-%d').date()
        if request.GET.get('fecha_fin'): fecha_fin = datetime.strptime(request.GET.get('fecha_fin'), '%Y-%m-%d').date()

        fecha_inicio_dt = make_aware(datetime.combine(fecha_inicio, datetime.min.time()))
        fecha_fin_dt = make_aware(datetime.combine(fecha_fin, datetime.max.time()))

        # Receta / colectivos
        total_salidas_receta = RecetaMedicamento.objects.filter(receta__fecha_surtido__range=[fecha_inicio, fecha_fin]).count()
        total_medicamentos_receta = RecetaMedicamento.objects.filter(receta__fecha_surtido__range=[fecha_inicio, fecha_fin]).aggregate(total=Sum('cantidad_surtida'))['total'] or 0
        total_pacientes = Receta.objects.filter(fecha_surtido__range=[fecha_inicio, fecha_fin]).values('paciente').distinct().count()
        valor_total_receta = RecetaMedicamento.objects.filter(receta__fecha_surtido__range=[fecha_inicio, fecha_fin]).aggregate(total=Sum('precio_total'))['total'] or 0

        # Transferencias
        transferencias_qs = DetalleSalidaTransferencia.objects.filter(
            transferencia__fecha__gte=fecha_inicio_dt,
            transferencia__fecha__lte=fecha_fin_dt
        )
        total_salidas_transferencia = transferencias_qs.count()
        total_medicamentos_transferencia = transferencias_qs.aggregate(total=Sum('cantidad'))['total'] or 0
        valor_total_transferencia = transferencias_qs.aggregate(total=Sum(F('cantidad') * F('costo_unitario'), output_field=DecimalField()))['total'] or 0
        total_instituciones = transferencias_qs.values('transferencia__institucion_destino').distinct().count()

        # Totales combinados (receta + transferencia)
        total_salidas = total_salidas_receta + total_salidas_transferencia
        total_medicamentos = total_medicamentos_receta + total_medicamentos_transferencia
        valor_total = float(valor_total_receta) + float(valor_total_transferencia)

        return JsonResponse({
            'success': True,
            'kpis': {
                'total_salidas': total_salidas,
                'total_medicamentos': total_medicamentos,
                'total_pacientes': total_pacientes,
                'valor_total': valor_total,
                'total_instituciones': total_instituciones
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def api_reportes_salidas(request):
    try:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)

        if request.GET.get('fecha_inicio'):
            fecha_inicio = datetime.strptime(
                request.GET.get('fecha_inicio'),
                '%Y-%m-%d'
            ).date()

        if request.GET.get('fecha_fin'):
            fecha_fin = datetime.strptime(
                request.GET.get('fecha_fin'),
                '%Y-%m-%d'
            ).date()

        datos_salidas = []

        # ===== SALIDAS POR RECETA / COLECTIVO =====
        salidas_receta = (
            RecetaMedicamento.objects
            .filter(receta__fecha_surtido__range=[fecha_inicio, fecha_fin])
            .select_related('receta__paciente', 'receta__surtido_por', 'medicamento', 'lote')
            .order_by('-receta__fecha_surtido')
        )

        for item in salidas_receta:
            fecha_str = item.receta.fecha_surtido.strftime('%Y-%m-%d')
            hora_str = (
                item.receta.fecha_surtido.strftime('%H:%M')
                if isinstance(item.receta.fecha_surtido, datetime)
                else '--:--'
            )

            tipo = 'Receta'
            tipo_badge = 'badge-receta'

            if item.receta.id_folio.startswith('COL-'):
                tipo = 'Colectivo - Paciente'
                tipo_badge = 'badge-colectivo'
            elif item.receta.id_folio.startswith('STK-'):
                tipo = 'Colectivo - Stock'
                tipo_badge = 'badge-stock'

            paciente_nombre = (
                item.receta.paciente.nombre_completo
                if item.receta.paciente else 'Stock/Servicio'
            )

            responsable_nombre = 'N/A'
            if item.receta.surtido_por:
                responsable_nombre = f"{item.receta.surtido_por.first_name} {item.receta.surtido_por.last_name}".strip()
                if not responsable_nombre:
                    responsable_nombre = item.receta.surtido_por.username

            datos_salidas.append({
                'id': item.receta.id,
                'folio': item.receta.id_folio,
                'fecha': fecha_str,
                'hora': hora_str,
                'clave': item.medicamento.clave or 'N/A',
                'medicamento': item.medicamento.descripcion,
                'lote': item.lote.lote_codigo if item.lote else 'N/A',
                'caducidad': item.lote.fecha_caducidad.strftime('%Y-%m-%d') if item.lote and item.lote.fecha_caducidad else 'N/A',
                'cantidad': item.cantidad_surtida,
                'paciente': paciente_nombre,
                'responsable': responsable_nombre,
                'valor': float(item.precio_total or 0),
                'precio_unitario': float(item.precio_unitario or 0),
                'tipo': tipo,
                'tipo_badge': tipo_badge,
                'destino': '',
                'pdf_url': reverse('descargar_comprobante', args=[item.receta.pk]),
            })

        # ===== SALIDAS POR TRANSFERENCIA =====
            fecha_inicio_dt = make_aware(datetime.combine(fecha_inicio, datetime.min.time()))
            fecha_fin_dt = make_aware(datetime.combine(fecha_fin, datetime.max.time()))

            salidas_transferencia = (
                DetalleSalidaTransferencia.objects
                .filter(
                    transferencia__fecha__gte=fecha_inicio_dt,
                    transferencia__fecha__lte=fecha_fin_dt
                )
                .select_related(
                    'transferencia__institucion_destino',
                    'transferencia__autorizado_por',
                    'lote__medicamento'
                )
                .order_by('-transferencia__fecha')
            )

        for item in salidas_transferencia:
            fecha_str = item.transferencia.fecha.strftime('%Y-%m-%d')
            hora_str = item.transferencia.fecha.strftime('%H:%M')

            responsable_nombre = 'N/A'
            if item.transferencia.autorizado_por:
                responsable_nombre = f"{item.transferencia.autorizado_por.first_name} {item.transferencia.autorizado_por.last_name}".strip()
                if not responsable_nombre:
                    responsable_nombre = item.transferencia.autorizado_por.username

            medicamento_obj = item.lote.medicamento if item.lote else None

            datos_salidas.append({
                'id': item.transferencia.id,
                'folio': item.transferencia.folio,
                'fecha': fecha_str,
                'hora': hora_str,
                'clave': medicamento_obj.clave if medicamento_obj else 'N/A',
                'medicamento': medicamento_obj.descripcion if medicamento_obj else 'N/A',
                'lote': item.lote.lote_codigo if item.lote else 'N/A',
                'caducidad': item.lote.fecha_caducidad.strftime('%Y-%m-%d') if item.lote and item.lote.fecha_caducidad else 'N/A',
                'cantidad': item.cantidad,
                'paciente': 'Transferencia',
                'responsable': responsable_nombre,
                'valor': float((item.cantidad or 0) * (item.costo_unitario or 0)),
                'precio_unitario': float(item.costo_unitario or 0),
                'tipo': 'Transferencia',
                'tipo_badge': 'badge-transferencia',
                'destino': item.transferencia.institucion_destino.nombre if item.transferencia.institucion_destino else 'N/A',
                'pdf_url': reverse('descargar_comprobante_transferencia', args=[item.transferencia.pk]),
            })

        datos_salidas = sorted(
            datos_salidas,
            key=lambda x: f"{x['fecha']} {x['hora']}",
            reverse=True
        )

        return JsonResponse({
            'success': True,
            'data': datos_salidas,
            'total': len(datos_salidas)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    
@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def exportar_medicamentos_sin_movimiento_pdf(request):
    """Exportar medicamentos sin movimiento a PDF"""
    try:
        import os
        from io import BytesIO
        from datetime import datetime

        from django.conf import settings
        from django.http import HttpResponse

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        )

        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)

        if request.GET.get('fecha_inicio'):
            fecha_inicio = datetime.strptime(
                request.GET.get('fecha_inicio'), '%Y-%m-%d'
            ).date()

        if request.GET.get('fecha_fin'):
            fecha_fin = datetime.strptime(
                request.GET.get('fecha_fin'), '%Y-%m-%d'
            ).date()

        medicamentos = list(
            obtener_medicamentos_sin_movimiento(fecha_inicio, fecha_fin)
        )

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
        )

        styles = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            name="TituloReporte",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=1,
            spaceAfter=4,
        )

        estilo_meta = ParagraphStyle(
            name="MetaReporte",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=1,
            spaceAfter=2,
        )

        estilo_header = ParagraphStyle(
            name="HeaderTabla",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,
            alignment=1,
            textColor=colors.whitesmoke,
        )

        estilo_celda = ParagraphStyle(
            name="CeldaTabla",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            alignment=0,
            wordWrap='LTR',
            splitLongWords=True
        )

        estilo_celda_centrada = ParagraphStyle(
            name="CeldaTablaCentrada",
            parent=estilo_celda,
            alignment=1,
        )

        elementos = []

        logo_path = os.path.join(
            settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=170 * mm, height=24 * mm)
            logo.hAlign = 'CENTER'
            elementos.append(logo)
            elementos.append(Spacer(1, 3 * mm))

        elementos.append(Paragraph(
            "BOLETINAJE DE MEDICAMENTOS SIN MOVIMIENTO",
            estilo_titulo
        ))

        fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
        nombre_usuario = (request.user.get_full_name() or request.user.username).strip()

        elementos.append(Paragraph(
            f"Periodo: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}",
            estilo_meta
        ))
        elementos.append(Paragraph(
            f"Fecha de Generación: {fecha_generacion}",
            estilo_meta
        ))
        elementos.append(Paragraph(
            f"Generado por: {nombre_usuario}",
            estilo_meta
        ))
        elementos.append(Spacer(1, 4 * mm))

        data_tabla = [[
            Paragraph("Clave", estilo_header),
            Paragraph("Descripción", estilo_header),
            Paragraph("Existencia Total", estilo_header),
        ]]

        for item in medicamentos:
            data_tabla.append([
                Paragraph(item['medicamento__clave'] or "N/A", estilo_celda_centrada),
                Paragraph(truncar_texto(item['medicamento__descripcion'] or "N/A", 180), estilo_celda),
                Paragraph(str(item['existencia_total'] or 0), estilo_celda_centrada),
            ])

        if not medicamentos:
            data_tabla.append([
                Paragraph("", estilo_celda),
                Paragraph(
                    "No se encontraron medicamentos sin movimiento para el periodo seleccionado.",
                    estilo_celda_centrada
                ),
                Paragraph("", estilo_celda),
            ])

        col_widths = [
            35 * mm,   # Clave
            110 * mm,  # Descripción
            36 * mm,   # Existencia Total
        ]

        tabla = Table(
            data_tabla,
            colWidths=col_widths,
            repeatRows=1,
            splitByRow=1,
            hAlign='LEFT',
        )

        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8B0000")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),

            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F4F4")]),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),

            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),

            ('ALIGN', (0, 1), (0, -1), 'CENTER'),    # Clave
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),    # Existencia
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(
            f"Documento generado por INVENTFARM - {nombre_usuario}",
            estilo_meta
        ))

        doc.build(elementos)

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="Medicamentos_Sin_Movimiento_{datetime.now().strftime("%d%m%Y")}.pdf"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)
    

@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def exportar_medicamentos_sin_movimiento_excel(request):
    try:
        import xlsxwriter

        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)

        if request.GET.get('fecha_inicio'):
            fecha_inicio = datetime.strptime(
                request.GET.get('fecha_inicio'),
                '%Y-%m-%d'
            ).date()

        if request.GET.get('fecha_fin'):
            fecha_fin = datetime.strptime(
                request.GET.get('fecha_fin'),
                '%Y-%m-%d'
            ).date()

        medicamentos = list(
            obtener_medicamentos_sin_movimiento(fecha_inicio, fecha_fin)
        )

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Sin Movimiento')

        header_format = workbook.add_format({
            'bg_color': '#8B0000',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11
        })

        title_format = workbook.add_format({
            'bg_color': '#8B0000',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14
        })

        date_format = workbook.add_format({
            'italic': True,
            'align': 'left',
            'font_size': 10
        })

        text_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10
        })

        number_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10,
            'num_format': '#,##0'
        })

        worksheet.set_column('A:A', 18)
        worksheet.set_column('B:B', 55)
        worksheet.set_column('C:C', 18)

        logo_path = os.path.join(
            settings.BASE_DIR,
            'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            try:
                worksheet.insert_image('A1', logo_path, {'x_scale': 0.8, 'y_scale': 0.8})
            except Exception:
                pass

        worksheet.merge_range(
            'A3:C3',
            'BOLETINAJE DE MEDICAMENTOS SIN MOVIMIENTO',
            title_format
        )
        worksheet.merge_range(
            'A4:C4',
            f'Periodo: {fecha_inicio.strftime("%d/%m/%Y")} al {fecha_fin.strftime("%d/%m/%Y")}',
            date_format
        )
        worksheet.merge_range(
            'A5:C5',
            f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
            date_format
        )

        headers = ['Clave', 'Descripción', 'Existencia Total']
        for col, header in enumerate(headers):
            worksheet.write(6, col, header, header_format)

        row = 7
        for item in medicamentos:
            worksheet.write(row, 0, item['medicamento__clave'], text_format)
            worksheet.write(row, 1, item['medicamento__descripcion'], text_format)
            worksheet.write_number(row, 2, item['existencia_total'], number_format)
            row += 1

        if not medicamentos:
            worksheet.merge_range(
                'A8:C8',
                'No se encontraron medicamentos sin movimiento para el periodo seleccionado.',
                text_format
            )

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="Medicamentos_Sin_Movimiento_{datetime.now().strftime("%d%m%Y")}.xlsx"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)


@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def api_medicamentos_sin_movimiento(request):
    try:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)

        if request.GET.get('fecha_inicio'):
            fecha_inicio = datetime.strptime(
                request.GET.get('fecha_inicio'),
                '%Y-%m-%d'
            ).date()

        if request.GET.get('fecha_fin'):
            fecha_fin = datetime.strptime(
                request.GET.get('fecha_fin'),
                '%Y-%m-%d'
            ).date()

        medicamentos = list(
            obtener_medicamentos_sin_movimiento(fecha_inicio, fecha_fin)
        )

        return JsonResponse({
            'success': True,
            'data': medicamentos,
            'total': len(medicamentos),
            'fecha_inicio': str(fecha_inicio),
            'fecha_fin': str(fecha_fin),
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def api_reportes_medicamentos_top(request):
    try:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)
        if request.GET.get('fecha_inicio'): fecha_inicio = datetime.strptime(request.GET.get('fecha_inicio'), '%Y-%m-%d').date()
        if request.GET.get('fecha_fin'): fecha_fin = datetime.strptime(request.GET.get('fecha_fin'), '%Y-%m-%d').date()
        
        medicamentos_top = RecetaMedicamento.objects.filter(receta__fecha_surtido__range=[fecha_inicio, fecha_fin]).values('medicamento__id', 'medicamento__descripcion', 'medicamento__clave').annotate(total_dispensado=Sum('cantidad_surtida')).order_by('-total_dispensado')[:10]
        
        datos = [{'medicamento': med['medicamento__descripcion'], 'clave': med['medicamento__clave'], 'cantidad': med['total_dispensado']} for med in medicamentos_top]
        return JsonResponse({'success': True, 'data': datos})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def api_reportes_pacientes_frecuentes(request):
    try:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)
        if request.GET.get('fecha_inicio'): fecha_inicio = datetime.strptime(request.GET.get('fecha_inicio'), '%Y-%m-%d').date()
        if request.GET.get('fecha_fin'): fecha_fin = datetime.strptime(request.GET.get('fecha_fin'), '%Y-%m-%d').date()
        
        pacientes_top = Receta.objects.filter(fecha_surtido__range=[fecha_inicio, fecha_fin]).values('paciente__id', 'paciente__nombre_completo').annotate(total_visitas=Count('id'), total_medicamentos=Sum('recetamedicamento__cantidad_surtida'), ultima_visita=Max('fecha_surtido')).order_by('-total_visitas')[:10]
        
        datos = [{'paciente': pac['paciente__nombre_completo'], 'visitas': pac['total_visitas'], 'medicamentos': pac['total_medicamentos'] or 0, 'ultima_visita': pac['ultima_visita'].strftime('%Y-%m-%d') if pac['ultima_visita'] else 'N/A', 'gasto_total': 0} for pac in pacientes_top]
        return JsonResponse({'success': True, 'data': datos})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def api_reportes_tendencias(request):
    try:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=365)
        
        salidas_por_mes = RecetaMedicamento.objects.filter(receta__fecha_surtido__range=[fecha_inicio, fecha_fin]).annotate(mes=TruncMonth('receta__fecha_surtido')).values('mes').annotate(total=Count('id')).order_by('mes')
        
        meses = [item['mes'].strftime('%b %Y') for item in salidas_por_mes]
        totales = [item['total'] for item in salidas_por_mes]
        return JsonResponse({'success': True, 'meses': meses, 'totales': totales})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def api_medicamentos_lento_movimiento(request):
    try:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)

        if request.GET.get('fecha_inicio'):
            fecha_inicio = datetime.strptime(
                request.GET.get('fecha_inicio'),
                '%Y-%m-%d'
            ).date()

        if request.GET.get('fecha_fin'):
            fecha_fin = datetime.strptime(
                request.GET.get('fecha_fin'),
                '%Y-%m-%d'
            ).date()

        fecha_inicio_dt = make_aware(datetime.combine(fecha_inicio, datetime.min.time()))
        fecha_fin_dt = make_aware(datetime.combine(fecha_fin, datetime.max.time()))

        conteo_salidas = defaultdict(int)
        metadata_medicamentos = {}

        # ===== Salidas por receta (unidades reales dispensadas) =====
        salidas_receta = (
            RecetaMedicamento.objects
            .filter(
                receta__fecha_surtido__range=[fecha_inicio, fecha_fin],
                medicamento__activo=True
            )
            .values(
                'medicamento_id',
                'medicamento__clave',
                'medicamento__descripcion'
            )
            .annotate(
                total_unidades=Coalesce(Sum('cantidad_surtida'), 0, output_field=IntegerField())
            )
        )

        for item in salidas_receta:
            medicamento_id = item['medicamento_id']
            conteo_salidas[medicamento_id] += item['total_unidades']

            metadata_medicamentos[medicamento_id] = {
                'id': medicamento_id,
                'clave': item['medicamento__clave'],
                'descripcion': item['medicamento__descripcion'],
            }

        # ===== Salidas por transferencia (unidades reales enviadas) =====
        salidas_transferencia = (
            DetalleSalidaTransferencia.objects
            .filter(
                transferencia__fecha__gte=fecha_inicio_dt,
                transferencia__fecha__lte=fecha_fin_dt,
                lote__medicamento__activo=True
            )
            .values(
                'lote__medicamento_id',
                'lote__medicamento__clave',
                'lote__medicamento__descripcion'
            )
            .annotate(
                total_unidades=Coalesce(Sum('cantidad'), 0, output_field=IntegerField())
            )
        )

        for item in salidas_transferencia:
            medicamento_id = item['lote__medicamento_id']
            conteo_salidas[medicamento_id] += item['total_unidades']

            if medicamento_id not in metadata_medicamentos:
                metadata_medicamentos[medicamento_id] = {
                    'id': medicamento_id,
                    'clave': item['lote__medicamento__clave'],
                    'descripcion': item['lote__medicamento__descripcion'],
                }

        # ===== Filtrar por unidades dispensadas entre 1 y 5 =====
        medicamentos_ids = [
            medicamento_id
            for medicamento_id, total in conteo_salidas.items()
            if 1 <= total <= 5
        ]

        existencias = (
            Lote.objects
            .filter(medicamento_id__in=medicamentos_ids, medicamento__activo=True)
            .values('medicamento_id')
            .annotate(existencia_total=Coalesce(Sum('existencia'), 0, output_field=IntegerField()))
        )

        lotes = (
            Lote.objects
            .filter(
                medicamento_id__in=medicamentos_ids,
                medicamento__activo=True,
                existencia__gt=0
            )
            .select_related('medicamento')
            .order_by('medicamento__descripcion', 'fecha_caducidad', 'lote_codigo')
        )

        data = []
        for lote in lotes:
            total_salidas = conteo_salidas.get(lote.medicamento_id, 0)

            data.append({
                'medicamento_id': lote.medicamento_id,
                'clave': lote.medicamento.clave or 'N/A',
                'descripcion': lote.medicamento.descripcion,
                'lote': lote.lote_codigo or 'N/A',
                'caducidad': lote.fecha_caducidad.strftime('%Y-%m-%d') if lote.fecha_caducidad else 'N/A',
                'salidas': total_salidas,
                'existencia_actual': lote.existencia,
            })

        return JsonResponse({
            'success': True,
            'data': data,
            'total': len(data),
            'fecha_inicio': str(fecha_inicio),
            'fecha_fin': str(fecha_fin),
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        

@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def exportar_medicamentos_lento_movimiento_pdf(request):
    """Exportar medicamentos de lento movimiento a PDF"""
    try:
        import os
        from io import BytesIO
        from datetime import datetime
        from collections import defaultdict

        from django.conf import settings
        from django.http import HttpResponse
        from django.db.models import Sum, IntegerField
        from django.db.models.functions import Coalesce
        from django.utils import timezone
        from django.utils.timezone import make_aware

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        )

        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)

        if request.GET.get('fecha_inicio'):
            fecha_inicio = datetime.strptime(
                request.GET.get('fecha_inicio'), '%Y-%m-%d'
            ).date()

        if request.GET.get('fecha_fin'):
            fecha_fin = datetime.strptime(
                request.GET.get('fecha_fin'), '%Y-%m-%d'
            ).date()

        fecha_inicio_dt = make_aware(datetime.combine(fecha_inicio, datetime.min.time()))
        fecha_fin_dt = make_aware(datetime.combine(fecha_fin, datetime.max.time()))

        conteo_salidas = defaultdict(int)

        salidas_receta = (
            RecetaMedicamento.objects
            .filter(
                receta__fecha_surtido__range=[fecha_inicio, fecha_fin],
                medicamento__activo=True
            )
            .values(
                'medicamento_id',
                'medicamento__clave',
                'medicamento__descripcion'
            )
            .annotate(
                total_unidades=Coalesce(Sum('cantidad_surtida'), 0, output_field=IntegerField())
            )
        )

        for item in salidas_receta:
            medicamento_id = item['medicamento_id']
            conteo_salidas[medicamento_id] += item['total_unidades']

        salidas_transferencia = (
            DetalleSalidaTransferencia.objects
            .filter(
                transferencia__fecha__gte=fecha_inicio_dt,
                transferencia__fecha__lte=fecha_fin_dt,
                lote__medicamento__activo=True
            )
            .values(
                'lote__medicamento_id',
                'lote__medicamento__clave',
                'lote__medicamento__descripcion'
            )
            .annotate(
                total_unidades=Coalesce(Sum('cantidad'), 0, output_field=IntegerField())
            )
        )

        for item in salidas_transferencia:
            medicamento_id = item['lote__medicamento_id']
            conteo_salidas[medicamento_id] += item['total_unidades']

        medicamentos_ids = [
            medicamento_id
            for medicamento_id, total in conteo_salidas.items()
            if 1 <= total <= 5
        ]

        lotes = (
            Lote.objects
            .filter(
                medicamento_id__in=medicamentos_ids,
                medicamento__activo=True,
                existencia__gt=0
            )
            .select_related('medicamento')
            .order_by('medicamento__descripcion', 'fecha_caducidad', 'lote_codigo')
        )

        data = []
        for lote in lotes:
            total_salidas = conteo_salidas.get(lote.medicamento_id, 0)

            data.append({
                'clave': lote.medicamento.clave or 'N/A',
                'descripcion': lote.medicamento.descripcion or 'N/A',
                'lote': lote.lote_codigo or 'N/A',
                'caducidad': lote.fecha_caducidad.strftime('%Y-%m-%d') if lote.fecha_caducidad else 'N/A',
                'salidas': total_salidas,
                'existencia_actual': lote.existencia or 0,
            })

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=10 * mm,
            rightMargin=10 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
        )

        styles = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            name="TituloReporte",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=1,
            spaceAfter=4,
        )

        estilo_meta = ParagraphStyle(
            name="MetaReporte",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=1,
            spaceAfter=2,
        )

        estilo_header = ParagraphStyle(
            name="HeaderTabla",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=1,
            textColor=colors.whitesmoke,
        )

        estilo_celda = ParagraphStyle(
            name="CeldaTabla",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8,
            alignment=0,
            wordWrap='LTR',
            splitLongWords=True
        )

        estilo_celda_centrada = ParagraphStyle(
            name="CeldaTablaCentrada",
            parent=estilo_celda,
            alignment=1,
        )

        elementos = []

        logo_path = os.path.join(
            settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=170 * mm, height=24 * mm)
            logo.hAlign = 'CENTER'
            elementos.append(logo)
            elementos.append(Spacer(1, 3 * mm))

        elementos.append(Paragraph(
            "BOLETINAJE DE MEDICAMENTOS DE LENTO MOVIMIENTO",
            estilo_titulo
        ))

        fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
        nombre_usuario = (request.user.get_full_name() or request.user.username).strip()

        elementos.append(Paragraph(
            f"Periodo: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}",
            estilo_meta
        ))
        elementos.append(Paragraph(
            f"Fecha de Generación: {fecha_generacion}",
            estilo_meta
        ))
        elementos.append(Paragraph(
            f"Generado por: {nombre_usuario}",
            estilo_meta
        ))
        elementos.append(Spacer(1, 4 * mm))

        data_tabla = [[
            Paragraph("Clave", estilo_header),
            Paragraph("Descripción", estilo_header),
            Paragraph("Lote", estilo_header),
            Paragraph("Caducidad", estilo_header),
            Paragraph("Salidas", estilo_header),
            Paragraph("Existencia Actual", estilo_header),
        ]]

        for item in data:
            data_tabla.append([
                Paragraph(item['clave'], estilo_celda_centrada),
                Paragraph(truncar_texto(item['descripcion'], 120), estilo_celda),
                Paragraph(item['lote'], estilo_celda_centrada),
                Paragraph(item['caducidad'], estilo_celda_centrada),
                Paragraph(str(item['salidas']), estilo_celda_centrada),
                Paragraph(str(item['existencia_actual']), estilo_celda_centrada),
            ])

        if not data:
            data_tabla.append([
                Paragraph("", estilo_celda),
                Paragraph(
                    "No se encontraron medicamentos de lento movimiento para el periodo seleccionado.",
                    estilo_celda_centrada
                ),
                Paragraph("", estilo_celda),
                Paragraph("", estilo_celda),
                Paragraph("", estilo_celda),
                Paragraph("", estilo_celda),
            ])

        col_widths = [
            24 * mm,   # Clave
            72 * mm,   # Descripción
            24 * mm,   # Lote
            28 * mm,   # Caducidad
            18 * mm,   # Salidas
            24 * mm,   # Existencia
        ]

        tabla = Table(
            data_tabla,
            colWidths=col_widths,
            repeatRows=1,
            splitByRow=1,
            hAlign='LEFT',
        )

        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8B0000")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),

            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F4F4")]),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),

            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),

            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (5, -1), 'CENTER'),
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(
            f"Documento generado por INVENTFARM - {nombre_usuario}",
            estilo_meta
        ))

        doc.build(elementos)

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="Medicamentos_Lento_Movimiento_{datetime.now().strftime("%d%m%Y")}.pdf"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)


@login_required
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
def exportar_medicamentos_lento_movimiento_excel(request):
    try:
        import os
        import xlsxwriter
        from io import BytesIO
        from datetime import datetime, timedelta
        from collections import defaultdict

        from django.conf import settings
        from django.http import HttpResponse
        from django.db.models import Sum, IntegerField
        from django.db.models.functions import Coalesce
        from django.utils import timezone
        from django.utils.timezone import make_aware

        from farmacia.models import Lote, RecetaMedicamento, DetalleSalidaTransferencia

        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=90)

        if request.GET.get('fecha_inicio'):
            fecha_inicio = datetime.strptime(
                request.GET.get('fecha_inicio'),
                '%Y-%m-%d'
            ).date()

        if request.GET.get('fecha_fin'):
            fecha_fin = datetime.strptime(
                request.GET.get('fecha_fin'),
                '%Y-%m-%d'
            ).date()

        fecha_inicio_dt = make_aware(datetime.combine(fecha_inicio, datetime.min.time()))
        fecha_fin_dt = make_aware(datetime.combine(fecha_fin, datetime.max.time()))

        conteo_salidas = defaultdict(int)

        salidas_receta = (
            RecetaMedicamento.objects
            .filter(
                receta__fecha_surtido__range=[fecha_inicio, fecha_fin],
                medicamento__activo=True
            )
            .values('medicamento_id')
            .annotate(
                total_unidades=Coalesce(
                    Sum('cantidad_surtida'),
                    0,
                    output_field=IntegerField()
                )
            )
        )

        for item in salidas_receta:
            conteo_salidas[item['medicamento_id']] += item['total_unidades']

        salidas_transferencia = (
            DetalleSalidaTransferencia.objects
            .filter(
                transferencia__fecha__gte=fecha_inicio_dt,
                transferencia__fecha__lte=fecha_fin_dt,
                lote__medicamento__activo=True
            )
            .values('lote__medicamento_id')
            .annotate(
                total_unidades=Coalesce(
                    Sum('cantidad'),
                    0,
                    output_field=IntegerField()
                )
            )
        )

        for item in salidas_transferencia:
            conteo_salidas[item['lote__medicamento_id']] += item['total_unidades']

        medicamentos_ids = [
            medicamento_id
            for medicamento_id, total in conteo_salidas.items()
            if 1 <= total <= 5
        ]

        lotes = (
            Lote.objects
            .filter(
                medicamento_id__in=medicamentos_ids,
                medicamento__activo=True,
                existencia__gt=0
            )
            .select_related('medicamento')
            .order_by('medicamento__descripcion', 'fecha_caducidad', 'lote_codigo')
        )

        data = []
        for lote in lotes:
            total_salidas = conteo_salidas.get(lote.medicamento_id, 0)
            data.append({
                'clave': lote.medicamento.clave or 'N/A',
                'descripcion': lote.medicamento.descripcion or 'N/A',
                'lote': lote.lote_codigo or 'N/A',
                'caducidad': lote.fecha_caducidad,
                'salidas': total_salidas,
                'existencia_actual': lote.existencia or 0,
            })

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Lento Movimiento')

        header_format = workbook.add_format({
            'bg_color': '#8B0000',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11
        })

        title_format = workbook.add_format({
            'bg_color': '#8B0000',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14
        })

        date_format = workbook.add_format({
            'italic': True,
            'align': 'left',
            'font_size': 10
        })

        text_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10
        })

        number_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10,
            'num_format': '#,##0'
        })

        date_cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10,
            'num_format': 'dd/mm/yyyy'
        })

        worksheet.set_column('A:A', 18)
        worksheet.set_column('B:B', 55)
        worksheet.set_column('C:C', 18)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:E', 12)
        worksheet.set_column('F:F', 18)

        logo_path = os.path.join(
            settings.BASE_DIR,
            'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            try:
                worksheet.insert_image('A1', logo_path, {'x_scale': 0.8, 'y_scale': 0.8})
            except Exception:
                pass

        worksheet.merge_range(
            'A3:F3',
            'BOLETINAJE DE MEDICAMENTOS DE LENTO MOVIMIENTO',
            title_format
        )
        worksheet.merge_range(
            'A4:F4',
            f'Periodo: {fecha_inicio.strftime("%d/%m/%Y")} al {fecha_fin.strftime("%d/%m/%Y")}',
            date_format
        )
        worksheet.merge_range(
            'A5:F5',
            f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
            date_format
        )

        headers = ['Clave', 'Descripción', 'Lote', 'Caducidad', 'Salidas', 'Existencia Actual']
        for col, header in enumerate(headers):
            worksheet.write(6, col, header, header_format)

        row = 7
        for item in data:
            worksheet.write(row, 0, item['clave'], text_format)
            worksheet.write(row, 1, item['descripcion'], text_format)
            worksheet.write(row, 2, item['lote'], text_format)

            if item['caducidad']:
                worksheet.write_datetime(
                    row,
                    3,
                    datetime.combine(item['caducidad'], datetime.min.time()),
                    date_cell_format
                )
            else:
                worksheet.write(row, 3, 'N/A', text_format)

            worksheet.write_number(row, 4, item['salidas'], number_format)
            worksheet.write_number(row, 5, item['existencia_actual'], number_format)
            row += 1

        if not data:
            worksheet.merge_range(
                'A8:F8',
                'No se encontraron medicamentos de lento movimiento para el periodo seleccionado.',
                text_format
            )

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="Medicamentos_Lento_Movimiento_{datetime.now().strftime("%d%m%Y")}.xlsx"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)