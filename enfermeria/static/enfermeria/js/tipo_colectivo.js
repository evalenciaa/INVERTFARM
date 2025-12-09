// ===== GESTIÓN DE TIPO DE COLECTIVO =====

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar estado
    actualizarSeccionesPorTipo();
});

/**
 * Seleccionar tipo de colectivo
 */
function seleccionarTipo(tipo) {
    // Actualizar radio buttons
    document.getElementById('tipo-paciente').checked = (tipo === 'PACIENTE');
    document.getElementById('tipo-stock').checked = (tipo === 'STOCK');
    
    // Actualizar estilos de las tarjetas
    document.getElementById('card-paciente').classList.toggle('selected', tipo === 'PACIENTE');
    document.getElementById('card-stock').classList.toggle('selected', tipo === 'STOCK');
    
    // Actualizar secciones
    actualizarSeccionesPorTipo();
}

/**
 * Actualizar visibilidad de secciones según el tipo
 */
function actualizarSeccionesPorTipo() {
    const tipoPaciente = document.getElementById('tipo-paciente').checked;
    const seccionPaciente = document.getElementById('seccion-paciente');
    const seccionStock = document.getElementById('seccion-stock');
    
    // Obtener campos
    const campoPaciente = document.getElementById('paciente_id');
    const campoNumeroCama = document.getElementById('numero_cama');
    const campoTurno = document.getElementById('turno');
    
    if (tipoPaciente) {
        // Mostrar sección de paciente
        seccionPaciente.classList.remove('seccion-oculta');
        seccionPaciente.classList.add('seccion-visible');
        seccionStock.classList.remove('seccion-visible');
        seccionStock.classList.add('seccion-oculta');
        
        // Habilitar campos de paciente
        if (campoPaciente) campoPaciente.disabled = false;
        if (campoNumeroCama) campoNumeroCama.disabled = false;
        
        // Deshabilitar campo de turno
        if (campoTurno) {
            campoTurno.disabled = true;
            campoTurno.value = '';  // Limpiar valor
        }
    } else {
        // Mostrar sección de stock
        seccionPaciente.classList.remove('seccion-visible');
        seccionPaciente.classList.add('seccion-oculta');
        seccionStock.classList.remove('seccion-oculta');
        seccionStock.classList.add('seccion-visible');
        
        // Deshabilitar campos de paciente
        if (campoPaciente) {
            campoPaciente.disabled = true;
            campoPaciente.value = '';  // Limpiar valor
        }
        if (campoNumeroCama) {
            campoNumeroCama.disabled = true;
            campoNumeroCama.value = '';  // Limpiar valor
        }
        
        // Habilitar campo de turno
        if (campoTurno) campoTurno.disabled = false;
    }
}

// Exportar función para uso global
window.seleccionarTipo = seleccionarTipo;
