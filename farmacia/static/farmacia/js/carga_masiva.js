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
            }
            
            row.innerHTML = `
                <td>${icono} ${tipo}</td>
                <td>${mensaje}</td>
            `;
            advertenciasTbody.appendChild(row);
        });
    } else {
        advertenciasList.style.display = 'none';
    }
    
    // Mostrar errores si existen
    if (resultados.errores.length > 0) {
        const errorsList = document.getElementById('errors-list');
        const errorsTbody = document.getElementById('errors-tbody');
        
        errorsList.style.display = 'block';
        errorsTbody.innerHTML = '';
        
        resultados.errores.forEach(error => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${error.fila}</td>
                <td><strong>${error.clave}</strong></td>
                <td>${error.error}</td>
            `;
            errorsTbody.appendChild(row);
        });
    }
    
    // Scroll a resultados
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Descargar plantilla
document.getElementById('descargar-plantilla').addEventListener('click', (e) => {
    e.preventDefault();
    
    // Crear plantilla CSV con precio incluido
    const plantilla = `clave,descripcion,lote,cantidad,precio,caducidad,origen,contrato,fuente_financiamiento
010.000.0142.00,Salmeterol fluticasona. Polvo. Cada dosis contiene: Xinafoato de salmeterol equi,3F6J,100,80.96,30/08/2026,ALMACEN A,IB/2261/2025,IMSS - BIENESTAR 32% 2025(U013)
010.00.2154.00,Enoxaparina. Solución inyectable cada jeringa contiene: Enoxaparina sódica 40 m,X15675A,200,682.57,30/06/2026,ALMACEN A,IB/0167/2025,IMSS - BIENESTAR 32% 2025(U013)`;
    
    const blob = new Blob([plantilla], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', 'plantilla_carga_masiva.csv');
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});