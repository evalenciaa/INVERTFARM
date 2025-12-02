import os
from io import BytesIO
from django.conf import settings
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from django.utils.timezone import now
from .models import RecetaMedicamento, MedicamentoNoSurtido
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import pytz


def generar_pdf_salida(receta):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # Ancho: 8.5 inch, Alto: 11 inch
    
    # ✅ Obtener la hora en zona de México
    zona_mexico = pytz.timezone(settings.TIME_ZONE)
    fecha_actual = now().astimezone(zona_mexico)
    
    # --- 1. Encabezado y Logos ---
    logo_path_abs = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')
    
    # Dimensiones del logo
    logo_width = 7.0 * inch
    logo_height = 1.0 * inch
    x_logo = (width - logo_width) / 2
    y_logo = height - (0.75 * inch) - logo_height
    
    # Dibujar logo
    if logo_path_abs and os.path.exists(logo_path_abs):
        try:
            p.drawImage(logo_path_abs, x_logo, y_logo,
                       width=logo_width, height=logo_height,
                       preserveAspectRatio=True)
        except Exception as e:
            print(f"Error al dibujar logo.jpg: {e}")
    else:
        print("ADVERTENCIA: No se encontró logo.jpg en la ruta esperada.")
    
    # Posición Y para el resto del contenido
    y_actual = y_logo - (0.25 * inch)
    
    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2.0, y_actual, "Comprobante de Salida de Farmacia")
    y_actual -= 20
    
    # ✅ AQUÍ ESTÁ LA HORA CORREGIDA:
    p.setFont("Helvetica", 10)
    p.drawCentredString(width / 2.0, y_actual, f"Fecha de Emisión: {fecha_actual.strftime('%d/%m/%Y %H:%M')}")
    y_actual -= 20
    
    # Línea divisoria
    p.line(inch, y_actual, width - inch, y_actual)
    y_actual -= 20
    
    # --- 2. Datos del Paciente y Receta ---
    y_start_datos = y_actual
    
    # Columna izquierda: Datos del Paciente
    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, y_start_datos, "Datos del Paciente")
    p.setFont("Helvetica", 10)
    p.drawString(inch, y_start_datos - 20, f"Paciente: {receta.paciente.nombre_completo}")
    p.drawString(inch, y_start_datos - 35, f"CURP: {receta.paciente.curp or 'N/A'}")
    
    fecha_nac = receta.paciente.fecha_nacimiento
    fecha_str = "N/A"
    if isinstance(fecha_nac, date):
        fecha_str = fecha_nac.strftime('%d/%m/%Y')
    elif fecha_nac:
        fecha_str = str(fecha_nac)
    p.drawString(inch, y_start_datos - 50, f"Fecha Nac: {fecha_str}")
    
    # Columna derecha: Datos de la Receta
    p.setFont("Helvetica-Bold", 12)
    p.drawString(width / 2, y_start_datos, "Datos de la Receta")
    p.setFont("Helvetica", 10)
    p.drawString(width / 2, y_start_datos - 20, f"Folio: {receta.id_folio}")
    p.drawString(width / 2, y_start_datos - 35, f"Origen: {receta.origen}")
    p.drawString(width / 2, y_start_datos - 50, f"Fecha Surtido: {receta.fecha_surtido.strftime('%d/%m/%Y')}")
    
    # --- 3. TABLA DE MEDICAMENTOS SURTIDOS ---
    y_start_meds = y_start_datos - 80
    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, y_start_meds, "Medicamentos Surtidos")
    
    items = RecetaMedicamento.objects.filter(receta=receta).select_related(
        'medicamento', 'lote'
    ).order_by('medicamento__descripcion')
    
    data_tabla = [['Clave', 'Descripción', 'Lote', 'Cant.']]
    max_desc_len = 50
    
    for item in items:
        desc = item.medicamento.descripcion
        if len(desc) > max_desc_len:
            desc = desc[:max_desc_len] + "..."
        data_tabla.append([
            item.medicamento.clave,
            desc,
            item.lote.lote_codigo if item.lote else 'N/A',
            item.cantidad_surtida
        ])
    
    # Si no hay medicamentos surtidos
    if len(data_tabla) == 1:
        data_tabla.append(['---', 'No se surtió ningún medicamento', '---', '0'])
    
    tabla = Table(data_tabla, colWidths=[1.5*inch, 4*inch, 1*inch, 0.5*inch])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#343a40")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
    ]))
    
    wrap_height = tabla.wrapOn(p, width - 2*inch, height)[1]
    y_tabla = y_start_meds - wrap_height - 20
    
    # Verificar si hay espacio suficiente
    if y_tabla < (inch * 2.5):
        p.showPage()
        y_tabla = height - inch - wrap_height
    
    tabla.drawOn(p, inch, y_tabla)
    y_actual = y_tabla - 30  # Posición después de la tabla
    
    # --- 4. MEDICAMENTOS NO DISPONIBLES ---
    medicamentos_faltantes = MedicamentoNoSurtido.objects.filter(
        receta=receta
    ).order_by('medicamento_descripcion')
    
    if medicamentos_faltantes.exists():
        # Título de la sección
        p.setFont("Helvetica-Bold", 12)
        p.setFillColorRGB(0.8, 0.4, 0)  # Color naranja/amarillo para advertencia
        p.drawString(inch, y_actual, "⚠ Medicamentos No Disponibles")
        p.setFillColorRGB(0, 0, 0)  # Volver a negro
        y_actual -= 20
        
        # Crear tabla de faltantes
        data_faltantes = [['Medicamento', 'Cant. Solicitada', 'Motivo']]
        
        for faltante in medicamentos_faltantes:
            desc = faltante.medicamento_descripcion
            if len(desc) > 40:
                desc = desc[:40] + "..."
            
            motivo = faltante.motivo
            if len(motivo) > 50:
                motivo = motivo[:50] + "..."
            
            data_faltantes.append([
                desc,
                str(faltante.cantidad_solicitada),
                motivo
            ])
        
        tabla_faltantes = Table(data_faltantes, colWidths=[2.5*inch, 1.5*inch, 3*inch])
        tabla_faltantes.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ffc107")),  # Amarillo
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#fff3cd")),  # Amarillo claro
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        wrap_height_faltantes = tabla_faltantes.wrapOn(p, width - 2*inch, height)[1]
        y_tabla_faltantes = y_actual - wrap_height_faltantes - 10
        
        # Si no cabe en la página actual, crear nueva página
        if y_tabla_faltantes < (inch * 2):
            p.showPage()
            y_tabla_faltantes = height - inch - wrap_height_faltantes
        
        tabla_faltantes.drawOn(p, inch, y_tabla_faltantes)
    
    # Finalizar PDF
    p.save()
    buffer.seek(0)
    return buffer
