document.addEventListener('DOMContentLoaded', function() {
    
    // Función para mostrar notificaciones
function mostrarNotificacion(tipo, mensaje) {
    // Puedes implementar notificaciones bonitas con Toastr, SweetAlert, o similar
    // Esta es una implementación básica con alert()
    alert(`${tipo.toUpperCase()}: ${mensaje}`);
    
    // Opcional: Implementación con Bootstrap (si lo estás usando)
    const notification = document.createElement('div');
    notification.className = `alert alert-${tipo} fixed-top mx-auto mt-2`;
    notification.style.maxWidth = '500px';
    notification.style.zIndex = '2000';
    notification.textContent = mensaje;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}
    
    
    // Variables globales
    let entradas = [];
    const hoy = new Date().toISOString().split('T')[0];
    
    // Elementos del DOM
    const buscarMedicamento = document.getElementById('buscar-medicamento');
    const resultadosBusqueda = document.getElementById('resultados-busqueda');
    const btnBuscar = document.getElementById('btn-buscar');
    const btnAgregar = document.getElementById('btn-agregar');
    const btnGuardar = document.getElementById('btn-guardar');
    const btnPdf = document.getElementById('btn-pdf');
    const btnExcel = document.getElementById('btn-excel');
    const tipoEntrada = document.getElementById('tipo_entrada');
    const grupoInstitucion = document.getElementById('grupo-institucion');
    const grupoAlmacen = document.getElementById('grupo-almacen');
    const tablaEntradas = document.getElementById('tabla-entradas').getElementsByTagName('tbody')[0];
    const totalGeneral = document.getElementById('total-general');
    
    // Eventos
    buscarMedicamento.addEventListener('input', buscarMedicamentos);
    btnBuscar.addEventListener('click', buscarMedicamentos);
    btnAgregar.addEventListener('click', agregarEntrada);
    btnGuardar.addEventListener('click', mostrarConfirmacion);
    document.getElementById('confirm-save').addEventListener('click', guardarEntradas);
    btnPdf.addEventListener('click', generarReportePDF);
    btnExcel.addEventListener('click', generarReporteExcel);
    tipoEntrada.addEventListener('change', toggleTipoEntrada);
    
    // Inicialización
    document.getElementById('fecha').value = hoy;
    document.getElementById('caducidad').min = hoy;
    
    // Funciones
    
    function buscarMedicamentos() {
        const query = buscarMedicamento.value.trim();
        
        if (query.length < 2) {
            resultadosBusqueda.style.display = 'none';
            return;
        }
        
        fetch(`/api/medicamentos/buscar/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                resultadosBusqueda.innerHTML = '';
                
                if (data.length === 0) {
                    const item = document.createElement('div');
                    item.className = 'list-group-item';
                    item.textContent = 'No se encontraron medicamentos';
                    resultadosBusqueda.appendChild(item);
                } else {
                    data.forEach(medicamento => {
                        const item = document.createElement('div');
                        item.className = 'list-group-item';
                        item.innerHTML = `
                            <strong>${medicamento.clave}</strong> - ${medicamento.descripcion}
                            <small class="text-muted float-right">${medicamento.presentacion || 'UNIDAD'}</small>
                        `;
                        item.addEventListener('click', () => seleccionarMedicamento(medicamento));
                        resultadosBusqueda.appendChild(item);
                    });
                }
                
                resultadosBusqueda.style.display = 'block';
            })
            .catch(error => {
                console.error('Error al buscar medicamentos:', error);
                resultadosBusqueda.style.display = 'none';
            });
    }
    
    function seleccionarMedicamento(medicamento) {
        document.getElementById('clave_medicamento').value = medicamento.clave;
        document.getElementById('medicamento_id').value = medicamento.id; // Guardar el ID real
        document.getElementById('nombre_medicamento').value = medicamento.descripcion;
        document.getElementById('descripcion').value = medicamento.descripcion;
        buscarMedicamento.value = '';
        resultadosBusqueda.style.display = 'none';
        document.getElementById('presentacion').focus();
    }
    
    function toggleTipoEntrada() {
        if (tipoEntrada.value === 'TRANSFERENCIA') {
            grupoInstitucion.style.display = 'block';
            grupoAlmacen.style.display = 'none';
            document.getElementById('institucion').required = true;
            document.getElementById('almacen').required = false;
        } else {
            grupoInstitucion.style.display = 'none';
            grupoAlmacen.style.display = 'block';
            document.getElementById('institucion').required = false;
            document.getElementById('almacen').required = true;
        }
    }
    
    function agregarEntrada() {
        // Validar campos obligatorios
        const lote = document.getElementById('lote').value;
    
    // Verificar duplicados
        if (entradas.some(e => e.lote === lote)) {
            mostrarNotificacion('warning', '¡Este lote ya fue agregado!');
            return;
        }
        
        const camposRequeridos = [
            'clave_medicamento', 'presentacion', 'lote', 'caducidad', 
            'cantidad', 'precio_unitario', 'tipo_entrada'
        ];
        
        let valido = true;
        camposRequeridos.forEach(campo => {
            const elemento = document.getElementById(campo);
            if (!elemento.value) {
                elemento.classList.add('is-invalid');
                valido = false;
            } else {
                elemento.classList.remove('is-invalid');
            }
        });
        
        if (!valido) {
            alert('Por favor complete todos los campos requeridos');
            return;
        }
        
        // Crear objeto de entrada
        const entrada = {
            medicamento_id: document.getElementById('medicamento_id').value,
            clave: document.getElementById('clave_medicamento').value,
            nombre: document.getElementById('nombre_medicamento').value,
            presentacion: document.getElementById('presentacion').options[document.getElementById('presentacion').selectedIndex].text,
            presentacion_id: document.getElementById('presentacion').value,
            lote: document.getElementById('lote').value,
            caducidad: document.getElementById('caducidad').value,
            cantidad: parseInt(document.getElementById('cantidad').value),
            precio_unitario: parseFloat(document.getElementById('precio_unitario').value),
            tipo_entrada: document.getElementById('tipo_entrada').value,
            institucion: document.getElementById('institucion').value,
            almacen: document.getElementById('almacen').value,
            fuente_financiamiento: document.getElementById('fuente_financiamiento').value,
            contrato: document.getElementById('contrato').value,
            proceso: document.getElementById('proceso').value
        };
        
        entrada.total = entrada.cantidad * entrada.precio_unitario;
        
        // Agregar a la lista
        entradas.push(entrada);
        
        // Actualizar tabla
        actualizarTabla();
        
        // Limpiar campos del medicamento
        document.getElementById('presentacion').value = '';
        document.getElementById('lote').value = '';
        document.getElementById('caducidad').value = '';
        document.getElementById('cantidad').value = '';
        document.getElementById('precio_unitario').value = '';
        
        // Enfocar campo de lote
        document.getElementById('lote').focus();
    }
    
    function actualizarTabla() {
        tablaEntradas.innerHTML = '';
        let granTotal = 0;
        
        entradas.forEach((entrada, index) => {
            granTotal += entrada.total;
            
            const fila = document.createElement('tr');
            fila.innerHTML = `
                <td>${entrada.clave}</td>
                <td>${entrada.nombre}</td>
                <td>${entrada.presentacion}</td>
                <td>${entrada.lote}</td>
                <td>${entrada.caducidad}</td>
                <td>${entrada.cantidad}</td>
                <td>$${entrada.precio_unitario.toFixed(2)}</td>
                <td>$${entrada.total.toFixed(2)}</td>
                <td>
                    <button class="btn btn-danger btn-sm btn-action" onclick="eliminarEntrada(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            
            tablaEntradas.appendChild(fila);
        });
        
        totalGeneral.textContent = `$${granTotal.toFixed(2)}`;
    }
    
    function eliminarEntrada(index) {
        if (confirm('¿Está seguro que desea eliminar esta entrada?')) {
            entradas.splice(index, 1);
            actualizarTabla();
        }
    }
    
    function mostrarConfirmacion() {
        if (entradas.length === 0) {
            alert('No hay entradas para guardar');
            return;
        }
        
        $('#confirmModal').modal('show');
    }


function generarFolioAutomatico() {
    const hoy = new Date();
    const dateStr = hoy.toISOString().split('T')[0].replace(/-/g, '');
    return `ENT-${dateStr}-${Math.floor(Math.random() * 10000).toString().padStart(4, '0')}`;
}

function guardarEntradas() {
    $('#confirmModal').modal('hide');
    
    // Verificar que tenemos medicamentos para guardar
    if (entradas.length === 0) {
        alert('Error: No hay medicamentos agregados para guardar');
        return;
    }

    // Obtener todos los campos necesarios
    const recibidoPorInput = document.querySelector('input[name="recibido_por"][type="hidden"]');
    const folioInput = document.getElementById('folio_entrada');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    // Validar campos requeridos
    if (!recibidoPorInput || !folioInput || !csrfToken) {
        alert('Error: Faltan datos requeridos en el formulario');
        return;
    }

    // Construir objeto de datos que coincida exactamente con views.py
    const datos = {
        folio: folioInput.value || generarFolioAutomatico(),
        fecha: document.getElementById('fecha').value,
        tipo_entrada: document.getElementById('tipo_entrada').value,
        almacen: document.getElementById('almacen')?.value || null,
        institucion: document.getElementById('institucion')?.value || null,
        fuente_financiamiento: document.getElementById('fuente_financiamiento').value,
        contrato: document.getElementById('contrato')?.value || '',
        proceso: document.getElementById('proceso').value,
        recibido_por: recibidoPorInput.value,
        detalles: entradas.map(entrada => ({
            medicamento_id: entrada.medicamento_id,  // Asegúrate que 'clave' sea el ID correcto del medicamento
            lote: entrada.lote,
            caducidad: entrada.caducidad,
            cantidad: entrada.cantidad,
            precio_unitario: entrada.precio_unitario,
            presentacion_id: entrada.presentacion_id
        }))
    };

    // Validación adicional
    const requiredFields = {
        'fuente_financiamiento': 'Fuente de financiamiento',
        'proceso': 'Proceso',
        'recibido_por': 'Usuario receptor'
    };

    for (const [field, name] of Object.entries(requiredFields)) {
        if (!datos[field]) {
            alert(`Error: El campo ${name} es requerido`);
            return;
        }
    }

    console.log('Datos a enviar:', datos); // Para depuración

    fetch('/api/entradas/guardar/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(datos)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                throw new Error(errData.error || `Error del servidor: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert(`Éxito: Entrada ${data.folio} guardada correctamente`);
            setTimeout(() => {
                window.location.href = data.redirect_url || "{% url 'farmacia_g' %}";
            }, 2000);
            entradas = [];
            actualizarTabla();
        } else {
            throw new Error(data.error || 'Error desconocido al guardar');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(`Error al guardar: ${error.message}`);
    });
}
    
// Función compartida para preparar datos
    function prepararDatosReporte() {
        const almacenSelect = document.getElementById('almacen');
        const institucionSelect = document.getElementById('institucion');
        const fuenteSelect = document.getElementById('fuente_financiamiento');
        
        return {
            titulo: 'REPORTE DE ENTRADA DE MEDICAMENTOS',
            folio: document.getElementById('folio_entrada').value,
            fecha: document.getElementById('fecha').value,
            tipo_entrada: document.getElementById('tipo_entrada').value,
            almacen: almacenSelect.value,
            almacen_nombre: almacenSelect.options[almacenSelect.selectedIndex]?.text || '',
            institucion: institucionSelect.value,
            institucion_nombre: institucionSelect.options[institucionSelect.selectedIndex]?.text || '',
            fuente_financiamiento: fuenteSelect.value,
            fuente_financiamiento_nombre: fuenteSelect.options[fuenteSelect.selectedIndex]?.text || '',
            proceso: document.getElementById('proceso').value,
            items: entradas.map(entrada => ({
                nombre: entrada.nombre,
                lote: entrada.lote,
                presentacion: entrada.presentacion,
                cantidad: entrada.cantidad,
                precio_unitario: entrada.precio_unitario,
                total: entrada.total
            })),
            total: entradas.reduce((sum, entrada) => sum + entrada.total, 0)
        };
    }

    // Función para manejar la respuesta de descarga
    function manejarDescarga(response, tipo) {
        if (!response.ok) throw new Error(`Error al generar ${tipo.toUpperCase()}`);
        return response.blob().then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ENTRADA_${document.getElementById('folio_entrada').value}.${tipo}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            mostrarNotificacion('success', `Reporte ${tipo.toUpperCase()} generado correctamente`);
        });
    }

    // Función para manejar errores
    function manejarErrorReporte(error) {
        console.error('Error:', error);
        mostrarNotificacion('danger', `Error al generar reporte: ${error.message}`);
    }

    // Generar PDF
    function generarReportePDF() {
        if (entradas.length === 0) {
            mostrarNotificacion('warning', 'No hay entradas para generar el reporte');
            return;
        }

        const datosReporte = prepararDatosReporte();

        fetch('/api/generar-reporte-pdf/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(datosReporte)
        })
        .then(response => manejarDescarga(response, 'pdf'))
        .catch(manejarErrorReporte);
    }

    // Función para generar reporte Excel
    function generarReporteExcel() {
        if (entradas.length === 0) {
            mostrarNotificacion('warning', 'No hay entradas para generar el reporte');
            return;
        }

        const datosReporte = prepararDatosReporte();

        fetch('/api/generar-reporte-excel/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(datosReporte)
        })
        .then(response => manejarDescarga(response, 'xlsx'))
        .catch(manejarErrorReporte);
    }


    // Generar Excel (similar estructura pero con diferente endpoint)
    function prepararDatosReporte() {
        // Obtener elementos select
        const almacenSelect = document.getElementById('almacen');
        const fuenteSelect = document.getElementById('fuente_financiamiento');
        
        return {
            titulo: 'REPORTE DE ENTRADA DE MEDICAMENTOS',
            folio: document.getElementById('folio_entrada').value,
            fecha: document.getElementById('fecha').value,
            tipo_entrada: document.getElementById('tipo_entrada').value,
            almacen: almacenSelect.value,
            almacen_nombre: almacenSelect.options[almacenSelect.selectedIndex]?.text || '',
            fuente_financiamiento: fuenteSelect.value,
            fuente_financiamiento_nombre: fuenteSelect.options[fuenteSelect.selectedIndex]?.text || '',
            proceso: document.getElementById('proceso').value,
            items: entradas.map(entrada => ({
                nombre: entrada.nombre,
                lote: entrada.lote,
                presentacion: entrada.presentacion,
                cantidad: entrada.cantidad,
                precio_unitario: entrada.precio_unitario,
                total: entrada.total
            })),
            total: entradas.reduce((sum, entrada) => sum + entrada.total, 0)
        };
    }
    
    // Hacer funciones disponibles globalmente
    window.eliminarEntrada = eliminarEntrada;
});