// ===== COLECTIVOS_FARMACIA.JS =====

console.log('🏥 Script de colectivos farmacia cargado');


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

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando gestión de colectivos en farmacia...');
    
    // Configurar checkboxes de disponibilidad
    configurarCheckboxDisponibilidad();
    
    // Validar cantidades al completar
    configurarValidacionCantidades();
    
    // Filtros rápidos
    configurarFiltrosRapidos();
    
    // Auto-refresh para colectivos pendientes
    const pendientes = document.querySelector('.farmacia-stat-number');
    if (pendientes && parseInt(pendientes.textContent) > 0) {
        iniciarAutoRefreshFarmacia(60); // Cada 60 segundos
    }
});

// ===== CHECKBOXES DE DISPONIBILIDAD =====
function configurarCheckboxDisponibilidad() {
    const checkboxes = document.querySelectorAll('.checkbox-disponibilidad input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        // Estado inicial
        const comentarioInput = checkbox.closest('.medicamento-row').querySelector('.input-comentario');
        
        checkbox.addEventListener('change', function() {
            if (!this.checked) {
                // Si no está disponible, enfocar el comentario
                comentarioInput.focus();
                comentarioInput.placeholder = 'Explica por qué no está disponible...';
            } else {
                comentarioInput.placeholder = 'Comentarios adicionales (opcional)';
            }
        });
    });
}

// ===== VALIDACIÓN DE CANTIDADES =====
function configurarValidacionCantidades() {
    const form = document.getElementById('form-completar');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        const inputs = form.querySelectorAll('.cantidad-surtir-input');
        let valido = true;
        
        inputs.forEach(input => {
            const cantidad = parseInt(input.value);
            const max = parseInt(input.getAttribute('max'));
            const stockDisponible = parseInt(input.dataset.stock);
            
            if (cantidad > stockDisponible) {
                e.preventDefault();
                valido = false;
                alert(`Stock insuficiente para ${input.dataset.medicamento}.\nDisponible: ${stockDisponible}, Solicitado: ${cantidad}`);
                input.focus();
                return;
            }
            
            if (cantidad <= 0) {
                e.preventDefault();
                valido = false;
                alert('Las cantidades deben ser mayores a 0');
                input.focus();
                return;
            }
        });
        
        if (valido) {
            // Confirmar antes de enviar
            const confirmacion = confirm('¿Confirmar el surtido de este colectivo?\n\nEsta acción descontará el stock del inventario.');
            if (!confirmacion) {
                e.preventDefault();
            }
        }
    });
}

// ===== FILTROS RÁPIDOS =====
function configurarFiltrosRapidos() {
    const botones = document.querySelectorAll('.filtro-rapido button');
    
    botones.forEach(boton => {
        boton.addEventListener('click', function() {
            // Remover clase active de todos
            botones.forEach(b => b.classList.remove('active'));
            
            // Agregar clase active al seleccionado
            this.classList.add('active');
            
            // Aplicar filtro
            const filtro = this.dataset.filtro;
            filtrarColectivosPorEstado(filtro);
        });
    });
}

function filtrarColectivosPorEstado(estado) {
    const cards = document.querySelectorAll('.colectivo-card');
    
    cards.forEach(card => {
        if (estado === 'todos') {
            card.style.display = 'block';
        } else {
            const estadoCard = card.querySelector('.estado-badge').textContent.trim().toUpperCase();
            if (estadoCard.includes(estado.toUpperCase())) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        }
    });
}

// ===== AUTO-REFRESH PARA FARMACIA =====
let autoRefreshFarmaciaInterval;

function iniciarAutoRefreshFarmacia(segundos) {
    console.log(`🔄 Auto-refresh farmacia activado cada ${segundos} segundos`);
    
    autoRefreshFarmaciaInterval = setInterval(() => {
        // Solo refrescar si hay pendientes o en revisión
        const pendientes = document.querySelector('.farmacia-stat-number');
        if (pendientes && parseInt(pendientes.textContent) > 0) {
            console.log('🔄 Actualizando lista de colectivos...');
            location.reload();
        }
    }, segundos * 1000);
}

function detenerAutoRefreshFarmacia() {
    if (autoRefreshFarmaciaInterval) {
        clearInterval(autoRefreshFarmaciaInterval);
        console.log('⏸️ Auto-refresh farmacia detenido');
    }
}

// ===== CÁLCULO AUTOMÁTICO DE STOCK =====
function calcularStockNecesario(medicamentoId) {
    const row = document.querySelector(`[data-medicamento-id="${medicamentoId}"]`);
    if (!row) return;
    
    const cantidadSolicitada = parseInt(row.dataset.cantidadSolicitada);
    const stockDisponible = parseInt(row.dataset.stockDisponible);
    
    const badge = row.querySelector('.stock-badge');
    if (stockDisponible >= cantidadSolicitada) {
        badge.className = 'stock-badge stock-suficiente';
        badge.innerHTML = '<i class="fas fa-check"></i> Stock suficiente';
    } else if (stockDisponible > 0) {
        badge.className = 'stock-badge stock-warning';
        badge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Stock parcial';
    } else {
        badge.className = 'stock-badge stock-insuficiente';
        badge.innerHTML = '<i class="fas fa-times"></i> Sin stock';
    }
}

// ===== RESALTAR MEDICAMENTOS CON PROBLEMAS =====
function resaltarMedicamentosProblema() {
    const rows = document.querySelectorAll('.medicamento-row');
    
    rows.forEach(row => {
        const checkbox = row.querySelector('input[type="checkbox"]');
        if (checkbox && !checkbox.checked) {
            row.style.borderLeft = '4px solid #DC3545';
            row.style.background = '#fff5f5';
        }
    });
}

// ===== VALIDAR RESPUESTA ANTES DE ENVIAR =====
function validarRespuesta(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    let algunoNoDisponible = false;
    let comentarioRequerido = false;
    
    checkboxes.forEach(checkbox => {
        if (!checkbox.checked) {
            algunoNoDisponible = true;
            const row = checkbox.closest('.medicamento-row');
            const comentario = row.querySelector('.input-comentario');
            
            if (!comentario.value.trim()) {
                comentarioRequerido = true;
                comentario.style.borderColor = '#DC3545';
                comentario.focus();
            }
        }
    });
    
    if (comentarioRequerido) {
        alert('Debes agregar un comentario para los medicamentos no disponibles');
        return false;
    }
    
    if (algunoNoDisponible) {
        return confirm('Algunos medicamentos no están disponibles.\n¿Enviar respuesta a enfermería?');
    }
    
    return confirm('¿Enviar respuesta a enfermería?');
}

// ===== MODAL DE CONFIRMAR SURTIDO =====
function mostrarModalSurtido() {
    const modal = document.getElementById('modal-confirmar-surtido');
    if (modal) {
        modal.classList.add('active');
        
        // Validar stock antes de mostrar
        validarStockDisponible();
    }
}

function cerrarModalSurtido() {
    const modal = document.getElementById('modal-confirmar-surtido');
    if (modal) {
        modal.classList.remove('active');
    }
}

function validarStockDisponible() {
    const inputs = document.querySelectorAll('.cantidad-surtir-input');
    let todoDisponible = true;
    
    inputs.forEach(input => {
        const solicitado = parseInt(input.dataset.solicitado);
        const disponible = parseInt(input.dataset.disponible);
        const valor = parseInt(input.value);
        
        const item = input.closest('.medicamento-surtir-item');
        
        if (valor > disponible) {
            item.classList.add('stock-insuficiente');
            todoDisponible = false;
        } else {
            item.classList.remove('stock-insuficiente');
        }
    });
    
    const btnConfirmar = document.getElementById('btn-confirmar-final');
    if (btnConfirmar) {
        btnConfirmar.disabled = !todoDisponible;
        if (!todoDisponible) {
            btnConfirmar.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Stock Insuficiente';
        } else {
            btnConfirmar.innerHTML = '<i class="fas fa-check-double"></i> Confirmar y Generar PDF';
        }
    }
}

// ===== EVENTOS =====
document.addEventListener('DOMContentLoaded', function() {
    // Botón confirmar surtido
    const btnConfirmarSurtido = document.getElementById('btn-confirmar-surtido');
    if (btnConfirmarSurtido) {
        btnConfirmarSurtido.addEventListener('click', mostrarModalSurtido);
    }
    
    // Validar en tiempo real las cantidades
    const inputsSurtir = document.querySelectorAll('.cantidad-surtir-input');
    inputsSurtir.forEach(input => {
        input.addEventListener('input', validarStockDisponible);
    });
    
    // Form submit con confirmación
    const formSurtido = document.getElementById('form-confirmar-surtido');
    if (formSurtido) {
        formSurtido.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevenir envío normal
            
            if (!confirm('¿Confirmas que deseas completar este colectivo?\n\nSe descontará del inventario.')) {
                return false;
            }
            
            // Obtener datos del formulario
            const formData = new FormData(this);
            const url = this.action;
            
            // Mostrar loading
            const btnSubmit = this.querySelector('button[type="submit"]');
            const originalHTML = btnSubmit.innerHTML;
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
            
            // Enviar formulario con AJAX
            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => {
                if (response.redirected) {
                    // Éxito - Abrir PDF en nueva ventana
                    const colectivoId = url.match(/\/(\d+)\//)[1];
                    window.open(`/colectivos-farmacia/${colectivoId}/pdf/`, '_blank');
                    
                    // Cerrar modal
                    cerrarModalSurtido();
                    
                    // Mostrar mensaje de éxito
                    alert('Colectivo completado exitosamente. El PDF se descargará automáticamente.');
                    
                    // Redirigir a lista
                    window.location.href = '/colectivos-farmacia/';
                } else {
                    throw new Error('Error al completar el colectivo');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error al completar el colectivo. Por favor, intenta nuevamente.');
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = originalHTML;
            });
            
            return false;
        });
    }
    
    // Configurar modales
    configurarModales();
});

// Exportar funciones globales
window.cerrarModalSurtido = cerrarModalSurtido;
// ===== EXPORTAR FUNCIONES GLOBALES =====
window.calcularStockNecesario = calcularStockNecesario;
window.validarRespuesta = validarRespuesta;
window.detenerAutoRefreshFarmacia = detenerAutoRefreshFarmacia;
