document.addEventListener('DOMContentLoaded', function() {
    
    // ============================================
    // 1. DECLARACIÓN DE VARIABLES Y SELECTORES
    // ============================================
    
    // Almacén de datos
    let itemsParaSalida = [];
    let medicamentosFaltantes = [];
    let loteEscaneadoActual = null;

    const institucionInput = document.getElementById('institucion-input');
    const institucionHidden = document.getElementById('institucion-id-hidden');

    // Selectores - Paso 1: Datos del Paciente
    const formPaciente = document.getElementById('form-salida-final');
    const curpInput = document.getElementById('id_paciente_curp');
    const nombreInput = document.getElementById('id_paciente_nombre');
    const nacimientoInput = document.getElementById('id_paciente_nacimiento');
    const origenSelect = document.getElementById('id_receta_origen'); 
    const folioInput = document.getElementById('id_receta_folio');
    
    // Selectores - Paso 2: Escaneo de Lotes
    const qrInput = document.getElementById('qr_input');
    const cantidadInput = document.getElementById('cantidad_input');
    const btnAnadir = document.getElementById('btn-anadir-item');
    const msgDiv = document.getElementById('info_message');
    const fieldsetLote = document.getElementById('fieldset-lote');
    const nombreField = document.getElementById('medicamento_nombre');
    const loteField = document.getElementById('lote_numero');
    const caducidadField = document.getElementById('caducidad_lote');
    const stockField = document.getElementById('stock_actual');
    
    // Selectores - Paso 2.5: Medicamentos Faltantes
    const medFaltanteDesc = document.getElementById('medicamento-faltante-desc');
    const medFaltanteCant = document.getElementById('medicamento-faltante-cant');
    const medFaltanteMotivo = document.getElementById('medicamento-faltante-motivo');
    const medFaltanteMotivoOtro = document.getElementById('medicamento-faltante-motivo-otro');
    const motivoOtroContainer = document.getElementById('motivo-otro-container');
    const btnAgregarFaltante = document.getElementById('btn-agregar-faltante');
    const tablaFaltantesBody = document.getElementById('tabla-faltantes-body');
    const tablaFaltantesContainer = document.getElementById('tabla-faltantes-container');
    
    // Selectores - Paso 3: Tabla de Salida
    const tablaSalidaBody = document.getElementById('tabla-salida');
    const filaVacia = document.getElementById('fila-vacia');
    const hiddenInputsContainer = document.getElementById('hidden-inputs-container');
    const btnFinalizar = document.getElementById('btn-finalizar-salida');

    // ============================================
    // 2. PASO 1: BÚSQUEDA DE PACIENTE
    // ============================================
    
    inicializarBuscadorInstitucion();


    // Búsqueda por CURP
    curpInput.addEventListener('change', function() {
        const curp = this.value.toUpperCase().trim();
        if (curp.length === 18) {
            fetch(`/api/get_paciente_info/${curp}/`)
                .then(response => response.ok ? response.json() : Promise.reject('Paciente nuevo'))
                .then(data => {
                    nombreInput.value = data.nombre_completo;
                    nacimientoInput.value = data.fecha_nacimiento;
                    nombreInput.readOnly = true;
                    nacimientoInput.readOnly = true;
                })
                .catch(error => {
                    nombreInput.value = '';
                    nacimientoInput.value = '';
                    nombreInput.readOnly = false;
                    nacimientoInput.readOnly = false;
                    nombreInput.focus();
                });
        }
    });

    // Búsqueda por Nombre
    nombreInput.addEventListener('change', function() {
        const nombre = this.value.trim();
        if (nombre && !nombreInput.readOnly) {
            fetch(`/api/get_paciente_by_name/${encodeURIComponent(nombre)}/`)
                .then(response => response.ok ? response.json() : Promise.reject('Paciente nuevo'))
                .then(data => {
                    curpInput.value = data.curp || '';
                    nacimientoInput.value = data.fecha_nacimiento;
                    curpInput.readOnly = true;
                    nacimientoInput.readOnly = true;
                })
                .catch(error => {
                    curpInput.value = '';
                    nacimientoInput.value = '';
                    curpInput.readOnly = false;
                    nacimientoInput.readOnly = false;
                });
        }
    });

    // ============================================
    // 3. PASO 2: ESCANEO DE LOTES
    // ============================================
    
    qrInput.addEventListener('change', function() {
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
    
    // Añadir item a la lista
    btnAnadir.addEventListener('click', function() {
        const cantidad = parseInt(cantidadInput.value);
        
        if (!loteEscaneadoActual) {
            alert("Error: No hay un lote escaneado.");
            return;
        }
        
        if (isNaN(cantidad) || cantidad <= 0) {
            alert("Por favor, ingrese una cantidad válida.");
            return;
        }
        
        if (cantidad > loteEscaneadoActual.cantidad_actual) {
            alert(`Error: No puede surtir ${cantidad}. El stock actual es ${loteEscaneadoActual.cantidad_actual}.`);
            return;
        }
        
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

    // Quitar item de la lista
    tablaSalidaBody.addEventListener('click', function(e) {
        const btnQuitar = e.target.closest('.btn-quitar-item');
        if (btnQuitar) {
            const indexAQuitar = parseInt(btnQuitar.getAttribute('data-index'));
            itemsParaSalida.splice(indexAQuitar, 1);
            actualizarTablaYFormulario();
        }
    });

    // ============================================
    // 4. PASO 2.5: MEDICAMENTOS FALTANTES
    // ============================================
    
    // Mostrar/Ocultar campo "Otro motivo"
    medFaltanteMotivo.addEventListener('change', function() {
        if (this.value === 'Otro') {
            motivoOtroContainer.style.display = 'block';
            medFaltanteMotivoOtro.focus();
        } else {
            motivoOtroContainer.style.display = 'none';
            medFaltanteMotivoOtro.value = '';
        }
    });

    // Agregar medicamento faltante
    btnAgregarFaltante.addEventListener('click', function() {
        const descripcion = medFaltanteDesc.value.trim();
        const cantidad = parseInt(medFaltanteCant.value);
        let motivo = medFaltanteMotivo.value;
        
        if (!descripcion) {
            alert('Por favor ingrese la descripción del medicamento.');
            medFaltanteDesc.focus();
            return;
        }
        
        if (isNaN(cantidad) || cantidad <= 0) {
            alert('Por favor ingrese una cantidad válida.');
            medFaltanteCant.focus();
            return;
        }
        
        if (!motivo) {
            alert('Por favor seleccione un motivo.');
            medFaltanteMotivo.focus();
            return;
        }
        
        if (motivo === 'Otro') {
            const motivoOtro = medFaltanteMotivoOtro.value.trim();
            if (!motivoOtro) {
                alert('Por favor especifique el motivo.');
                medFaltanteMotivoOtro.focus();
                return;
            }
            motivo = motivoOtro;
        }
        
        const faltante = {
            descripcion: descripcion,
            cantidad: cantidad,
            motivo: motivo
        };
        
        medicamentosFaltantes.push(faltante);
        actualizarTablaFaltantes();
        limpiarCamposFaltantes();
    });

    // Quitar medicamento faltante
    tablaFaltantesBody.addEventListener('click', function(e) {
        const btnQuitar = e.target.closest('.btn-quitar-faltante');
        if (btnQuitar) {
            const index = parseInt(btnQuitar.getAttribute('data-index'));
            medicamentosFaltantes.splice(index, 1);
            actualizarTablaFaltantes();
        }
    });

    // ============================================
    // 5. PASO 3: FINALIZAR SALIDA
    // ============================================
    
    formPaciente.addEventListener('submit', async function(e) {
        e.preventDefault();

        const tipo = document.querySelector('input[name="tiposalida"]:checked').value;

        if (tipo === 'RECETA') {
            if (itemsParaSalida.length === 0 && medicamentosFaltantes.length === 0) {
                alert('Error: No hay medicamentos en la lista de salida ni medicamentos faltantes registrados.');
                return;
            }
        } else if (tipo === 'TRANSFERENCIA') {
            const institucion = document.getElementById('institucion-input').value.trim();
            if (!institucion) {
                alert('Escribe el nombre de la Institución destino.');
                return;
            }
            if (itemsParaSalida.length === 0 && medicamentosFaltantes.length === 0) {
                alert('Error: No hay medicamentos transferidos ni medicamentos no disponibles registrados.');
                return;
            }
        }

        btnFinalizar.disabled = true;
        btnFinalizar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';

        const formData = new FormData(formPaciente);
        const urlDestino = tipo === 'RECETA'
            ? formPaciente.dataset.urlReceta
            : formPaciente.dataset.urlTransferencia;

        itemsParaSalida.forEach((item, index) => {
            formData.append(`item_lote_${index}`, item.lote_id);
            formData.append(`item_cantidad_${index}`, item.cantidad);
        });

        if (tipo === 'TRANSFERENCIA') {
            formData.append('institucion_destino_nombre', document.getElementById('institucion-input').value.trim());
        }

        if (tipo === 'RECETA' || tipo === 'TRANSFERENCIA') {
            medicamentosFaltantes.forEach((faltante, index) => {
                formData.append(`faltante_desc_${index}`, faltante.descripcion);
                formData.append(`faltante_cant_${index}`, faltante.cantidad);
                formData.append(`faltante_motivo_${index}`, faltante.motivo);
            });
        }

        try {
            const response = await fetch(urlDestino, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error desconocido del servidor.');
            }

            let mensaje = tipo === 'RECETA'
                ? '✓ Salida registrada exitosamente!'
                : '✓ Transferencia registrada exitosamente!';

            if (tipo === 'RECETA') {
                if (data.estado === 'parcial') {
                    mensaje += '\n⚠ Surtido PARCIAL: Algunos medicamentos no estaban disponibles.';
                } else if (data.estado === 'no_surtida') {
                    mensaje += '\n✗ NINGÚN medicamento pudo ser surtido.';
                }
            }
            mensaje += '\n\nEl comprobante se está descargando...';

            alert(mensaje);
            resetFormularioCompleto();
            medicamentosFaltantes = [];
            actualizarTablaFaltantes();
            window.location.href = data.pdf_url;

        } catch (error) {
            console.error('Error al finalizar:', error);
            alert('Error: ' + error.message);
        } finally {
            btnFinalizar.disabled = false;
            btnFinalizar.innerHTML = '<i class="fas fa-check-circle"></i> Finalizar y Generar PDF';
        }
    });

    // ============================================
    // 6. FUNCIONES HELPER
    // ============================================
    
    function actualizarTablaYFormulario() {
        tablaSalidaBody.innerHTML = '';
        hiddenInputsContainer.innerHTML = '';
        
        if (itemsParaSalida.length === 0) {
            tablaSalidaBody.appendChild(filaVacia);
            btnFinalizar.disabled = medicamentosFaltantes.length === 0;
            return;
        }
        
        itemsParaSalida.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.nombre}<br><small class="text-muted">Lote: ${item.lote_codigo}</small></td>
                <td>${item.cantidad}</td>
                <td class="text-center">
                    <button type="button" class="btn btn-danger btn-sm btn-quitar-item" data-index="${index}" title="Quitar item">
                        <i class="fas fa-times"></i>
                    </button>
                </td>
            `;
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
    
    function actualizarTablaFaltantes() {
        tablaFaltantesBody.innerHTML = '';
        
        if (medicamentosFaltantes.length === 0) {
            tablaFaltantesContainer.style.display = 'none';
            // Si no hay items surtidos tampoco, deshabilitar botón
            if (itemsParaSalida.length === 0) {
                btnFinalizar.disabled = true;
            }
            return;
        }
        
        tablaFaltantesContainer.style.display = 'block';
        
        medicamentosFaltantes.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.descripcion}</td>
                <td class="text-center">${item.cantidad}</td>
                <td><small class="text-muted">${item.motivo}</small></td>
                <td class="text-center">
                    <button 
                        type="button" 
                        class="btn btn-danger btn-sm btn-quitar-faltante" 
                        data-index="${index}"
                        title="Quitar">
                        <i class="fas fa-times"></i>
                    </button>
                </td>
            `;
            tablaFaltantesBody.appendChild(tr);
        });
        
        // Habilitar botón finalizar si hay faltantes
        btnFinalizar.disabled = false;
    }
    
    function resetCamposLote() {
        qrInput.value = '';
        cantidadInput.value = '';
        cantidadInput.disabled = true;
        btnAnadir.disabled = true;
        loteEscaneadoActual = null;
        fieldsetLote.style.display = 'none';
        msgDiv.innerHTML = '';
        qrInput.focus();
    }
    
    function limpiarCamposFaltantes() {
        medFaltanteDesc.value = '';
        medFaltanteCant.value = '';
        medFaltanteMotivo.selectedIndex = 0;
        medFaltanteMotivoOtro.value = '';
        motivoOtroContainer.style.display = 'none';
        medFaltanteDesc.focus();
    }
    
    function resetFormularioCompleto() {
        curpInput.value = '';
        nombreInput.value = '';
        nacimientoInput.value = '';
        folioInput.value = '';
        origenSelect.selectedIndex = 0;
        nombreInput.readOnly = false;
        curpInput.readOnly = false;
        nacimientoInput.readOnly = false;
        resetCamposLote();
        itemsParaSalida = [];
        actualizarTablaYFormulario();
        curpInput.focus();
    }

function seleccionarTipoSalida(tipo) {
    document.getElementById('tipo-receta').checked = (tipo === 'RECETA');
    document.getElementById('tipo-transferencia').checked = (tipo === 'TRANSFERENCIA');

    document.getElementById('card-receta').classList.toggle('selected', tipo === 'RECETA');
    document.getElementById('card-transferencia').classList.toggle('selected', tipo === 'TRANSFERENCIA');

    document.getElementById('seccion-receta').classList.toggle('seccion-visible', tipo === 'RECETA');
    document.getElementById('seccion-receta').classList.toggle('seccion-oculta', tipo !== 'RECETA');

    document.getElementById('seccion-transferencia').classList.toggle('seccion-visible', tipo === 'TRANSFERENCIA');
    document.getElementById('seccion-transferencia').classList.toggle('seccion-oculta', tipo !== 'TRANSFERENCIA');

    const nombreInput = document.getElementById('id_paciente_nombre');
    const nacimientoInput = document.getElementById('id_paciente_nacimiento');
    const origenSelect = document.getElementById('id_receta_origen');
    const institucionInput = document.getElementById('institucion-input');
    const institucionHidden = document.getElementById('institucion-id-hidden');

    if (tipo === 'TRANSFERENCIA') {
        nombreInput.required = false;
        nombreInput.disabled = true;
        nacimientoInput.required = false;
        nacimientoInput.disabled = true;
        origenSelect.required = false;
        origenSelect.disabled = true;
        institucionInput.required = true;
        institucionInput.disabled = false;
    } else {
        nombreInput.required = true;
        nombreInput.disabled = false;
        nacimientoInput.required = true;
        nacimientoInput.disabled = false;
        origenSelect.required = true;
        origenSelect.disabled = false;
        institucionInput.required = false;
        institucionInput.disabled = true;
        institucionInput.value = '';
        institucionHidden.value = '';
    }
}

window.seleccionarTipoSalida = seleccionarTipoSalida;


function inicializarBuscadorInstitucion() {
    const inputInstitucion = document.getElementById('institucion-input');
    const resultadosInstitucion = document.getElementById('resultados-institucion');
    const hiddenInputInstitucion = document.getElementById('institucion-id-hidden');
    if (!inputInstitucion || !resultadosInstitucion || !hiddenInputInstitucion) return;

    let timeoutId;
    let institucionSeleccionada = false;

    inputInstitucion.addEventListener('input', function() {
        clearTimeout(timeoutId);
        const query = this.value.trim();
        if (institucionSeleccionada) {
            hiddenInputInstitucion.value = '';
            institucionSeleccionada = false;
        }
        if (query.length < 2) {
            resultadosInstitucion.innerHTML = '';
            resultadosInstitucion.style.display = 'none';
            return;
        }
        timeoutId = setTimeout(() => {
            fetch(`/api/buscar-instituciones-autocomplete/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => mostrarResultadosInstituciones(data.results))
                .catch(error => {
                    console.error('Error al buscar instituciones:', error);
                    resultadosInstitucion.innerHTML = '<div class="autocomplete-error">Error al buscar</div>';
                    resultadosInstitucion.style.display = 'block';
                });
        }, 300);
    });

    function mostrarResultadosInstituciones(instituciones) {
        if (instituciones.length === 0) {
            resultadosInstitucion.innerHTML = `
                <div class="autocomplete-no-results">
                    <i class="fas fa-info-circle"></i> No se encontró la institución.
                    <strong>Escribe el nombre completo para crearla automáticamente.</strong>
                </div>`;
            resultadosInstitucion.style.display = 'block';
            return;
        }
        const html = instituciones.map(inst => `
            <div class="autocomplete-item" data-id="${inst.id}" data-nombre="${inst.nombre}">
                <div class="paciente-info">
                    <strong>${inst.nombre}</strong>
                    <br><small>${inst.tipo} · ${inst.codigo}</small>
                </div>
            </div>
        `).join('');
        resultadosInstitucion.innerHTML = html;
        resultadosInstitucion.style.display = 'block';

        resultadosInstitucion.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                const nombre = this.getAttribute('data-nombre');
                inputInstitucion.value = nombre;
                hiddenInputInstitucion.value = id;
                institucionSeleccionada = true;
                resultadosInstitucion.style.display = 'none';
            });
        });
    }

    document.addEventListener('click', function(e) {
        if (!inputInstitucion.contains(e.target) && !resultadosInstitucion.contains(e.target)) {
            resultadosInstitucion.style.display = 'none';
        }
    });
}
    
}); // Fin de DOMContentLoaded