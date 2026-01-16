/* ===== VARIABLES GLOBALES ===== */
let usuarios = [];

/* ===== OBTENER CSRF TOKEN ===== */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCSRFToken() {
    // 1. Variable global de JavaScript (más confiable)
    if (typeof window.CSRF_TOKEN !== 'undefined' && window.CSRF_TOKEN) {
        return window.CSRF_TOKEN;
    }
    
    // 2. Meta tag
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag && metaTag.getAttribute('content')) {
        return metaTag.getAttribute('content');
    }
    
    // 3. Input hidden
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (csrfInput && csrfInput.value) {
        return csrfInput.value;
    }
    
    // 4. Cookie
    const cookieValue = getCookie('csrftoken');
    if (cookieValue) {
        return cookieValue;
    }
    
    console.error('❌ No se pudo obtener el CSRF token');
    return null;
}

/* ===== FUNCIÓN PARA ABRIR MODAL ===== */
function abrirModalNuevoUsuario() {
    const modal = document.getElementById('modalNuevoUsuario');
    modal.classList.add('active');
    modal.style.display = 'flex';
}

/* ===== FUNCIÓN PARA CERRAR MODAL ===== */
function cerrarModal() {
    const modal = document.getElementById('modalNuevoUsuario');
    modal.classList.remove('active');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

/* ===== CERRAR MODAL AL HACER CLIC FUERA ===== */
window.onclick = function(event) {
    const modal = document.getElementById('modalNuevoUsuario');
    if (event.target === modal) {
        cerrarModal();
    }
}

/* ===== FILTRAR USUARIOS ===== */
function filtrarUsuarios() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const filterGrupo = document.getElementById('filterGrupo').value.toLowerCase();
    const filterEstado = document.getElementById('filterEstado').value;
    
    const table = document.getElementById('usuariosTable');
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    
    let visibleCount = 0;
    
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const cells = row.getElementsByTagName('td');
        
        if (cells.length === 0) continue;
        
        const username = cells[0].textContent.toLowerCase();
        const fullname = cells[1].textContent.toLowerCase();
        const email = cells[2].textContent.toLowerCase();
        const grupos = row.getAttribute('data-grupos') ? row.getAttribute('data-grupos').toLowerCase() : '';
        const isActive = row.getAttribute('data-activo') === 'True';
        const isSuperuser = row.getAttribute('data-superuser') === 'True';
        
        const matchSearch = searchTerm === '' || 
                          username.includes(searchTerm) || 
                          fullname.includes(searchTerm) || 
                          email.includes(searchTerm);
        
        const matchGrupo = filterGrupo === '' || grupos.includes(filterGrupo);
        
        let matchEstado = true;
        if (filterEstado === 'activo') {
            matchEstado = isActive && !isSuperuser;
        } else if (filterEstado === 'inactivo') {
            matchEstado = !isActive;
        } else if (filterEstado === 'superuser') {
            matchEstado = isSuperuser;
        }
        
        if (matchSearch && matchGrupo && matchEstado) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    }
    
    document.getElementById('resultCount').textContent = visibleCount;
}

/* ===== LIMPIAR FILTROS ===== */
function limpiarFiltros() {
    document.getElementById('searchInput').value = '';
    document.getElementById('filterGrupo').value = '';
    document.getElementById('filterEstado').value = '';
    filtrarUsuarios();
}

/* ===== CONFIRMAR ELIMINACIÓN ===== */
function confirmarEliminar(username, userId) {
    if (confirm(`¿Estás seguro de que deseas eliminar al usuario "${username}"?\n\nEsta acción no se puede deshacer.`)) {
        eliminarUsuario(userId);
    }
}

/* ===== ELIMINAR USUARIO VÍA AJAX ===== */
function eliminarUsuario(userId) {
    const csrftoken = getCSRFToken();
    
    if (!csrftoken) {
        mostrarNotificacion('Error: No se pudo obtener el token CSRF', 'error');
        console.error('CSRF token no encontrado');
        return;
    }
    
    fetch(`/admin-usuarios/eliminar/${userId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            mostrarNotificacion('Usuario eliminado exitosamente', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            mostrarNotificacion(data.error || 'Error al eliminar usuario', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarNotificacion('Error de conexión: ' + error.message, 'error');
    });
}

/* ===== MOSTRAR NOTIFICACIONES ===== */
function mostrarNotificacion(mensaje, tipo) {
    const notif = document.createElement('div');
    notif.className = `notificacion notificacion-${tipo}`;
    notif.innerHTML = `
        <i class="fas fa-${tipo === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${mensaje}</span>
    `;
    
    document.body.appendChild(notif);
    
    if (!document.getElementById('notificacion-styles')) {
        const style = document.createElement('style');
        style.id = 'notificacion-styles';
        style.textContent = `
            .notificacion {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 25px;
                border-radius: 10px;
                box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
                display: flex;
                align-items: center;
                gap: 12px;
                font-weight: 600;
                z-index: 10000;
                animation: slideInRight 0.3s ease;
            }
            
            .notificacion-success {
                background: #d1fae5;
                color: #065f46;
            }
            
            .notificacion-error {
                background: #fee2e2;
                color: #991b1b;
            }
            
            @keyframes slideInRight {
                from {
                    opacity: 0;
                    transform: translateX(100px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    setTimeout(() => {
        notif.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => {
            notif.remove();
        }, 300);
    }, 3000);
}

/* ===== VALIDAR FORMULARIO ANTES DE ENVIAR ===== */
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('#modalNuevoUsuario form');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            const password = document.querySelector('input[name="password"]').value;
            const password2 = document.querySelector('input[name="password2"]').value;
            
            if (password !== password2) {
                e.preventDefault();
                mostrarNotificacion('Las contraseñas no coinciden', 'error');
                return false;
            }
            
            if (password.length < 4) {
                e.preventDefault();
                mostrarNotificacion('La contraseña debe tener al menos 4 caracteres', 'error');
                return false;
            }
        });
    }
});

/* ===== EFECTOS DE HOVER EN STATS ===== */
document.addEventListener('DOMContentLoaded', function() {
    const statCards = document.querySelectorAll('.stat-card');
    
    statCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
});
