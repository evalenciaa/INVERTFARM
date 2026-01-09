// ===== CREAR COLECTIVO - GESTIÓN DE MEDICAMENTOS =====

let medicamentosSeleccionados = [];
let medicamentoIdGlobal = null;

document.addEventListener('DOMContentLoaded', function() {
    inicializarBuscadorMedicamentos();
    inicializarBotonAgregar();
    inicializarFormulario();
    inicializarBuscadorPacientes();
    console.log('✅ Aplicación iniciada');
});

/**
 * Inicializar buscador de medicamentos
 */

function inicializarBuscadorPacientes() {
    console.log('🔧 Inicializando buscador de pacientes...');
    
    const inputPaciente = document.getElementById('paciente-input');
    const resultadosPaciente = document.getElementById('resultados-paciente');
    const hiddenInputPaciente = document.getElementById('paciente-id-hidden');
    
    console.log('📋 Elementos encontrados:');
    console.log('  - Input:', inputPaciente);
    console.log('  - Resultados:', resultadosPaciente);
    console.log('  - Hidden:', hiddenInputPaciente);
    
    if (!inputPaciente || !resultadosPaciente || !hiddenInputPaciente) {
        console.error('❌ No se encontraron los elementos necesarios');
        return;
    }
    
    let timeoutId;
    let pacienteSeleccionado = false;
    
    inputPaciente.addEventListener('input', function() {
        console.log('⌨️ Usuario escribiendo:', this.value);
        
        clearTimeout(timeoutId);
        const query = this.value.trim();
        
        if (pacienteSeleccionado) {
            hiddenInputPaciente.value = '';
            pacienteSeleccionado = false;
        }
        
        if (query.length < 3) {
            resultadosPaciente.innerHTML = '';
            resultadosPaciente.style.display = 'none';
            return;
        }
        
        timeoutId = setTimeout(() => {
            console.log('🔍 Buscando pacientes:', query);
            
            // ← CAMBIAR ESTA URL
            fetch(`/enfermeria/api/buscar-pacientes-autocomplete/?q=${encodeURIComponent(query)}`)
                .then(response => {
                    console.log('📡 Respuesta recibida:', response);
                    return response.json();
                })
                .then(data => {
                    console.log('📦 Datos parseados:', data);
                    mostrarResultadosPacientes(data.results);
                })
                .catch(error => {
                    console.error('❌ Error:', error);
                    resultadosPaciente.innerHTML = '<div class="autocomplete-error">Error al buscar pacientes</div>';
                    resultadosPaciente.style.display = 'block';
                });
        }, 300);
    });
    
    document.addEventListener('click', function(e) {
        if (!inputPaciente.contains(e.target) && !resultadosPaciente.contains(e.target)) {
            resultadosPaciente.style.display = 'none';
        }
    });
    
    function mostrarResultadosPacientes(pacientes) {
        console.log('📊 Mostrando resultados:', pacientes);
        
        if (pacientes.length === 0) {
            resultadosPaciente.innerHTML = `
                <div class="autocomplete-no-results">
                    <i class="fas fa-info-circle"></i> 
                    No se encontró el paciente. 
                    <strong>Escribe el nombre completo para crearlo automáticamente.</strong>
                </div>
            `;
            resultadosPaciente.style.display = 'block';
            return;
        }
        
        const html = pacientes.map(paciente => {
            console.log('  - Paciente:', paciente);
            return `
                <div class="autocomplete-item" data-id="${paciente.id}" data-nombre="${paciente.nombre_completo}">
                    <div class="paciente-info">
                        <strong>${paciente.nombre_completo}</strong>
                        ${paciente.curp ? `<br><small>CURP: ${paciente.curp}</small>` : ''}
                        ${paciente.fecha_nacimiento ? `<br><small>Nacimiento: ${paciente.fecha_nacimiento}</small>` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        resultadosPaciente.innerHTML = html;
        resultadosPaciente.style.display = 'block';
        
        resultadosPaciente.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                const nombre = this.getAttribute('data-nombre');
                
                console.log('👆 Paciente seleccionado:', id, nombre);
                
                inputPaciente.value = nombre;
                hiddenInputPaciente.value = id;
                pacienteSeleccionado = true;
                resultadosPaciente.style.display = 'none';
            });
        });
    }
    
    console.log('✅ Buscador de pacientes inicializado');
}


    
    /**
     * Mostrar resultados de pacientes
     */


function inicializarBuscadorMedicamentos() {
    const input = document.getElementById('medicamento-input');
    const resultados = document.getElementById('resultados-medicamento');
    
    if (!input || !resultados) return;
    
    let timeoutId;
    
    input.addEventListener('input', function() {
        clearTimeout(timeoutId);
        const query = this.value.trim();
        
        if (query.length < 2) {
            resultados.innerHTML = '';
            resultados.style.display = 'none';
            return;
        }
        
        timeoutId = setTimeout(() => {
            fetch(`/enfermeria/api/buscar-medicamentos/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    mostrarResultadosMedicamentos(data.results);
                })
                .catch(error => {
                    console.error('Error:', error);
                    resultados.innerHTML = '<div class="autocomplete-item error">Error al buscar medicamentos</div>';
                });
        }, 300);
    });
    
    // Cerrar resultados al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !resultados.contains(e.target)) {
            resultados.style.display = 'none';
        }
    });
}

/**
 * Mostrar resultados de búsqueda de medicamentos
 */
function mostrarResultadosMedicamentos(results) {
    const resultados = document.getElementById('resultados-medicamento');
    
    if (!results || results.length === 0) {
        resultados.innerHTML = '<div class="autocomplete-item">No se encontraron medicamentos</div>';
        resultados.style.display = 'block';
        return;
    }
    
    resultados.innerHTML = results.map(med => `
        <div class="autocomplete-item" data-id="${med.id}" data-text="${med.text}">
            <strong>${med.clave}</strong><br>
            <small>${med.descripcion}</small>
        </div>
    `).join('');
    
    resultados.style.display = 'block';
    
    // Agregar eventos a los items
    resultados.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('click', function() {
            seleccionarMedicamento(this.dataset.id, this.dataset.text);
        });
    });
}

/**
 * Seleccionar medicamento
 */
function seleccionarMedicamento(id, text) {
    medicamentoIdGlobal = id;
    document.getElementById('medicamento-input').value = text;
    document.getElementById('resultados-medicamento').style.display = 'none';
    document.getElementById('cantidad-input').focus();
}

/**
 * Inicializar botón agregar medicamento
 */
function inicializarBotonAgregar() {
    const btnAgregar = document.getElementById('btn-agregar-medicamento');
    const cantidadInput = document.getElementById('cantidad-input');
    
    if (!btnAgregar) return;
    
    btnAgregar.addEventListener('click', agregarMedicamento);
    
    // Agregar con Enter en el campo de cantidad
    if (cantidadInput) {
        cantidadInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                agregarMedicamento();
            }
        });
    }
}

/**
 * Agregar medicamento a la tabla
 */
function agregarMedicamento() {
    const medicamentoText = document.getElementById('medicamento-input').value.trim();
    const cantidad = parseInt(document.getElementById('cantidad-input').value);
    
    // Validaciones
    if (!medicamentoIdGlobal || !medicamentoText) {
        alert('Selecciona un medicamento de la lista');
        return;
    }
    
    if (!cantidad || cantidad <= 0) {
        alert('Ingresa una cantidad válida');
        return;
    }
    
    // Verificar si ya existe
    const existe = medicamentosSeleccionados.find(m => m.id === medicamentoIdGlobal);
    if (existe) {
        alert('Este medicamento ya fue agregado');
        return;
    }
    
    // Agregar a la lista
    medicamentosSeleccionados.push({
        id: medicamentoIdGlobal,
        text: medicamentoText,
        cantidad: cantidad
    });
    
    // Actualizar tabla
    actualizarTablaMedicamentos();
    
    // Limpiar campos
    document.getElementById('medicamento-input').value = '';
    document.getElementById('cantidad-input').value = '';
    medicamentoIdGlobal = null;
    document.getElementById('medicamento-input').focus();
}

/**
 * Actualizar tabla de medicamentos
 */
function actualizarTablaMedicamentos() {
    const tbody = document.getElementById('medicamentos-tbody');
    const contador = document.getElementById('contador-medicamentos');
    
    if (medicamentosSeleccionados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: #999;">
                    No hay medicamentos agregados
                </td>
            </tr>
        `;
        contador.textContent = '0 medicamento(s) agregado(s)';
        return;
    }
    
    tbody.innerHTML = medicamentosSeleccionados.map((med, index) => `
        <tr>
            <td>${index + 1}</td>
            <td>${med.text}</td>
            <td style="text-align: center;">${med.cantidad}</td>
            <td style="text-align: center;">
                <button type="button" class="btn-eliminar" onclick="eliminarMedicamento(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
    
    contador.textContent = `${medicamentosSeleccionados.length} medicamento(s) agregado(s)`;
}

/**
 * Eliminar medicamento
 */
function eliminarMedicamento(index) {
    if (confirm('¿Eliminar este medicamento?')) {
        medicamentosSeleccionados.splice(index, 1);
        actualizarTablaMedicamentos();
    }
}

/**
 * Inicializar validación del formulario
 */
function inicializarFormulario() {
    const form = document.getElementById('form-colectivo');
    
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // ✅ Validar según el tipo de colectivo
        const tipo = document.querySelector('input[name="tipo_colectivo"]:checked').value;
        
        if (tipo === 'PACIENTE') {
            // Validar campos de paciente (usando los nuevos IDs)
            const pacienteInput = document.getElementById('paciente-input');  // ← Cambio
            const pacienteHidden = document.getElementById('paciente-id-hidden');  // ← Cambio
            const numeroCama = document.getElementById('numero_cama');
            
            if (!pacienteInput || !pacienteInput.value.trim()) {
                alert('⚠️ Por favor ingrese el nombre del paciente');
                if (pacienteInput) pacienteInput.focus();
                return;
            }
            
            if (!numeroCama || !numeroCama.value) {
                alert('⚠️ Ingresa el número de cama');
                if (numeroCama) numeroCama.focus();
                return;
            }
        } else if (tipo === 'STOCK') {
            // Validar campos de stock
            const turno = document.getElementById('turno');
            
            if (!turno || !turno.value) {
                alert('⚠️ Selecciona el turno solicitante');
                if (turno) turno.focus();
                return;
            }
        }
        
        // Validar servicio (común para ambos tipos)
        const servicio = document.getElementById('servicio');
        if (!servicio || !servicio.value) {
            alert('⚠️ Selecciona el servicio');
            if (servicio) servicio.focus();
            return;
        }
        
        // Validar medicamentos
        if (medicamentosSeleccionados.length === 0) {
            alert('⚠️ Agrega al menos un medicamento');
            return;
        }
        
        // ✅ Agregar medicamentos como campos ocultos
        medicamentosSeleccionados.forEach(med => {
            const inputId = document.createElement('input');
            inputId.type = 'hidden';
            inputId.name = 'medicamento_id[]';
            inputId.value = med.id;
            form.appendChild(inputId);
            
            const inputCant = document.createElement('input');
            inputCant.type = 'hidden';
            inputCant.name = 'cantidad[]';
            inputCant.value = med.cantidad;
            form.appendChild(inputCant);
        });
        
        // ✅ Deshabilitar campos no necesarios según el tipo
        if (tipo === 'STOCK') {
            const pacienteInput = document.getElementById('paciente-input');  // ← Cambio
            const pacienteHidden = document.getElementById('paciente-id-hidden');  // ← Cambio
            const numeroCama = document.getElementById('numero_cama');
            
            if (pacienteInput) pacienteInput.disabled = true;
            if (pacienteHidden) pacienteHidden.disabled = true;
            if (numeroCama) numeroCama.disabled = true;
        } else if (tipo === 'PACIENTE') {
            const turno = document.getElementById('turno');
            if (turno) turno.disabled = true;
        }
        
        // Enviar formulario
        console.log('✅ Formulario validado, enviando...');  // ← DEBUG
        form.submit();
    });
}


// Exportar funciones globales
window.eliminarMedicamento = eliminarMedicamento;
