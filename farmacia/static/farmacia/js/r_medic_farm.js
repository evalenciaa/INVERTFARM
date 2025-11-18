// Hay un error de sintaxis - falta cerrar llave del primer event listener
document.addEventListener('DOMContentLoaded', function() {
    const formulario = document.querySelector('.formulario-medicamento');
    
    if (formulario) {
        formulario.addEventListener('submit', function(e) {
            const clave = document.getElementById('id_clave').value;  // Cambiado a 'id_clave'
            const descripcion = document.getElementById('id_descripcion').value;  // Cambiado a 'id_descripcion'
            
            if (clave.length < 3) {
                alert('La clave debe tener al menos 3 caracteres');
                e.preventDefault();
            }
            
            if (descripcion.length < 5) {
                alert('La descripción debe ser más detallada');
                e.preventDefault();
            }
        });
    }
});  // Esta llave estaba faltando

document.addEventListener('DOMContentLoaded', function() {
    const codigoBarras = document.getElementById('id_codigo_barras');
    if (codigoBarras) {
        codigoBarras.addEventListener('focus', function() {
            if (!this.value) {
                this.value = '750' + Math.floor(Math.random() * 1000000000).toString().padStart(9, '0');
            }
        });
    }
});