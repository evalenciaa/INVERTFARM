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

/* ===== CREAR NUEVO BACKUP ===== */
function crearBackup() {
    if (!confirm('¿Deseas crear un nuevo backup?\n\nEsto incluirá:\n✓ Base de datos completa\n✓ Archivos media\n\nEl proceso puede tardar unos momentos.')) {
        return;
    }
    
    showLoading('Creando backup...');
    
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
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading();
        
        if (data.success) {
            mostrarNotificacion('✅ Backup creado exitosamente', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            mostrarNotificacion('❌ ' + (data.error || 'Error al crear backup'), 'error');
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
    link.href = `/backups/descargar/${filename}/`;
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
                      `• Sobrescribirá TODA la base de datos actual\n` +
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
    showLoading('Restaurando backup... NO cierres esta ventana');
    
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
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading();
        
        if (data.success) {
            mostrarNotificacion('✅ Backup restaurado exitosamente', 'success');
            setTimeout(() => {
                alert('La base de datos ha sido restaurada.\n\nLa página se recargará ahora.');
                window.location.href = '/principal/';
            }, 2000);
        } else {
            mostrarNotificacion('❌ ' + (data.error || 'Error al restaurar backup'), 'error');
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
    
    fetch(`/backups/eliminar/${filename}/`, {
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

/* ===== SUBIR BACKUP EXTERNO ===== */
function subirBackup(file) {
    if (!file) {
        mostrarNotificacion('❌ No se seleccionó ningún archivo', 'error');
        return;
    }
    
    // Validar extensión
    const validExtensions = ['.sql', '.sql.gz', '.tar.gz', '.tar'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));
    
    if (!isValid) {
        mostrarNotificacion('❌ Formato no válido. Solo: .sql, .sql.gz, .tar.gz', 'error');
        return;
    }
    
    // Validar tamaño (500MB máximo)
    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
        mostrarNotificacion('❌ Archivo demasiado grande. Máximo: 500MB', 'error');
        return;
    }
    
    if (!confirm(`¿Deseas subir este backup?\n\nArchivo: ${file.name}\nTamaño: ${(file.size / (1024*1024)).toFixed(2)} MB`)) {
        // Limpiar input
        document.getElementById('fileInput').value = '';
        return;
    }
    
    showLoading('Subiendo backup... Esto puede tardar unos momentos');
    
    const csrftoken = getCSRFToken();
    if (!csrftoken) {
        hideLoading();
        mostrarNotificacion('Error: No se pudo obtener el token CSRF', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('backup_file', file);
    
    fetch('/backups/subir/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: formData,
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
            mostrarNotificacion(`✅ ${data.message}`, 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            mostrarNotificacion('❌ ' + (data.error || 'Error al subir backup'), 'error');
        }
        
        // Limpiar input
        document.getElementById('fileInput').value = '';
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        mostrarNotificacion('❌ Error de conexión: ' + error.message, 'error');
        document.getElementById('fileInput').value = '';
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
});
