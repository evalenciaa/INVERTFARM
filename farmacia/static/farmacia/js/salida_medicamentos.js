document.addEventListener('DOMContentLoaded', function() {
    
    // --- Almacén de datos ---
    let itemsParaSalida = [];
    let loteEscaneadoActual = null;

    // --- Selectores (Paso 1) ---
    const formPaciente = document.getElementById('form-salida-final');
    const curpInput = document.getElementById('id_paciente_curp');
    const nombreInput = document.getElementById('id_paciente_nombre');
    const nacimientoInput = document.getElementById('id_paciente_nacimiento');
    const origenSelect = document.getElementById('id_receta_origen'); 
    const folioInput = document.getElementById('id_receta_folio');
    
    // ... (Selectores de Paso 2 y 3: qrInput, tablaSalidaBody, etc. - Sin cambios) ...
    const qrInput = document.getElementById('qr_input');
    const cantidadInput = document.getElementById('cantidad_input');
    const btnAnadir = document.getElementById('btn-anadir-item');
    const msgDiv = document.getElementById('info_message');
    const fieldsetLote = document.getElementById('fieldset-lote');
    const nombreField = document.getElementById('medicamento_nombre');
    const loteField = document.getElementById('lote_numero');
    const caducidadField = document.getElementById('caducidad_lote');
    const stockField = document.getElementById('stock_actual');
    const tablaSalidaBody = document.getElementById('tabla-salida');
    const filaVacia = document.getElementById('fila-vacia');
    const hiddenInputsContainer = document.getElementById('hidden-inputs-container');
    const btnFinalizar = document.getElementById('btn-finalizar-salida');

    // --- LÓGICA PASO 1: BUSCAR PACIENTE ---

    // 1.a. Búsqueda por CURP (Como antes)
    curpInput.addEventListener('change', function() {
        const curp = this.value.toUpperCase().trim();
        if (curp.length === 18) {
            fetch(`/api/get_paciente_info/${curp}/`)
                .then(response => response.ok ? response.json() : Promise.reject('Paciente nuevo'))
                .then(data => {
                    // Encontrado por CURP: rellenamos todo
                    nombreInput.value = data.nombre_completo;
                    nacimientoInput.value = data.fecha_nacimiento;
                    nombreInput.readOnly = true;
                    nacimientoInput.readOnly = true;
                })
                .catch(error => {
                    // No encontrado: limpiamos y habilitamos
                    nombreInput.value = '';
                    nacimientoInput.value = '';
                    nombreInput.readOnly = false;
                    nacimientoInput.readOnly = false;
                    nombreInput.focus();
                });
        }
    });

    // 1.b. ¡NUEVA BÚSQUEDA POR NOMBRE!
    nombreInput.addEventListener('change', function() {
        const nombre = this.value.trim();
        // Solo buscamos si el campo de nombre tiene algo
        // y si el usuario no está ya bloqueado (readonly)
        if (nombre && !nombreInput.readOnly) {
            // Usamos 'encodeURIComponent' por si el nombre tiene espacios o eñes
            fetch(`/api/get_paciente_by_name/${encodeURIComponent(nombre)}/`)
                .then(response => response.ok ? response.json() : Promise.reject('Paciente nuevo'))
                .then(data => {
                    // Encontrado por Nombre: rellenamos CURP y Fecha
                    curpInput.value = data.curp; // Rellenará el CURP si existe, o ''
                    nacimientoInput.value = data.fecha_nacimiento;
                    // (Opcional: bloquear campos si se encuentra)
                    // curpInput.readOnly = true;
                    // nacimientoInput.readOnly = true;
                })
                .catch(error => {
                    // No encontrado por nombre: limpiamos CURP y Fecha
                    curpInput.value = '';
                    nacimientoInput.value = '';
                    // curpInput.readOnly = false;
                    // nacimientoInput.readOnly = false;
                });
        }
    });

    // --- LÓGICA LOTE (Sin cambios) ---
    qrInput.addEventListener('change', function() {
        // ... (Tu lógica de buscar lote está perfecta, no se toca) ...
        const query = this.value.trim();
        if (!query) return;
        resetCamposLote();
        msgDiv.innerHTML = '<div class="alert alert-info">Buscando lote...</div>';
        const apiUrl = `/api/buscar_lote/${query}/`;
        fetch(apiUrl)
            .then(response => response.ok ? response.json() : response.json().then(err => Promise.reject(err)))
            .then(data => {
                const yaExiste = itemsParaSalida.some(item => item.lote_id === data.id);
                if (yaExiste) {
                    throw { error: `Este lote (${data.lote_numero}) ya fue añadido a la lista.` };
                }
                msgDiv.innerHTML = `<div class="alert alert-success">Lote encontrado: ${data.medicamento_nombre}. Stock: ${data.cantidad_actual}</div>`;
                loteEscaneadoActual = data; 
                nombreField.value = data.medicamento_nombre;
                loteField.value = data.lote_numero;
                caducidadField.value = data.caducidad;
                stockField.value = `Stock: ${data.cantidad_actual}`;
                fieldsetLote.style.display = 'flex';
                cantidadInput.disabled = false;
                cantidadInput.max = data.cantidad_actual;
                cantidadInput.value = 1; 
                cantidadInput.focus();
                btnAnadir.disabled = false;
            })
            .catch(error => {
                msgDiv.innerHTML = `<div class="alert alert-danger">${error.error || 'Lote no encontrado'}</div>`;
                resetCamposLote();
            });
    });
    
    // --- LÓGICA AÑADIR A LISTA (Sin cambios) ---
    btnAnadir.addEventListener('click', function() {
        // ... (Tu lógica de añadir item está perfecta, no se toca) ...
        const cantidad = parseInt(cantidadInput.value);
        if (!loteEscaneadoActual) { alert("Error: No hay un lote escaneado."); return; }
        if (isNaN(cantidad) || cantidad <= 0) { alert("Por favor, ingrese una cantidad válida."); return; }
        if (cantidad > loteEscaneadoActual.cantidad_actual) { alert(`Error: No puede surtir ${cantidad}. El stock actual es ${loteEscaneadoActual.cantidad_actual}.`); return; }
        const item = {
            lote_id: loteEscaneadoActual.id,
            nombre: loteEscaneadoActual.medicamento_nombre,
            lote_codigo: loteEscaneadoActual.lote_numero,
            cantidad: cantidad
        };
        itemsParaSalida.push(item);
        actualizarTablaYFormulario();
        resetCamposLote();
    });

    // --- LÓGICA QUITAR DE LISTA (Sin cambios) ---
    tablaSalidaBody.addEventListener('click', function(e) {
        // ... (Tu lógica de quitar item está perfecta, no se toca) ...
        const btnQuitar = e.target.closest('.btn-quitar-item');
        if (btnQuitar) {
            const indexAQuitar = parseInt(btnQuitar.getAttribute('data-index'));
            itemsParaSalida.splice(indexAQuitar, 1);
            actualizarTablaYFormulario();
        }
    });

    // --- LÓGICA DE FINALIZAR (Sin cambios) ---
    formPaciente.addEventListener('submit', async function(e) {
        // ... (Tu lógica de submit por AJAX está perfecta, no se toca) ...
        e.preventDefault(); 
        if (itemsParaSalida.length === 0) {
            alert("Error: No hay ningún medicamento en la lista de salida.");
            return;
        }
        btnFinalizar.disabled = true;
        btnFinalizar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
        const formData = new FormData(formPaciente);
        itemsParaSalida.forEach((item, index) => {
            formData.append(`item_lote_${index}`, item.lote_id);
            formData.append(`item_cantidad_${index}`, item.cantidad);
        });
        try {
            const response = await fetch(formPaciente.action, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': formData.get('csrfmiddlewaretoken') }
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Error desconocido del servidor.');
            }
            resetFormularioCompleto(); 
            alert("¡Salida registrada exitosamente! El comprobante se está descargando.");
            window.location.href = data.pdf_url;
        } catch (error) {
            console.error('Error al finalizar la salida:', error);
            alert(`Error: ${error.message}`);
        } finally {
            if (itemsParaSalida.length > 0) {
                 btnFinalizar.disabled = false;
            }
            btnFinalizar.innerHTML = '<i class="fas fa-check-circle"></i> Finalizar y Generar PDF';
        }
    });

    // --- FUNCIONES HELPER (Sin cambios) ---
    function actualizarTablaYFormulario() {
        // ... (Esta función está perfecta, no se toca) ...
        tablaSalidaBody.innerHTML = '';
        hiddenInputsContainer.innerHTML = '';
        if (itemsParaSalida.length === 0) {
            tablaSalidaBody.appendChild(filaVacia);
            btnFinalizar.disabled = true;
            return;
        }
        itemsParaSalida.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${item.nombre}<br><small class="text-muted">Lote: ${item.lote_codigo}</small></td><td>${item.cantidad}</td><td class="text-center"><button type="button" class="btn btn-danger btn-sm btn-quitar-item" data-index="${index}" title="Quitar item"><i class="fas fa-times"></i></button></td>`;
            tablaSalidaBody.appendChild(tr);
            const inputLote = document.createElement('input');
            inputLote.type = 'hidden';
            inputLote.name = `item_lote_${index}`; 
            inputLote.value = item.lote_id;
            hiddenInputsContainer.appendChild(inputLote);
            const inputCantidad = document.createElement('input');
            inputCantidad.type = 'hidden';
            inputCantidad.name = `item_cantidad_${index}`;
            inputCantidad.value = item.cantidad;
            hiddenInputsContainer.appendChild(inputCantidad);
        });
        btnFinalizar.disabled = false;
    }
    
    function resetCamposLote() {
        // ... (Esta función está perfecta, no se toca) ...
        qrInput.value = '';
        cantidadInput.value = '';
        cantidadInput.disabled = true;
        btnAnadir.disabled = true;
        loteEscaneadoActual = null;
        fieldsetLote.style.display = 'none';
        msgDiv.innerHTML = '';
        qrInput.focus();
    }
    
    function resetFormularioCompleto() {
        // ... (Esta función está perfecta, no se toca) ...
        curpInput.value = '';
        nombreInput.value = '';
        nacimientoInput.value = '';
        folioInput.value = '';
        origenSelect.selectedIndex = 0;
        nombreInput.readOnly = false;
        resetCamposLote();
        itemsParaSalida = [];
        actualizarTablaYFormulario();
        curpInput.focus();
    }
});