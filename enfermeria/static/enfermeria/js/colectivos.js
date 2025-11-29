// ===== COLECTIVOS.JS - JavaScript para módulo de colectivos =====

console.log('🏥 Módulo de Colectivos cargado');

// ===== PREVENIR CACHE =====
window.onpageshow = function(event) {
    if (event.persisted) {
        console.log('⚠️ Página cargada desde caché, recargando...');
        window.location.reload();
    }
};

// Detectar navegación desde caché
if (performance.navigation.type === 2) {
    window.location.replace('/enfermeria/colectivos/');
}

// ===== CONFIRMACIONES =====
function confirmarCancelacion(colectivoId, folio) {
    if (confirm(`¿Estás seguro de cancelar el colectivo ${folio}?\n\nEsta acción no se puede deshacer.`)) {
        // Enviar formulario de cancelación
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/enfermeria/colectivos/${colectivoId}/cancelar/`;
        
        // Agregar CSRF token
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

// ===== ANIMACIONES DE TARJETAS =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('📋 Inicializando colectivos...');
    
    // Animar entrada de tarjetas
    const cards = document.querySelectorAll('.colectivo-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    // Estadísticas animadas
    animarContadores();
});

// ===== ANIMAR CONTADORES DE ESTADÍSTICAS =====
function animarContadores() {
    const counters = document.querySelectorAll('.stat-number');
    
    counters.forEach(counter => {
        const target = parseInt(counter.textContent);
        const duration = 1000;
        const step = target / (duration / 16);
        let current = 0;
        
        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                counter.textContent = target;
                clearInterval(timer);
            } else {
                counter.textContent = Math.floor(current);
            }
        }, 16);
    });
}

// ===== BÚSQUEDA EN TIEMPO REAL (OPCIONAL) =====
function filtrarColectivos() {
    const busqueda = document.querySelector('input[name="q"]').value.toLowerCase();
    const cards = document.querySelectorAll('.colectivo-card');
    
    cards.forEach(card => {
        const texto = card.textContent.toLowerCase();
        if (texto.includes(busqueda)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// ===== TOOLTIP PARA ESTADOS =====
function mostrarTooltip(elemento, mensaje) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = mensaje;
    tooltip.style.cssText = `
        position: absolute;
        background: #333;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 0.8rem;
        z-index: 1000;
        white-space: nowrap;
    `;
    
    elemento.appendChild(tooltip);
    
    setTimeout(() => tooltip.remove(), 2000);
}

// ===== AUTO-REFRESH PARA COLECTIVOS PENDIENTES =====
let autoRefreshInterval;

function iniciarAutoRefresh(segundos = 30) {
    console.log(`🔄 Auto-refresh activado cada ${segundos} segundos`);
    
    autoRefreshInterval = setInterval(() => {
        // Solo refrescar si hay colectivos pendientes
        const pendientes = document.querySelector('.stat-number[style*="FFA500"]');
        if (pendientes && parseInt(pendientes.textContent) > 0) {
            console.log('🔄 Actualizando colectivos...');
            location.reload();
        }
    }, segundos * 1000);
}

function detenerAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        console.log('⏸️ Auto-refresh detenido');
    }
}

// ===== NOTIFICACIONES =====
function mostrarNotificacion(mensaje, tipo = 'info') {
    const colores = {
        'success': '#28A745',
        'error': '#DC3545',
        'warning': '#FFA500',
        'info': '#1E90FF'
    };
    
    const notif = document.createElement('div');
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colores[tipo]};
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    notif.textContent = mensaje;
    
    document.body.appendChild(notif);
    
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

// Agregar animaciones CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ===== EXPORTAR FUNCIONES GLOBALES =====
window.confirmarCancelacion = confirmarCancelacion;
window.filtrarColectivos = filtrarColectivos;
window.iniciarAutoRefresh = iniciarAutoRefresh;
window.detenerAutoRefresh = detenerAutoRefresh;
