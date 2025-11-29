// ===== CREAR_COLECTIVO.JS =====

console.log('📝 Script de creación de colectivo cargado');

let medicamentosSeleccionados = [];
let contadorMedicamentos = 0;

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando formulario...');
    
    // Configurar autocompletado de pacientes
    configurarAutocompletadoPacientes();
    
    // Configurar autocompletado de medicamentos
    configurarAutocompletadoMedicamentos();
    
    // Event listener para agregar medicamento
    const btnAgregarMed = document.getElementById('btn-agregar-medicamento');
    if (btnAgregarMed) {
        btnAgregarMed.addEventListener('click', agregarMedicamento);
    }
    
    // Validación del formulario
    const form = document.getElementById('form-colectivo');
    if (form) {
        form.addEventListener('submit', validarFormulario);
    }
    
    actualizarContador();
});

// ===== AUTOCOMPLETADO DE PACIENTES =====
function configurarAutocompletadoPacientes() {
    const input = document.getElementById('paciente-input');
    const hiddenId = document.getElementById('paciente_id');
    const results = document.getElementById('resultados-paciente');
    
    if (!input) return;
    
    let timeout = null;
    
    input.addEventListener('input', function() {
        clearTimeout(timeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            results.innerHTML = '';
            results.classList.remove('active');
            return;
        }
        
        timeout = setTimeout(() => {
            fetch(`/enfermeria/api/buscar-pacientes/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    mostrarResultadosPacientes(data.results, results, input, hiddenId);
                })
                .catch(error => {
                    console.error('Error al buscar pacientes:', error);
                });
        }, 300);
    });
    
    // Cerrar resultados al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !results.contains(e.target)) {
            results.classList.remove('active');
        }
    });
}

function mostrarResultadosPacientes(resultados, contenedor, input, hiddenId) {
    if (resultados.length === 0) {
        contenedor.innerHTML = '<div class="autocomplete-item">No se encontraron pacientes</div>';
        contenedor.classList.add('active');
        return;
    }
    
    contenedor.innerHTML = resultados.map(paciente => `
        <div class="autocomplete-item" data-id="${paciente.id}" data-nombre="${paciente.nombre}">
            <strong>${paciente.nombre}</strong><br>
            <small>CURP: ${paciente.curp}</small>
        </div>
    `).join('');
    
    contenedor.classList.add('active');
    
    // Seleccionar paciente
    contenedor.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            const nombre = this.getAttribute('data-nombre');
            
            input.value = nombre;
            hiddenId.value = id;
            contenedor.classList.remove('active');
        });
    });
}

// ===== AUTOCOMPLETADO DE MEDICAMENTOS =====
function configurarAutocompletadoMedicamentos() {
    const input = document.getElementById('medicamento-input');
    const results = document.getElementById('resultados-medicamento');
    
    if (!input) return;
    
    let timeout = null;
    
    input.addEventListener('input', function() {
        clearTimeout(timeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            results.innerHTML = '';
            results.classList.remove('active');
            return;
        }
        
        timeout = setTimeout(() => {
            fetch(`/enfermeria/api/buscar-medicamentos/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    mostrarResultadosMedicamentos(data.results, results, input);
                })
                .catch(error => {
                    console.error('Error al buscar medicamentos:', error);
                });
        }, 300);
    });
    
    // Cerrar resultados al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !results.contains(e.target)) {
            results.classList.remove('active');
        }
    });
}

function mostrarResultadosMedicamentos(resultados, contenedor, input) {
    if (resultados.length === 0) {
        contenedor.innerHTML = '<div class="autocomplete-item">No se encontraron medicamentos</div>';
        contenedor.classList.add('active');
        return;
    }
    
    contenedor.innerHTML = resultados.map(med => `
        <div class="autocomplete-item" data-id="${med.id}" data-clave="${med.clave}" data-descripcion="${med.descripcion}">
            <strong>${med.clave}</strong> - ${med.descripcion}
        </div>
    `).join('');
    
    contenedor.classList.add('active');
    
    // Seleccionar medicamento
    contenedor.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            const clave = this.getAttribute('data-clave');
            const descripcion = this.getAttribute('data-descripcion');
            
            input.value = `${clave} - ${descripcion}`;
            input.dataset.medicamentoId = id;
            input.dataset.medicamentoClave = clave;
            input.dataset.medicamentoDescripcion = descripcion;
            
            contenedor.classList.remove('active');
        });
    });
}

// ===== AGREGAR MEDICAMENTO A LA TABLA =====
function agregarMedicamento() {
    const input = document.getElementById('medicamento-input');
    const cantidadInput = document.getElementById('cantidad-input');
    
    const medicamentoId = input.dataset.medicamentoId;
    const clave = input.dataset.medicamentoClave;
    const descripcion = input.dataset.medicamentoDescripcion;
    const cantidad = parseInt(cantidadInput.value);
    
    // Validaciones
    if (!medicamentoId) {
        alert('Selecciona un medicamento válido de la lista');
        return;
    }
    
    if (!cantidad || cantidad <= 0) {
        alert('Ingresa una cantidad válida');
        return;
    }
    
    // Verificar si ya está agregado
    if (medicamentosSeleccionados.some(m => m.id === medicamentoId)) {
        alert('Este medicamento ya fue agregado');
        return;
    }
    
    // Agregar a la lista
    const medicamento = {
        id: medicamentoId,
        clave: clave,
        descripcion: descripcion,
        cantidad: cantidad
    };
    
    medicamentosSeleccionados.push(medicamento);
    actualizarTablaMedicamentos();
    
    // Limpiar campos
    input.value = '';
    cantidadInput.value = '';
    delete input.dataset.medicamentoId;
    delete input.dataset.medicamentoClave;
    delete input.dataset.medicamentoDescripcion;
    
    input.focus();
}

// ===== ACTUALIZAR TABLA DE MEDICAMENTOS =====
function actualizarTablaMedicamentos() {
    const tbody = document.getElementById('medicamentos-tbody');
    
    if (medicamentosSeleccionados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #999;">No hay medicamentos agregados</td></tr>';
    } else {
        tbody.innerHTML = medicamentosSeleccionados.map((med, index) => `
            <tr>
                <td>${index + 1}</td>
                <td><strong>${med.clave}</strong><br><small>${med.descripcion}</small></td>
                <td>${med.cantidad}</td>
                <td style="text-align: center;">
                    <button type="button" class="btn-eliminar-med" onclick="eliminarMedicamento(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                    <input type="hidden" name="medicamento_id[]" value="${med.id}">
                    <input type="hidden" name="cantidad[]" value="${med.cantidad}">
                </td>
            </tr>
        `).join('');
    }
    
    actualizarContador();
}

// ===== ELIMINAR MEDICAMENTO =====
function eliminarMedicamento(index) {
    if (confirm('¿Eliminar este medicamento de la solicitud?')) {
        medicamentosSeleccionados.splice(index, 1);
        actualizarTablaMedicamentos();
    }
}

// ===== ACTUALIZAR CONTADOR =====
function actualizarContador() {
    const contador = document.getElementById('contador-medicamentos');
    if (contador) {
        contador.textContent = `${medicamentosSeleccionados.length} medicamento(s) agregado(s)`;
    }
}

// ===== VALIDAR FORMULARIO =====
function validarFormulario(e) {
    const pacienteId = document.getElementById('paciente_id').value;
    const numeroCama = document.getElementById('numero_cama').value;
    const servicio = document.getElementById('servicio').value;
    
    if (!pacienteId) {
        e.preventDefault();
        alert('Selecciona un paciente válido');
        return false;
    }
    
    if (!numeroCama.trim()) {
        e.preventDefault();
        alert('Ingresa el número de cama');
        return false;
    }
    
    if (!servicio.trim()) {
        e.preventDefault();
        alert('Ingresa el servicio');
        return false;
    }
    
    if (medicamentosSeleccionados.length === 0) {
        e.preventDefault();
        alert('Debes agregar al menos un medicamento');
        return false;
    }
    
    // Todo válido
    return true;
}

// ===== EXPORTAR FUNCIONES GLOBALES =====
window.eliminarMedicamento = eliminarMedicamento;
