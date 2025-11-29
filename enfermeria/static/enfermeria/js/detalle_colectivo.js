// ===== DETALLE_COLECTIVO.JS =====

console.log('📄 Script de detalle de colectivo cargado');

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando vista de detalle...');
    
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
    const comentarioTextarea = document.getElementById('comentario-reenvio');
    if (comentarioTextarea) {
        comentarioTextarea.addEventListener('input', actualizarContadorCaracteres);
    }
    
    // Validación del formulario de edición
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
        if (form) form.reset();
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
        if (length >= maxLength * 0.9) {
            contador.style.color = '#DC3545';
        } else {
            contador.style.color = '#666';
        }
    }
}

// ===== VALIDAR FORMULARIO DE EDICIÓN =====
function validarFormularioEdicion(e) {
    const form = e.target;
    const comentario = form.querySelector('#comentario-reenvio').value.trim();
    
    // Validar que el comentario no esté vacío
    if (comentario.length < 10) {
        e.preventDefault();
        alert('Por favor, agrega un comentario más detallado (mínimo 10 caracteres) explicando los cambios realizados.');
        return false;
    }
    
    // Validar que al menos una cantidad haya cambiado
    let hayCambios = false;
    const inputs = form.querySelectorAll('.cantidad-input');
    inputs.forEach(input => {
        const valorActual = parseInt(input.value);
        const valorOriginal = parseInt(input.defaultValue);
        if (valorActual !== valorOriginal) {
            hayCambios = true;
        }
    });
    
    if (!hayCambios && !confirm('No has modificado ninguna cantidad. ¿Deseas reenviar el colectivo de todas formas?')) {
        e.preventDefault();
        return false;
    }
    
    // Confirmación final
    if (!confirm('¿Estás seguro de reenviar este colectivo a farmacia?\n\nEl colectivo volverá a estado PENDIENTE.')) {
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

// ===== EXPORTAR FUNCIONES GLOBALES =====
window.cerrarModalEdicion = cerrarModalEdicion;
window.imprimirColectivo = imprimirColectivo;
