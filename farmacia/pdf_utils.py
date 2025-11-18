import os
from io import BytesIO
from django.conf import settings 
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from django.utils.timezone import now
from .models import RecetaMedicamento 
from datetime import date 
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle 
from reportlab.lib import colors

def generar_pdf_salida(receta):
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter # Ancho: 8.5 inch, Alto: 11 inch
    
    # --- 1. Encabezado y Logos (¡CORREGIDO SOLO 1 LOGO!) ---
    
    # Ruta (solo para logo.jpg)
    logo_path_abs = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')

    # ========================================================
    # ==== ¡NUEVA LÓGICA DE TAMAÑO Y POSICIÓN (1 LOGO)! ====
    # ========================================================
    # Dimensiones 1236x175 (Ratio ~7:1)
    # Le daremos 7 pulgadas de ancho, lo que da ~1 pulgada de alto.
    logo_width = 7.0 * inch
    logo_height = 1.0 * inch # Esta es la "caja" de altura
    
    # Coordenada X (Centrado)
    # (Ancho total - Ancho del logo) / 2
    x_logo = (width - logo_width) / 2  # (8.5 - 7.0) / 2 = 0.75 inch de margen
    
    # Coordenada Y (Altura)
    # (Altura total) - (Margen superior de 0.75 pulgadas) - (Altura del logo)
    y_logo = height - (0.75 * inch) - logo_height # 11 - 0.75 - 1 = 9.25 inch
    # ========================================================

    # Dibujamos SOLO 'logo.jpg'
    if logo_path_abs and os.path.exists(logo_path_abs):
        try: 
            p.drawImage(logo_path_abs, x_logo, y_logo, 
                        width=logo_width, height=logo_height, 
                        preserveAspectRatio=True) # preserveAspectRatio es clave
        except Exception as e: print(f"Error al dibujar logo.jpg: {e}")
    else:
        print("ADVERTENCIA: No se encontró logo.jpg en la ruta esperada.")
            
    # (Hemos eliminado todo el código de imss_bienestar.jpg)

    # ========================================================
    # Posición Y para el resto del contenido
    # ========================================================
    # Colocamos el título 0.25 pulgadas DEBAJO de la parte inferior del logo
    y_actual = y_logo - (0.25 * inch) 

    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2.0, y_actual, "Comprobante de Salida de Farmacia")
    y_actual -= 20 # Bajamos 20 puntos
    p.setFont("Helvetica", 10)
    p.drawCentredString(width / 2.0, y_actual, f"Fecha de Emisión: {now().strftime('%d/%m/%Y %H:%M')}")
    y_actual -= 20 # Bajamos 20 puntos
    
    # Línea divisoria
    p.line(inch, y_actual, width - inch, y_actual)
    y_actual -= 20 # Espacio

    # --- 2. Datos del Paciente y Receta ---
    y_start_datos = y_actual # Empezar desde donde nos quedamos

    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, y_start_datos, "Datos del Paciente")
    p.setFont("Helvetica", 10)
    p.drawString(inch, y_start_datos - 20, f"Paciente: {receta.paciente.nombre_completo}")
    p.drawString(inch, y_start_datos - 35, f"CURP: {receta.paciente.curp}")

    fecha_nac = receta.paciente.fecha_nacimiento
    fecha_str = "N/A"
    if isinstance(fecha_nac, date):
        fecha_str = fecha_nac.strftime('%d/%m/%Y')
    elif fecha_nac:
        fecha_str = str(fecha_nac)
    p.drawString(inch, y_start_datos - 50, f"Fecha Nac: {fecha_str}")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(width / 2, y_start_datos, "Datos de la Receta")
    p.setFont("Helvetica", 10)
    p.drawString(width / 2, y_start_datos - 20, f"Folio: {receta.id_folio}")
    p.drawString(width / 2, y_start_datos - 35, f"Origen: {receta.origen}")
    p.drawString(width / 2, y_start_datos - 50, f"Fecha Surtido: {receta.fecha_surtido.strftime('%d/%m/%Y')}")

    # --- 3. Datos del Medicamento (Tabla) ---
    y_start_meds = y_start_datos - 80
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, y_start_meds, "Medicamentos Surtidos")

    items = RecetaMedicamento.objects.filter(receta=receta).select_related('medicamento', 'lote').order_by('medicamento__descripcion')

    data_tabla = [['Clave', 'Descripción', 'Lote', 'Cant.']]
    max_desc_len = 50
    for item in items:
        desc = item.medicamento.descripcion
        if len(desc) > max_desc_len: desc = desc[:max_desc_len] + "..."
        data_tabla.append([
            item.medicamento.clave,
            desc,
            item.lote.lote_codigo if item.lote else 'N/A',
            item.cantidad_surtida
        ])

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
    
    if y_tabla < (inch * 2.5):
        p.showPage()
        y_tabla = height - inch - wrap_height
        
    tabla.drawOn(p, inch, y_tabla)

    # --- 4. Pie de página ---
    p.setFont("Helvetica", 10)
    
    surtido_por_str = "N/A"
    if receta.surtido_por:
        surtido_por_str = f"{receta.surtido_por.first_name} {receta.surtido_por.last_name}"
        if not surtido_por_str.strip(): # Si el nombre está vacío
            surtido_por_str = receta.surtido_por.username
    
    p.drawString(inch, inch * 1.5, f"Surtido por: {surtido_por_str}")
    
    p.line(inch, inch * 1.3, width - inch, inch * 1.3)
    p.drawCentredString(width / 2.0, inch, "Documento generado por INVENTFARM")

    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer