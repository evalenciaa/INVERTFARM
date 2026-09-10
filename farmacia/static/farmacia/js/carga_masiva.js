// Elementos del DOM
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('archivo-excel');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const formCargaMasiva = document.getElementById('form-carga-masiva');
const loader = document.getElementById('loader');
const resultsSection = document.getElementById('results-section');

// Drag & Drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (validarArchivo(file)) {
            fileInput.files = files;
            mostrarInfoArchivo(file);
        }
    }
});

// Selección de archivo
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file && validarArchivo(file)) {
        mostrarInfoArchivo(file);
    }
});

// Validar tipo de archivo
function validarArchivo(file) {
    const extensionesValidas = ['.xlsx', '.xls'];
    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!extensionesValidas.includes(extension)) {
        alert('Por favor selecciona un archivo Excel válido (.xlsx o .xls)');
        return false;
    }
    
    // Validar tamaño (máximo 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        alert('El archivo es demasiado grande. Máximo 10MB permitido.');
        return false;
    }
    
    return true;
}

// Mostrar información del archivo
function mostrarInfoArchivo(file) {
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    fileName.textContent = file.name;
}

// Remover archivo
function removerArchivo() {
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    fileName.textContent = '';
}

// Enviar formulario
formCargaMasiva.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(formCargaMasiva);
    
    if (!fileInput.files.length) {
        alert('Por favor selecciona un archivo');
        return;
    }
    
    // Mostrar loader
    loader.style.display = 'flex';
    
    try {
        const response = await fetch('/api/carga-masiva/procesar/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        });
        
        const data = await response.json();
        
        // Ocultar loader
        loader.style.display = 'none';
        
        // Aceptar 200 (éxito) y 207 (éxito con advertencias/errores)
        if (response.ok || response.status === 207) {
            if (data.success) {
                mostrarResultados(data.resultados);
            } else {
                alert(`Error: ${data.error || 'Error desconocido'}`);
            }
        } else {
            alert(`Error: ${data.error || 'Error desconocido'}`);
        }
        
    } catch (error) {
        loader.style.display = 'none';
        alert(`Error al procesar el archivo: ${error.message}`);
        console.error('Error:', error);
    }
});


// Mostrar resultados
function mostrarResultados(resultados) {
    // Ocultar formulario
    document.querySelector('.upload-section').style.display = 'none';
    
    // Mostrar sección de resultados
    resultsSection.style.display = 'block';
    
    // Actualizar estadísticas
    document.getElementById('stat-total').textContent = resultados.total;
    document.getElementById('stat-exitosos').textContent = resultados.exitosos;
    document.getElementById('stat-actualizados').textContent = resultados.actualizados;
    document.getElementById('stat-errores').textContent = resultados.errores.length;
    

        // ========== NUEVO: Mostrar advertencias ==========
    const advertenciasList = document.getElementById('advertencias-list');
    const advertenciasTbody = document.getElementById('advertencias-tbody');
    const procesadosList = document.getElementById('procesados-list');
    const procesadosTbody = document.getElementById('procesados-tbody');
    const errorsList = document.getElementById('errors-list');
    const errorsTbody = document.getElementById('errors-tbody');
    
    if (resultados.advertencias && resultados.advertencias.length > 0) {
        advertenciasList.style.display = 'block';
        advertenciasTbody.innerHTML = '';
        
        resultados.advertencias.forEach(adv => {
            const row = document.createElement('tr');
            
            // Diferentes tipos de advertencia
            let icono = '<i class="fas fa-exclamation-triangle"></i>';
            let tipo = 'Advertencia';
            let mensaje = adv.mensaje;
            
            if (adv.tipo === 'claves_similares') {
                icono = '<i class="fas fa-copy"></i>';
                tipo = 'Claves Similares';
                mensaje = `${adv.clave1} y ${adv.clave2} son ${adv.similitud} similares. ${adv.mensaje}`;
            } else if (adv.tipo === 'lote_duplicado') {
                icono = '<i class="fas fa-layer-group"></i>';
                tipo = 'Lote Duplicado';
                mensaje = `Clave: ${adv.clave}, Lote: ${adv.lote} - ${adv.mensaje} (Filas: ${adv.filas.join(', ')})`;
            } else if (adv.tipo === 'caducidad_proxima') {
                icono = '<i class="fas fa-calendar-times"></i>';
                tipo = 'Caducidad Próxima';
                mensaje = `Fila ${adv.fila} - Clave: ${adv.clave}, Lote: ${adv.lote} - ${adv.mensaje}`;
            } else if (adv.tipo === 'codigo_atc_sin_catalogo') {
                tipo = 'ATC sin catálogo';
                mensaje = `Fila ${adv.fila} - Clave: ${adv.clave}, Código ATC: ${adv.codigo_atc} - ${adv.mensaje}`;
            }
            else if (adv.tipo === 'precio_vacio') {
                tipo = 'Precio vacío';
                mensaje = `Fila ${adv.fila} - Clave: ${adv.clave}, Lote: ${adv.lote} - ${adv.mensaje}`;
            }
            
            row.innerHTML = `
                <td>${icono} ${escapeHtml(tipo)}</td>
                <td>${escapeHtml(mensaje)}</td>
            `;
            advertenciasTbody.appendChild(row);
        });
    } else {
        advertenciasList.style.display = 'none';
    }

    if (resultados.procesados && resultados.procesados.length > 0) {
        procesadosList.style.display = 'block';
        procesadosTbody.innerHTML = '';

        resultados.procesados.forEach(item => {
            const row = document.createElement('tr');

            row.innerHTML = `
                <td>${item.fila ?? ''}</td>
                <td>${escapeHtml(item.clave ?? '')}</td>
                <td>${escapeHtml(item.descripcion ?? '')}</td>
                <td>${escapeHtml(item.lote ?? '')}</td>
                <td>${item.cantidad ?? ''}</td>
                <td>${formatearMoneda(item.precio)}</td>
                <td>${escapeHtml(item.caducidad ?? '')}</td>
                <td>
                    <span class="badge ${item.es_antibiotico ? 'badge-success' : 'badge-secondary'}">
                        ${item.es_antibiotico ? 'Sí' : 'No'}
                    </span>
                </td>
                <td>${escapeHtml(item.via_administracion ?? '')}</td>
                <td>${escapeHtml(item.codigo_atc ?? '')}</td>
                <td>${escapeHtml(item.categoria_aware ?? '')}</td>
                <td>${item.gramos_por_pieza ?? ''}</td>
                <td>${item.valor_atc ?? ''}</td>
            `;

            procesadosTbody.appendChild(row);
        });
    } else {
        procesadosList.style.display = 'none';
    }
    
    // Mostrar errores si existen
    if (resultados.errores && resultados.errores.length > 0) {
        errorsList.style.display = 'block';
        errorsTbody.innerHTML = '';

        resultados.errores.forEach(error => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${error.fila ?? ''}</td>
                <td><strong>${escapeHtml(error.clave ?? '')}</strong></td>
                <td>${escapeHtml(error.error ?? '')}</td>
            `;
            errorsTbody.appendChild(row);
        });
    } else {
        errorsList.style.display = 'none';
        errorsTbody.innerHTML = '';
    }
    
    // Scroll a resultados
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Descargar plantilla
document.getElementById('descargar-plantilla').addEventListener('click', (e) => {
    e.preventDefault();

    const datos = [
        {
            clave: '010.000.0142.00',
            descripcion: 'Salmeterol fluticasona. Polvo. Cada dosis contiene: Xinafoato de salmeterol equi',
            lote: '3F6J',
            cantidad: 100,
            precio: 80.96,
            caducidad: '2026-08-30',
            origen: 'ALMACEN A',
            contrato: 'IB/2261/2025',
            fuente_financiamiento: 'IMSS - BIENESTAR 32% 2025(U013)',
            via_administracion: '',
            codigo_atc: '',
            categoria_aware: '',
            gramos_por_pieza: '',
            valor_atc: ''
        },
        {
            clave: '010.00.2154.00',
            descripcion: 'Enoxaparina. Solución inyectable cada jeringa contiene: Enoxaparina sódica 40 m',
            lote: 'X15675A',
            cantidad: 200,
            precio: 682.57,
            caducidad: '2026-06-30',
            origen: 'ALMACEN A',
            contrato: 'IB/0167/2025',
            fuente_financiamiento: 'IMSS - BIENESTAR 32% 2025(U013)',
            via_administracion: '',
            codigo_atc: '',
            categoria_aware: '',
            gramos_por_pieza: '',
            valor_atc: ''
        },
        {
            clave: '010.000.0999.00',
            descripcion: 'Amoxicilina con ácido clavulánico. Tableta. Cada tableta contiene: Amoxicilina 875 mg',
            lote: 'AX2201',
            cantidad: 150,
            precio: 45.30,
            caducidad: '2026-12-15',
            origen: 'ALMACEN A',
            contrato: 'IB/3300/2025',
            fuente_financiamiento: 'IMSS - BIENESTAR 32% 2025(U013)',
            via_administracion: 'ORAL',
            codigo_atc: 'J01CR02',
            categoria_aware: 'Access',
            gramos_por_pieza: 0.875,
            valor_atc: 1
        }
    ];

    const ws = XLSX.utils.json_to_sheet(datos);

    const columnas = [
        { wch: 18 },
        { wch: 75 },
        { wch: 15 },
        { wch: 10 },
        { wch: 12 },
        { wch: 15 },
        { wch: 18 },
        { wch: 18 },
        { wch: 35 },
        { wch: 20 },
        { wch: 14 },
        { wch: 18 },
        { wch: 16 },
        { wch: 12 }
    ];
    ws['!cols'] = columnas;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Plantilla');

    XLSX.writeFile(wb, 'plantilla_carga_masiva.xlsx');
});

///Helpers functions

function escapeHtml(texto) {
    return String(texto ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function formatearMoneda(valor) {
    const numero = Number(valor || 0);
    return new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: 'MXN'
    }).format(numero);
}