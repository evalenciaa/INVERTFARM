// Formulario de registro de medicamento

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('form-medicamento');
    const claveInput = document.getElementById('id_clave');
    const descripcionInput = document.getElementById('id_descripcion');
    
    // Convertir clave a mayúsculas automáticamente
    if (claveInput) {
        claveInput.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    }
    
    // Validación en tiempo real
    if (form) {
        form.addEventListener('submit', function(e) {
            let errores = [];
            
            // Validar clave
            const clave = claveInput.value.trim();
            if (!clave) {
                errores.push('La clave del medicamento es obligatoria.');
            } else if (clave.length < 3) {
                errores.push('La clave debe tener al menos 3 caracteres.');
            }
            
            // Validar descripción
            const descripcion = descripcionInput.value.trim();
            if (!descripcion) {
                errores.push('La descripción es obligatoria.');
            } else if (descripcion.length < 5) {
                errores.push('La descripción debe tener al menos 5 caracteres.');
            }
            
            // Si hay errores, mostrarlos
            if (errores.length > 0) {
                e.preventDefault();
                mostrarErrores(errores);
                return false;
            }
            
            // Mostrar loading en el botón
            const btnSubmit = form.querySelector('button[type="submit"]');
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registrando...';
        });
    }
});

function limpiarFormulario() {
    const form = document.getElementById('form-medicamento');
    if (form) {
        form.reset();
        
        // Remover mensajes de error
        const errorMessages = document.querySelectorAll('.error-message');
        errorMessages.forEach(msg => msg.remove());
        
        // Focus en el primer campo
        document.getElementById('id_clave').focus();
    }
}

function mostrarErrores(errores) {
    // Remover alertas previas
    const alertasAnteriores = document.querySelectorAll('.alert-danger');
    alertasAnteriores.forEach(alerta => alerta.remove());
    
    // Crear nueva alerta
    const alertaDiv = document.createElement('div');
    alertaDiv.className = 'alert alert-danger';
    alertaDiv.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <ul style="margin: 10px 0 0 0; padding-left: 20px;">
            ${errores.map(error => `<li>${error}</li>`).join('')}
        </ul>
    `;
    
    // Insertar después del header
    const formHeader = document.querySelector('.form-header');
    formHeader.insertAdjacentElement('afterend', alertaDiv);
    
    // Scroll hacia arriba para ver el error
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
