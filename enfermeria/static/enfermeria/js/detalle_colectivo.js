// ===== DETALLE_COLECTIVO.JS =====

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function() {
    
    // Configurar modales
    configurarModales();
    
    // Botón de cancelar
    const btnCancelar = document.getElementById('btn-cancelar-colectivo');
    if (btnCancelar) {
        btnCancelar.addEventListener('click', confirmarCancelacion);
    }
    
    // Botón de editar
    const btnEditar = document.getElementById('btn-editar-colectivo');
    if (btnEditar) {
        btnEditar.addEventListener('click', mostrarModalEdicion);
    }
    
    // Contador de caracteres del comentario
    const comentarioTextarea = document.getElementById('observaciones-edit');
    if (comentarioTextarea) {
        comentarioTextarea.addEventListener('input', actualizarContadorCaracteres);
    }
    
    // Validación del formulario de ediciónn
    const formEditar = document.getElementById('form-editar-colectivo');
    if (formEditar) {
        formEditar.addEventListener('submit', validarFormularioEdicion);
    }
});

// ===== CONFIRMAR CANCELACIÓN =====
function confirmarCancelacion() {
    const folio = this.dataset.folio;
    const colectivoId = this.dataset.colectivoId;
    
    if (confirm(`¿Estás seguro de cancelar el colectivo ${folio}?\n\nEsta acción no se puede deshacer.`)) {
        // Crear formulario y enviarlo
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/enfermeria/colectivos/${colectivoId}/cancelar/`;
        
        // CSRF Token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
        
        document.body.appendChild(form);
        form.submit();
    }
}

// ===== MODAL DE EDICIÓN =====
function mostrarModalEdicion() {
    const modal = document.getElementById('modal-edicion');
    if (modal) {
        modal.classList.add('active');
        
        // Focus en el primer campo
        setTimeout(() => {
            const primerInput = modal.querySelector('input[type="number"]');
            if (primerInput) primerInput.focus();
        }, 100);
    }
}

function cerrarModalEdicion() {
    const modal = document.getElementById('modal-edicion');
    if (modal) {
        modal.classList.remove('active');
        
        // Resetear formulario
        const form = document.getElementById('form-editar-colectivo');
        if (form) {
            // No hacer reset completo porque perderíamos los datos
            // form.reset();
        }
    }
}

// ===== CONTADOR DE CARACTERES =====
function actualizarContadorCaracteres(e) {
    const textarea = e.target;
    const contador = textarea.parentElement.querySelector('.char-counter');
    
    if (contador) {
        const length = textarea.value.length;
        const maxLength = textarea.getAttribute('maxlength') || 500;
        contador.textContent = `${length} / ${maxLength} caracteres`;
        
        // Cambiar color si está cerca del límite
        if (length > maxLength * 0.9) {
            contador.style.color = '#DC3545';
        } else {
            contador.style.color = '#666';
        }
    }
}

// ===== VALIDAR FORMULARIO DE EDICIÓN =====
function validarFormularioEdicion(e) {
    const form = e.target;
    
    // ✅ Contar medicamentos válidos (no deshabilitados y con ID)
    const medicamentosActivos = []

    // Medicamentos existentes (no eliminados)
    const existentes = form.querySelectorAll('.medicamento-edit-item:not(.medicamento-agregado):not(.nuevo-medicamento):not(.medicamento-temporal)');
    existentes.forEach(item => {
        const medId = item.querySelector('input[name="medicamento_id[]"]');
        const cantidad = item.querySelector('input[name="cantidad[]"]');
        
        if (medId && cantidad && !medId.disabled && !cantidad.disabled && medId.value) {
            medicamentosActivos.push({
                tipo: 'existente',
                id: medId.value,
                cantidad: cantidad.value
            });
        }
    });
    
    // Medicamentos agregados (nuevos permanentes)
    const agregados = form.querySelectorAll('.medicamento-agregado');
    
    agregados.forEach(item => {
        const medId = item.querySelector('input[name="medicamento_id[]"]');
        const cantidad = item.querySelector('input[name="cantidad[]"]');
        
        if (medId && cantidad && medId.value && cantidad.value) {
            medicamentosActivos.push({
                tipo: 'agregado',
                id: medId.value,
                cantidad: cantidad.value
            });
        }
    });
    
    // Validar que haya al menos uno
    if (medicamentosActivos.length === 0) {
        e.preventDefault();
        alert('Debe haber al menos un medicamento en el colectivo.\n\nSi eliminaste todos, agrega al menos uno nuevo.');
        return false;
    }
    
    // Confirmación final
    const mensaje = `¿Estás seguro de reenviar este colectivo a farmacia?\n\n` +
                   `Total de medicamentos: ${medicamentosActivos.length}\n` +
                   `El colectivo volverá a estado PENDIENTE.`;
    
    if (!confirm(mensaje)) {
        e.preventDefault();
        return false;
    }
    
    // Mostrar indicador de carga
    const btnSubmit = form.querySelector('button[type="submit"]');
    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
    }
    
    return true;
}


// ===== CONFIGURAR MODALES =====
function configurarModales() {
    // Cerrar modal al hacer clic en el botón X
    const closeButtons = document.querySelectorAll('.modal-close');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').classList.remove('active');
        });
    });
    
    // Cerrar modal al hacer clic fuera del contenido
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    });
    
    // Cerrar modal con tecla ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            modals.forEach(modal => modal.classList.remove('active'));
        }
    });
}

// ===== IMPRIMIR COLECTIVO =====
function imprimirColectivo() {
    window.print();
}


// ===== GESTIÓN DE MEDICAMENTOS EN MODAL ===== 

let contadorNuevos = 0;

/**
 * Eliminar un medicamento existente de la lista
 */
function eliminarMedicamentoAgregado(itemId) {
    if (!confirm('¿Eliminar este medicamento?')) {
        return;
    }
    
    const item = document.getElementById(itemId);
    if (item) {
        item.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            item.remove();
            mostrarMensajeExito('Medicamento eliminado');
        }, 300);
    }
}

/**
 * Agregar un nuevo medicamento
 */
function agregarNuevoMedicamento() {
    contadorNuevos++;
    const container = document.getElementById('nuevos-medicamentos-container');
    crearNuevoMedicamentoHTML(container, contadorNuevos);
}

/**
 * Crear HTML del nuevo medicamento con autocompletado dinámico
 */
function crearNuevoMedicamentoHTML(container, id) {
    const nuevoHTML = `
        <div class="medicamento-edit-item nuevo-medicamento medicamento-temporal" id="nuevo-med-${id}">
            <div class="med-info" style="flex: 3; position: relative;">
                <label>Medicamento</label>
                <input type="text" 
                       class="input-medicamento-autocomplete" 
                       id="input-med-${id}"
                       placeholder="Escribe al menos 2 caracteres para buscar..."
                       autocomplete="off">
                <div id="suggestions-${id}" class="autocomplete-suggestions" style="display: none;"></div>
                <input type="hidden" id="med-id-temp-${id}" value="">
            </div>
            
            <div class="med-cantidad">
                <label>Cantidad</label>
                <input type="number" 
                       id="cantidad-temp-${id}"
                       value="1" 
                       min="1" max="9999" 
                       class="cantidad-input">
            </div>
            
            <button type="button" 
                    class="btn-agregar-med" 
                    id="btn-agregar-${id}"
                    onclick="agregarMedicamentoAlFormulario(${id})"
                    title="Agregar medicamento"
                    disabled>
                <i class="fas fa-plus"></i> Agregar
            </button>
            
            <button type="button" 
                    class="btn-eliminar-med" 
                    onclick="quitarNuevoMedicamento('nuevo-med-${id}')"
                    title="Cancelar"
                    style="background: #6c757d;">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', nuevoHTML);
    
    // Configurar autocompletado
    configurarAutocompletado(id);
}

/**
 * Configurar autocompletado dinámico para un input
 */
function configurarAutocompletado(id) {
    const input = document.getElementById(`input-med-${id}`);
    const hiddenId = document.getElementById(`med-id-temp-${id}`);
    const suggestions = document.getElementById(`suggestions-${id}`);
    const btnAgregar = document.getElementById(`btn-agregar-${id}`);
    
    let timeout = null;
    
    // Buscar mientras escribe
    input.addEventListener('input', function() {
        const query = this.value.trim();
        
        // Limpiar timeout anterior
        clearTimeout(timeout);
        
        // Limpiar selección si cambia el texto
        hiddenId.value = '';
        btnAgregar.disabled = true;
        btnAgregar.style.background = '#6c757d';
        
        // Ocultar sugerencias si es muy corto
        if (query.length < 2) {
            suggestions.style.display = 'none';
            suggestions.innerHTML = '';
            return;
        }
        
        // Esperar 300ms antes de buscar (debounce)
        timeout = setTimeout(() => {
            buscarMedicamentos(query, suggestions, input, hiddenId, btnAgregar);
        }, 300);
    });
    
    // Cerrar sugerencias al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !suggestions.contains(e.target)) {
            suggestions.style.display = 'none';
        }
    });
    
    // Mostrar sugerencias al hacer focus si ya tiene texto
    input.addEventListener('focus', function() {
        if (this.value.length >= 2 && suggestions.children.length > 0) {
            suggestions.style.display = 'block';
        }
    });
}

/**
 * Buscar medicamentos en el servidor
 */
async function buscarMedicamentos(query, suggestionsDiv, input, hiddenId, btnAgregar) {
    try {
        const response = await fetch(`/enfermeria/api/buscar-medicamentos/?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            mostrarSugerencias(data.results, suggestionsDiv, input, hiddenId, btnAgregar);
        } else {
            suggestionsDiv.innerHTML = '<div class="suggestion-item no-results">No se encontraron medicamentos</div>';
            suggestionsDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error al buscar medicamentos:', error);
        suggestionsDiv.innerHTML = '<div class="suggestion-item error">Error al buscar medicamentos</div>';
        suggestionsDiv.style.display = 'block';
    }
}

/**
 * Mostrar sugerencias en el dropdown
 */
function mostrarSugerencias(medicamentos, suggestionsDiv, input, hiddenId, btnAgregar) {
    suggestionsDiv.innerHTML = '';
    
    medicamentos.forEach(med => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.innerHTML = `
            <strong>${med.clave}</strong>
            <span>${med.descripcion}</span>
        `;
        
        item.addEventListener('click', function() {
            input.value = `${med.clave} - ${med.descripcion}`;
            hiddenId.value = med.id;
            suggestionsDiv.style.display = 'none';
            
            // Habilitar botón de agregar
            btnAgregar.disabled = false;
            btnAgregar.style.background = '#28a745';
            
            // Marcar como válido
            input.style.borderColor = '#28a745';
            setTimeout(() => {
                input.style.borderColor = '';
            }, 2000);
        });
        
        suggestionsDiv.appendChild(item);
    });
    
    suggestionsDiv.style.display = 'block';
}

function eliminarMedicamento(itemId) {
    if (!confirm('¿Eliminar este medicamento de la solicitud?')) {
        return;
    }
    
    const item = document.getElementById(itemId);
    if (item) {
        // Marcar visualmente como eliminado
        item.style.opacity = '0.4';
        item.style.textDecoration = 'line-through';
        item.style.pointerEvents = 'none';
        
        // Deshabilitar inputs para que no se envíen
        const inputs = item.querySelectorAll('input');
        inputs.forEach(input => input.disabled = true);
        
        // Cambiar botón
        const btnEliminar = item.querySelector('.btn-eliminar-med');
        if (btnEliminar) {
            btnEliminar.innerHTML = '<i class="fas fa-check"></i> Eliminado';
            btnEliminar.disabled = true;
            btnEliminar.style.background = '#6c757d';
        }
    }
}

function agregarMedicamentoAlFormulario(id) {
    const container = document.getElementById(`nuevo-med-${id}`);
    const medIdTemp = document.getElementById(`med-id-temp-${id}`);
    const cantidadTemp = document.getElementById(`cantidad-temp-${id}`);
    const inputText = document.getElementById(`input-med-${id}`);
    
    // Validar que haya medicamento seleccionado
    if (!medIdTemp || !medIdTemp.value) {
        alert('Debes seleccionar un medicamento de la lista');
        return;
    }
    
    // Validar cantidad
    if (!cantidadTemp || !cantidadTemp.value || cantidadTemp.value < 1) {
        alert('La cantidad debe ser mayor a 0');
        return;
    }
    
    // ✅ Agregar al contenedor
    listaPermanente.insertAdjacentHTML('beforeend', medicamentoPermanenteHTML);
    
    // ✅ Eliminar el formulario temporal
    if (container) {
        container.remove();
    }
    
    // ✅ Mostrar mensaje de éxito
    mostrarMensajeExito('Medicamento agregado correctamente');
}

function mostrarMensajeExito(texto) {
    // Eliminar mensajes anteriores
    const mensajesAnteriores = document.querySelectorAll('.alert-success-temporal');
    mensajesAnteriores.forEach(m => m.remove());
    
    const mensaje = document.createElement('div');
    mensaje.className = 'alert alert-success alert-success-temporal';
    mensaje.style.cssText = `
        padding: 12px 20px;
        margin: 10px 0;
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
        border-radius: 6px;
        display: flex;
        align-items: center;
        gap: 10px;
        animation: slideIn 0.3s ease;
    `;
    mensaje.innerHTML = `<i class="fas fa-check-circle"></i> ${texto}`;
    
    const contenedor = document.getElementById('medicamentos-agregados-lista');
    if (contenedor) {
        contenedor.insertAdjacentElement('afterend', mensaje);
        
        setTimeout(() => {
            mensaje.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => mensaje.remove(), 300);
        }, 3000);
    }
}

/**
 * Quitar un medicamento recién agregado
 */
function quitarNuevoMedicamento(itemId) {
    const item = document.getElementById(itemId);
    if (item) {
        item.remove();
    }
}



// Exportar funciones globales
window.eliminarMedicamento = eliminarMedicamento;  // ✅ Para medicamentos existentes
window.eliminarMedicamentoAgregado = eliminarMedicamentoAgregado;  // ✅ Para medicamentos nuevos
window.agregarNuevoMedicamento = agregarNuevoMedicamento;
window.quitarNuevoMedicamento = quitarNuevoMedicamento;
window.cerrarModalEdicion = cerrarModalEdicion;
window.imprimirColectivo = imprimirColectivo;
window.agregarMedicamentoAlFormulario = agregarMedicamentoAlFormulario;

