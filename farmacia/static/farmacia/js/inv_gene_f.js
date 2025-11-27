document.addEventListener('DOMContentLoaded', function() {
document.addEventListener('DOMContentLoaded', function() {
    // Filtrado por medicamento - Versión mejorada
    const filtroMedicamento = document.getElementById('filtro-medicamento');
    if (filtroMedicamento) {
        filtroMedicamento.addEventListener('input', function() {
            const texto = this.value.trim().toLowerCase();
            const filas = document.querySelectorAll('#tabla-inventario-general tbody tr');
            
            // Si el campo está vacío, mostrar todas las filas
            if (texto === '') {
                filas.forEach(fila => fila.style.display = '');
                return;
            }
            
            // Filtrar por clave o descripción
            filas.forEach(fila => {
                const clave = fila.dataset.clave ? fila.dataset.clave.toLowerCase() : '';
                const descripcion = fila.dataset.descripcion ? fila.dataset.descripcion.toLowerCase() : '';
                const mostrar = clave.includes(texto) || descripcion.includes(texto);
                fila.style.display = mostrar ? '' : 'none';
            });
            
            // Opcional: Mostrar mensaje si no hay resultados
            const filasVisibles = document.querySelectorAll('#tabla-inventario-general tbody tr[style=""]');
            if (filasVisibles.length === 0) {
                mostrarMensajeSinResultados();
            } else {
                ocultarMensajeSinResultados();
            }
        });
    }

    // Botón exportar (manteniendo tu implementación actual)
    const btnExportar = document.getElementById('btn-exportar');
    if (btnExportar) {
        btnExportar.addEventListener('click', function() {
            mostrarMenuExportacion();
        });
    }
});

function mostrarMenuExportacion() {
    const menuHTML = `
        <div id="menu-exportacion" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.2); z-index: 1000;">
            <h3 style="margin-top: 0; color: #750000;">Exportar Inventario</h3>
            <button id="btn-exportar-excel" class="btn-exportar-option">
                <i class="fas fa-file-excel"></i> Exportar a Excel
            </button>
            <button id="btn-exportar-pdf" class="btn-exportar-option">
                <i class="fas fa-file-pdf"></i> Exportar a PDF
            </button>
            <button id="btn-cancelar-export" class="btn-exportar-option" style="margin-top: 10px;">
                <i class="fas fa-times"></i> Cancelar
            </button>
        </div>
        <div id="overlay-export" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                background: rgba(0,0,0,0.5); z-index: 999;"></div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', menuHTML);
    
    // Event listeners para los botones del menú
    document.getElementById('btn-exportar-excel').addEventListener('click', exportarAExcel);
    document.getElementById('btn-exportar-pdf').addEventListener('click', exportarAPDF);
    document.getElementById('btn-cancelar-export').addEventListener('click', cerrarMenuExportacion);
    document.getElementById('overlay-export').addEventListener('click', cerrarMenuExportacion);
}

function cerrarMenuExportacion() {
    const menu = document.getElementById('menu-exportacion');
    const overlay = document.getElementById('overlay-export');
    if (menu) menu.remove();
    if (overlay) overlay.remove();
}

// Funciones auxiliares para mensajes de no resultados
function mostrarMensajeSinResultados() {
    let mensaje = document.getElementById('mensaje-sin-resultados');
    if (!mensaje) {
        mensaje = document.createElement('tr');
        mensaje.id = 'mensaje-sin-resultados';
        mensaje.innerHTML = `
            <td colspan="3" style="text-align: center; padding: 20px; color: #750000;">
                No se encontraron medicamentos que coincidan con la búsqueda
            </td>
        `;
        document.querySelector('#tabla-inventario-general tbody').appendChild(mensaje);
    }
}

function ocultarMensajeSinResultados() {
    const mensaje = document.getElementById('mensaje-sin-resultados');
    if (mensaje) {
        mensaje.remove();
    }
}})

function exportarAExcel() {
    // Cargar la librería SheetJS (xlsx) dinámicamente
    const btnExcel = document.getElementById('btn-exportar-excel');
    btnExcel.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
    btnExcel.disabled = true;

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js';
    script.onload = function() {
        // Obtener los datos de la tabla
        const tabla = document.getElementById('tabla-inventario-general');
        const datos = [];
        
        // Encabezados
        const encabezados = [];
        tabla.querySelectorAll('thead th').forEach(th => {
            encabezados.push(th.textContent.trim());
        });
        datos.push(encabezados);
        
        // Filas de datos
        tabla.querySelectorAll('tbody tr').forEach(tr => {
            if (tr.style.display !== 'none') { // Solo filas visibles
                const fila = [];
                tr.querySelectorAll('td').forEach(td => {
                    fila.push(td.textContent.trim());
                });
                datos.push(fila);
            }
        });
        
        // Crear libro de Excel
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(datos);
        XLSX.utils.book_append_sheet(wb, ws, "Inventario");
        
        btnExcel.innerHTML = '<i class="fas fa-file-excel"></i> Exportar a Excel';
        btnExcel.disabled = false;

        // Exportar
        XLSX.writeFile(wb, 'inventario_general.xlsx');
        cerrarMenuExportacion();
    };
    document.head.appendChild(script);
}

function exportarAPDF() {
    // Cargar la librería jsPDF dinámicamente
    const filasVisibles = document.querySelectorAll('#tabla-inventario-general tbody tr[style=""]');
    if (filasVisibles.length === 0) {
        alert('No hay datos visibles para exportar');
        return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
    script.onload = function() {
        const scriptAutoTable = document.createElement('script');
        scriptAutoTable.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js';
        scriptAutoTable.onload = function() {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            // Título del documento
            doc.setFontSize(18);
            doc.setTextColor(117, 0, 0); // Color vino
            doc.text('Inventario General de Farmacia', 14, 15);
            doc.setFontSize(12);
            doc.setTextColor(0, 0, 0);
            doc.text(`Generado el: ${new Date().toLocaleDateString()}`, 14, 22);
            
            // Obtener datos de la tabla
            const tabla = document.getElementById('tabla-inventario-general');
            const encabezados = [];
            const datos = [];
            
            // Encabezados
            tabla.querySelectorAll('thead th').forEach(th => {
                encabezados.push({
                    header: th.textContent.trim(),
                    dataKey: th.textContent.trim().toLowerCase().replace(/\s+/g, '_')
                });
            });
            
            // Datos (solo filas visibles)
            tabla.querySelectorAll('tbody tr').forEach(tr => {
                if (tr.style.display !== 'none') {
                    const fila = {};
                    const celdas = tr.querySelectorAll('td');
                    encabezados.forEach((col, index) => {
                        fila[col.dataKey] = celdas[index].textContent.trim();
                    });
                    datos.push(fila);
                }
            });
            
            // Generar tabla en PDF
            doc.autoTable({
                head: [encabezados.map(col => col.header)],
                body: datos.map(row => encabezados.map(col => row[col.dataKey])),
                startY: 30,
                styles: {
                    cellPadding: 5,
                    fontSize: 10,
                    valign: 'middle'
                },
                headStyles: {
                    fillColor: [117, 0, 0], // Color vino
                    textColor: 255,
                    fontStyle: 'bold'
                },
                alternateRowStyles: {
                    fillColor: [240, 240, 240]
                }
            });
            
            // Guardar PDF
            doc.save('inventario_general.pdf');
            cerrarMenuExportacion();
        };
        document.head.appendChild(scriptAutoTable);
    };
    document.head.appendChild(script);
}


// En inv_gene_f.js - agregar funciones para editar CPM
function actualizarCPM(elemento) {
    const medicamentoId = elemento.getAttribute('data-medicamento-id');
    const nuevoCPM = elemento.textContent.trim();
    
    // Validar que sea un número
    if (!/^\d+$/.test(nuevoCPM)) {
        alert('El CPM debe ser un número entero');
        elemento.textContent = elemento.dataset.valorAnterior || '0';
        return;
    }
    
    const cpmNum = parseInt(nuevoCPM);
    if (cpmNum < 0) {
        alert('El CPM no puede ser negativo');
        elemento.textContent = elemento.dataset.valorAnterior || '0';
        return;
    }
    
    // Mostrar loading
    elemento.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    // Enviar al servidor
    fetch('/editar-cpm/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            medicamento_id: medicamentoId,
            cpm: cpmNum
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            elemento.textContent = data.nuevo_cpm;
            elemento.dataset.valorAnterior = data.nuevo_cpm;
            
            // Actualizar estado de alerta visualmente
            actualizarEstadoAlerta(medicamentoId, cpmNum);
            
            // Mostrar mensaje de éxito
            mostrarMensajeTemporal('CPM actualizado correctamente', 'success');
        } else {
            alert('Error: ' + data.error);
            elemento.textContent = elemento.dataset.valorAnterior || '0';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al actualizar el CPM');
        elemento.textContent = elemento.dataset.valorAnterior || '0';
    });
}

function actualizarEstadoAlerta(medicamentoId, nuevoCPM) {
    const fila = document.querySelector(`tr[data-medicamento-id="${medicamentoId}"]`);
    if (!fila) return;
    
    const existencia = parseInt(fila.dataset.existencia);
    const porcentaje = nuevoCPM > 0 ? (existencia / nuevoCPM) * 100 : 0;
    
    // Actualizar icono de estado
    const celdaEstado = fila.querySelector('td:nth-child(5)');
    if (celdaEstado) {
        let icono, titulo;
        
        if (porcentaje <= 50) {
            icono = '🔴';
            titulo = 'Stock CRÍTICO (≤ 50% CPM)';
        } else if (porcentaje <= 100) {
            icono = '🟡';
            titulo = 'Stock BAJO (≤ 100% CPM)';
        } else {
            icono = '✅';
            titulo = 'Stock SUFICIENTE';
        }
        
        celdaEstado.innerHTML = `
            <span class="alerta-icono" title="${titulo}">${icono}</span>
            <br>
            <small>${Math.round(porcentaje)}%</small>
        `;
    }
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function mostrarMensajeTemporal(mensaje, tipo = 'info') {
    const div = document.createElement('div');
    div.className = `mensaje-flash mensaje-${tipo}`;
    div.textContent = mensaje;
    div.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px;
        border-radius: 5px;
        color: white;
        z-index: 10000;
        font-weight: bold;
    `;
    
    if (tipo === 'success') {
        div.style.background = '#4CAF50';
    } else if (tipo === 'error') {
        div.style.background = '#F44336';
    } else {
        div.style.background = '#2196F3';
    }
    
    document.body.appendChild(div);
    
    setTimeout(() => {
        div.remove();
    }, 3000);
}

// Agregar event listeners para los botones de edición
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.btn-editar-cpm').forEach(btn => {
        btn.addEventListener('click', function() {
            const medicamentoId = this.getAttribute('data-medicamento-id');
            const celdaCPM = document.querySelector(`.cpm-editable[data-medicamento-id="${medicamentoId}"]`);
            if (celdaCPM) {
                celdaCPM.focus();
                // Seleccionar todo el texto para facilitar la edición
                const range = document.createRange();
                range.selectNodeContents(celdaCPM);
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
            }
        });
    });
    
    // Guardar valor anterior al hacer focus
    document.querySelectorAll('.cpm-editable').forEach(elemento => {
        elemento.addEventListener('focus', function() {
            this.dataset.valorAnterior = this.textContent;
        });
    });
});


// ===== EDITAR CPM =====
function editarMedicamento(medicamentoId, clave, descripcion, cpmActual) {
    document.getElementById('edit-medicamento-id').value = medicamentoId;
    document.getElementById('edit-medicamento-nombre').textContent = `${clave} - ${descripcion}`;
    document.getElementById('edit-cpm-input').value = cpmActual;
    
    document.getElementById('modal-overlay-editar').style.display = 'block';
    document.getElementById('modal-editar-cpm').style.display = 'flex';
}

function cerrarModalEditarCPM() {
    document.getElementById('modal-overlay-editar').style.display = 'none';
    document.getElementById('modal-editar-cpm').style.display = 'none';
}

function guardarCPM() {
    const medicamentoId = document.getElementById('edit-medicamento-id').value;
    const cpmValor = document.getElementById('edit-cpm-input').value;
    
    if (!cpmValor || cpmValor < 0) {
        alert('Por favor ingrese un valor válido para el CPM');
        return;
    }
    
    // Hacer petición AJAX para guardar
    fetch('/actualizar_cpm/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            medicamento_id: medicamentoId,
            cpm: cpmValor
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('CPM actualizado correctamente');
            cerrarModalEditarCPM();
            location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al actualizar el CPM');
    });
}

// ===== ELIMINAR MEDICAMENTO =====
function confirmarEliminacionMedicamento(medicamentoId, descripcion) {
    document.getElementById('eliminar-medicamento-id').value = medicamentoId;
    document.getElementById('eliminar-medicamento-nombre').textContent = descripcion;
    
    document.getElementById('modal-overlay-eliminar').style.display = 'block';
    document.getElementById('modal-eliminar').style.display = 'flex';
}

function cerrarModalEliminar() {
    document.getElementById('modal-overlay-eliminar').style.display = 'none';
    document.getElementById('modal-eliminar').style.display = 'none';
}

function eliminarMedicamento() {
    const medicamentoId = document.getElementById('eliminar-medicamento-id').value;
    
    fetch('/eliminar_medicamento/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            medicamento_id: medicamentoId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Medicamento eliminado correctamente');
            cerrarModalEliminar();
            location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al eliminar el medicamento');
    });
}

// Función auxiliar para obtener CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ===== EXPORTAR INVENTARIO GENERAL =====

function exportarInventarioGeneral() {
    // Crear un dropdown con opciones
    const exportOptions = `
        <div class="export-menu">
            <button class="export-option" onclick="exportarExcelGeneral()">
                <i class="fas fa-file-excel"></i> Exportar a Excel
            </button>
            <button class="export-option" onclick="exportarPdfGeneral()">
                <i class="fas fa-file-pdf"></i> Exportar a PDF
            </button>
        </div>
    `;
    
    // O simplemente hacer ambas descargas con un menú
    const menu = document.createElement('div');
    menu.className = 'export-dropdown';
    menu.innerHTML = exportOptions;
    menu.style.position = 'fixed';
    menu.style.top = '100px';
    menu.style.right = '20px';
    menu.style.zIndex = '1000';
    menu.style.backgroundColor = 'white';
    menu.style.border = '1px solid #ddd';
    menu.style.borderRadius = '8px';
    menu.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
    menu.style.minWidth = '200px';
    
    document.body.appendChild(menu);
    
    // Remover menú al hacer clic fuera
    setTimeout(() => {
        document.addEventListener('click', function removeMenu(e) {
            if (!menu.contains(e.target) && e.target.className !== 'btn-success') {
                menu.remove();
                document.removeEventListener('click', removeMenu);
            }
        });
    }, 100);
}

function exportarExcelGeneral() {
    window.location.href = '/exportar_inventario_general_excel/';
}

function exportarPdfGeneral() {
    window.location.href = '/exportar_inventario_general_pdf/';
}