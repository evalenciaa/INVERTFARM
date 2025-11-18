// qr-generator.js - Sistema de generación de códigos QR en PDF (CORREGIDO)
console.log('🎯 Cargando sistema de generación de QR en PDF');

// Función para inicializar el sistema de QR
function inicializarSistemaQR() {
    // Botón para generar QR para todos
    const btnGenerarTodosQR = document.getElementById('btn-generar-todos-qr');
    if (btnGenerarTodosQR) {
        btnGenerarTodosQR.addEventListener('click', generarQRParaTodosPDF);
    }

    // Asignar eventos a botones individuales de QR
    document.querySelectorAll('.btn-generar-qr').forEach(btn => {
        btn.addEventListener('click', function() {
            const fila = this.closest('tr');
            
            // OBTENER CLAVE CORRECTAMENTE - es texto en la primera celda (td)
            const primeraCelda = fila.querySelector('td:first-child');
            const clave = primeraCelda ? primeraCelda.textContent.trim() : 'N/A';
            
            const lote = fila.querySelector('input[name^="lote_codigo_"]').value;
            const caducidad = fila.dataset.fecha;
            const existencia = parseInt(fila.dataset.existencia);
            const descripcion = fila.querySelector('.campo-descripcion').value;
            
            generarQRIndividualPDF(clave, lote, caducidad, existencia, descripcion);
        });
    });

    console.log('✅ Sistema de QR PDF inicializado');
}

// Función para dividir texto en líneas que quepan en el PDF
function dividirTexto(texto, maxWidth, doc, fontSize) {
    const words = texto.split(' ');
    const lines = [];
    let currentLine = '';

    doc.setFontSize(fontSize);
    
    for (let i = 0; i < words.length; i++) {
        const word = words[i];
        const testLine = currentLine ? `${currentLine} ${word}` : word;
        const testWidth = doc.getTextWidth(testLine);
        
        if (testWidth > maxWidth && currentLine) {
            lines.push(currentLine);
            currentLine = word;
        } else {
            currentLine = testLine;
        }
    }
    
    if (currentLine) {
        lines.push(currentLine);
    }
    
    return lines;
}

// Función para generar QR individual en PDF
function generarQRIndividualPDF(clave, lote, caducidad, existencia, descripcion) {
    // Crear PDF
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    // Título del documento
    doc.setFontSize(16);
    doc.text('Códigos QR de Medicamento', 105, 15, { align: 'center' });
    
    // Información del medicamento (con texto dividido)
    doc.setFontSize(10);
    
    // Dividir la descripción si es muy larga
    const descLines = dividirTexto(descripcion, 180, doc, 10);
    let yPosition = 25;
    
    doc.text(`Medicamento:`, 10, yPosition);
    yPosition += 5;
    
    descLines.forEach((line, index) => {
        doc.text(line, 15, yPosition + (index * 5));
    });
    
    yPosition += descLines.length * 5 + 5;
    
    doc.text(`Clave: ${clave}`, 10, yPosition);
    doc.text(`Lote: ${lote}`, 10, yPosition + 5);
    doc.text(`Caducidad: ${formatearFecha(caducidad)}`, 10, yPosition + 10);
    doc.text(`Cantidad: ${existencia} unidades`, 10, yPosition + 15);
    
    let x = 20;
    let y = yPosition + 30;
    const qrSize = 40;
    const spacing = 10;
    const qrPerRow = 4;
    
    // Generar QR codes
    for (let i = 0; i < existencia; i++) {
        if (x + qrSize > 180) {
            x = 20;
            y += qrSize + 20;
            
            // Agregar nueva página si es necesario
            if (y > 250) {
                doc.addPage();
                y = 20;
                
                // Encabezado en nuevas páginas
                doc.setFontSize(12);
                doc.text(`Continuación - ${clave} - ${lote}`, 105, 15, { align: 'center' });
            }
        }
        
        // Generar QR
        const qrDataText = `CLAVE:${clave}|LOTE:${lote}|CAD:${caducidad}`;
        const qrCanvas = document.createElement('canvas');
        
        QRCode.toCanvas(qrCanvas, qrDataText, {
            width: qrSize,
            height: qrSize,
            margin: 1
        }, function(error) {
            if (error) console.error('Error generando QR:', error);
        });
        
        // Agregar QR al PDF
        const imgData = qrCanvas.toDataURL('image/png');
        doc.addImage(imgData, 'PNG', x, y, qrSize, qrSize);
        
        // Agregar texto debajo del QR
        doc.setFontSize(8);
        doc.text(`Clave: ${clave}`, x, y + qrSize + 2);
        doc.text(`Lote: ${lote}`, x, y + qrSize + 5);
        doc.text(`Cad: ${formatearFecha(caducidad)}`, x, y + qrSize + 8);
        
        x += qrSize + spacing;
    }
    
    // Guardar PDF
    doc.save(`QR_${clave}_${lote}.pdf`);
}

// Función para generar QR para todos los lotes en PDF
function generarQRParaTodosPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    // Título del documento
    doc.setFontSize(16);
    doc.text('Códigos QR - Inventario Completo', 105, 15, { align: 'center' });
    doc.setFontSize(10);
    doc.text(`Generado: ${new Date().toLocaleDateString()}`, 10, 25);
    
    let currentPage = 1;
    let x = 20;
    let y = 40;
    const qrSize = 40;
    const spacing = 10;
    let totalQR = 0;
    
    // Obtener todos los lotes de la tabla
    const filas = document.querySelectorAll('.medicamentos-table tbody tr');
    
    filas.forEach((fila) => {
        // OBTENER CLAVE CORRECTAMENTE - es texto en la primera celda (td)
        const primeraCelda = fila.querySelector('td:first-child');
        const clave = primeraCelda ? primeraCelda.textContent.trim() : 'N/A';
        
        const loteInput = fila.querySelector('input[name^="lote_codigo_"]');
        const lote = loteInput ? loteInput.value : 'N/A';
        const caducidad = fila.dataset.fecha;
        const existencia = parseInt(fila.dataset.existencia);
        const descripcion = fila.querySelector('.campo-descripcion').value;
        
        if (existencia > 0) {
            // Agregar encabezado de medicamento
            if (y > 200) {
                doc.addPage();
                currentPage++;
                y = 20;
            }
            
            doc.setFontSize(12);
            const titleLines = dividirTexto(descripcion, 180, doc, 12);
            titleLines.forEach((line, index) => {
                doc.text(line, 20, y + (index * 5));
            });
            
            doc.setFontSize(10);
            doc.text(`Clave: ${clave} | Lote: ${lote} | Cad: ${formatearFecha(caducidad)}`, 20, y + (titleLines.length * 5) + 5);
            y += (titleLines.length * 5) + 15;
            
            for (let i = 0; i < existencia; i++) {
                if (x + qrSize > 180) {
                    x = 20;
                    y += qrSize + 20;
                    
                    // Agregar nueva página si es necesario
                    if (y > 250) {
                        doc.addPage();
                        currentPage++;
                        y = 20;
                    }
                }
                
                // Generar QR
                const qrDataText = `CLAVE:${clave}|LOTE:${lote}|CAD:${caducidad}`;
                const qrCanvas = document.createElement('canvas');
                
                QRCode.toCanvas(qrCanvas, qrDataText, {
                    width: qrSize,
                    height: qrSize,
                    margin: 1
                }, function(error) {
                    if (error) console.error('Error generando QR:', error);
                });
                
                // Agregar QR al PDF
                const imgData = qrCanvas.toDataURL('image/png');
                doc.addImage(imgData, 'PNG', x, y, qrSize, qrSize);
                
                // Agregar texto debajo del QR
                doc.setFontSize(8);
                doc.text(`Lote: ${lote}`, x, y + qrSize + 5);
                doc.text(`Cad: ${formatearFecha(caducidad)}`, x, y + qrSize + 10);
                
                x += qrSize + spacing;
                totalQR++;
            }
            
            // Resetear posición para el próximo medicamento
            x = 20;
            y += qrSize + 30;
        }
    });
    
    // Número de página
    doc.setFontSize(8);
    for (let i = 1; i <= currentPage; i++) {
        doc.setPage(i);
        doc.text(`Página ${i} de ${currentPage}`, 190, 280, { align: 'right' });
    }
    
    // Guardar PDF
    doc.save('QR_Inventario_Completo.pdf');
}

// Función para formatear fecha (YYYY-MM-DD a DD/MM/YYYY)
function formatearFecha(fecha) {
    if (!fecha) return 'N/A';
    const partes = fecha.split('-');
    if (partes.length === 3) {
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }
    return fecha;
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarSistemaQR);
} else {
    inicializarSistemaQR();
}