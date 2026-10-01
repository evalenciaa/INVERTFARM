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
    // 1. Meta tag
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag && metaTag.getAttribute('content')) {
        return metaTag.getAttribute('content');
    }
    
    // 2. Cookie
    const cookieValue = getCookie('csrftoken');
    if (cookieValue) {
        return cookieValue;
    }
    
    console.error('❌ No se pudo obtener el CSRF token');
    return null;
}

/* ===== MOSTRAR/OCULTAR LOADING ===== */
function showLoading(text = 'Procesando...') {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    loadingText.textContent = text;
    overlay.classList.add('active');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.remove('active');
}

function mostrarProgresoTrabajo(job) {
    const porcentaje = Math.max(0, Math.min(100, Number(job.progreso || 0)));
    showLoading(`${job.etapa || 'Procesando respaldo'} (${porcentaje}%)`);
}

function monitorearTrabajo(job) {
    if (!job || !job.id) {
        hideLoading();
        mostrarNotificacion('❌ No fue posible consultar el estado del trabajo.', 'error');
        return;
    }
    let intentos = 0;
    const consultar = () => {
        const token = job.token ? `?token=${encodeURIComponent(job.token)}` : '';
        fetch(`/backups/trabajos/${encodeURIComponent(job.id)}/estado/${token}`, {
            credentials: 'same-origin',
            cache: 'no-store'
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok || !data.success) {
                throw new Error(data.error || 'No se pudo consultar el trabajo');
            }
            const actual = data.job;
            mostrarProgresoTrabajo(actual);
            if (actual.estado === 'COMPLETADO') {
                hideLoading();
                if (actual.tipo === 'RESTAURAR') {
                    alert('La base de datos y los archivos media fueron restaurados.\n\nPor seguridad, debes iniciar sesión de nuevo.');
                    window.location.href = '/login/';
                    return;
                }
                mostrarNotificacion('✅ Copia verificable creada exitosamente', 'success');
                setTimeout(() => window.location.reload(), 900);
                return;
            }
            if (actual.estado === 'ERROR') {
                hideLoading();
                mostrarNotificacion('❌ ' + (actual.error || 'El trabajo no se completó'), 'error');
                return;
            }
            intentos = 0;
            setTimeout(consultar, 1500);
        })
        .catch(error => {
            intentos += 1;
            if (intentos >= 4) {
                hideLoading();
                mostrarNotificacion('❌ No se pudo consultar el avance: ' + error.message, 'error');
                return;
            }
            setTimeout(consultar, 2000);
        });
    };
    mostrarProgresoTrabajo(job);
    consultar();
}

/* ===== CREAR NUEVO BACKUP ===== */
function crearBackup() {
    if (!confirm('¿Deseas crear un nuevo respaldo verificable?\n\nIncluirá como un solo conjunto:\n✓ Base de datos completa\n✓ Archivos media\n✓ Manifiesto de integridad firmado\n\nEl proceso puede tardar unos momentos.')) {
        return;
    }
    
    showLoading('Enviando la solicitud de respaldo...');
    
    const csrftoken = getCSRFToken();
    if (!csrftoken) {
        hideLoading();
        mostrarNotificacion('Error: No se pudo obtener el token CSRF', 'error');
        return;
    }
    
    fetch('/backups/crear/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        credentials: 'same-origin'
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(({ ok, data }) => {
        if (data.success) {
            monitorearTrabajo(data.job);
        } else {
            hideLoading();
            mostrarNotificacion('❌ ' + (data.error || 'Error al crear backup'), 'error');
            if (data.job) {
                monitorearTrabajo(data.job);
            }
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        mostrarNotificacion('❌ Error de conexión: ' + error.message, 'error');
    });
}

/* ===== DESCARGAR BACKUP ===== */
function descargarBackup(filename) {
    showLoading('Preparando descarga...');
    
    // Crear un enlace temporal para la descarga
    const link = document.createElement('a');
    link.href = `/backups/descargar/${encodeURIComponent(filename)}/`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    hideLoading();
    mostrarNotificacion('⬇️ Descargando backup...', 'success');
}

/* ===== CONFIRMAR Y RESTAURAR BACKUP ===== */
function confirmarRestaurar(filename) {
    const confirmMsg = `⚠️ ADVERTENCIA: RESTAURAR BACKUP\n\n` +
                      `Archivo: ${filename}\n\n` +
                      `Esta acción:\n` +
                      `• Sobrescribirá la base de datos y los archivos media actuales\n` +
                      `• Cerrará todas las sesiones activas\n` +
                      `• NO se puede deshacer\n` +
                      `• Puede tardar varios minutos\n\n` +
                      `¿Estás COMPLETAMENTE seguro de continuar?\n\n` +
                      `Escribe "RESTAURAR" para confirmar:`;
    
    const confirmacion = prompt(confirmMsg);
    
    if (confirmacion !== 'RESTAURAR') {
        if (confirmacion !== null) {
            mostrarNotificacion('❌ Restauración cancelada. Debes escribir "RESTAURAR" exactamente.', 'error');
        }
        return;
    }
    
    restaurarBackup(filename);
}

function restaurarBackup(filename) {
    showLoading('Enviando la restauración al proceso seguro...');
    
    const csrftoken = getCSRFToken();
    if (!csrftoken) {
        hideLoading();
        mostrarNotificacion('Error: No se pudo obtener el token CSRF', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('filename', filename);
    
    fetch('/backups/restaurar/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: formData,
        credentials: 'same-origin'
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(({ ok, data }) => {
        if (data.success) {
            monitorearTrabajo(data.job);
        } else {
            hideLoading();
            mostrarNotificacion('❌ ' + (data.error || 'Error al restaurar backup'), 'error');
            if (data.job) {
                monitorearTrabajo(data.job);
            }
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        mostrarNotificacion('❌ Error de conexión: ' + error.message, 'error');
    });
}

/* ===== CONFIRMAR Y ELIMINAR BACKUP ===== */
function confirmarEliminar(filename) {
    if (!confirm(`¿Estás seguro de que deseas eliminar este backup?\n\n${filename}\n\nEsta acción no se puede deshacer.`)) {
        return;
    }
    
    eliminarBackup(filename);
}

function eliminarBackup(filename) {
    showLoading('Eliminando backup...');
    
    const csrftoken = getCSRFToken();
    if (!csrftoken) {
        hideLoading();
        mostrarNotificacion('Error: No se pudo obtener el token CSRF', 'error');
        return;
    }
    
    fetch(`/backups/eliminar/${encodeURIComponent(filename)}/`, {
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
        hideLoading();
        
        if (data.success) {
            mostrarNotificacion('🗑️ Backup eliminado correctamente', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            mostrarNotificacion('❌ ' + (data.error || 'Error al eliminar backup'), 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        mostrarNotificacion('❌ Error de conexión: ' + error.message, 'error');
    });
}

/* ===== MOSTRAR NOTIFICACIONES ===== */
function mostrarNotificacion(mensaje, tipo) {
    const notif = document.createElement('div');
    notif.className = `notificacion notificacion-${tipo}`;
    
    const icon = tipo === 'success' ? '✅' : '❌';
    notif.innerHTML = `
        <span style="font-size: 1.2rem;">${icon}</span>
        <span>${mensaje}</span>
    `;
    
    document.body.appendChild(notif);
    
    // Agregar estilos si no existen
    if (!document.getElementById('notificacion-styles')) {
        const style = document.createElement('style');
        style.id = 'notificacion-styles';
        style.textContent = `
            .notificacion {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 25px;
                border-radius: 12px;
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
                display: flex;
                align-items: center;
                gap: 12px;
                font-weight: 600;
                z-index: 10001;
                animation: slideInRight 0.4s ease;
                min-width: 300px;
            }
            
            .notificacion-success {
                background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                color: #065f46;
                border-left: 4px solid #10b981;
            }
            
            .notificacion-error {
                background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                color: #991b1b;
                border-left: 4px solid #dc2626;
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
    
    // Auto-ocultar después de 4 segundos
    setTimeout(() => {
        notif.style.animation = 'slideInRight 0.4s ease reverse';
        setTimeout(() => {
            notif.remove();
        }, 400);
    }, 4000);
}

/* ===== EFECTOS AL CARGAR ===== */
document.addEventListener('DOMContentLoaded', function() {
    // Animación de entrada para las cards
    const cards = document.querySelectorAll('.stat-card, .content-card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.5s ease';
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 50);
        }, index * 100);
    });
    
    // Efecto hover mejorado en backup items
    const backupItems = document.querySelectorAll('.backup-item');
    backupItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(10px) scale(1.02)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0) scale(1)';
        });
    });
    
    console.log('✅ Panel de Backups cargado correctamente');
    const trabajoActivo = document.getElementById('trabajoActivoRespaldo');
    if (trabajoActivo && trabajoActivo.dataset.jobId) {
        monitorearTrabajo({ id: trabajoActivo.dataset.jobId });
    }
});
