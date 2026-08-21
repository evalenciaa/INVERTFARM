document.addEventListener('DOMContentLoaded', function() {
    // Elementos del DOM
    const filtroMedicamentoInput = document.getElementById('filtro-medicamento-input');
    const filtroMedicamentoId = document.getElementById('filtro-medicamento-id');
    const resultadosFiltro = document.getElementById('resultados-filtro-medicamento');

    // Si esta vista no tiene el autocompletado, no inicializar nada (y no sobreescribir window.limpiarFiltros)
    if (!filtroMedicamentoInput || !filtroMedicamentoId || !resultadosFiltro) return;
    const filtroColor = document.getElementById('filtro-color');
    const btnFiltrar = document.getElementById('btn-filtrar');
    const btnLimpiar = document.getElementById('btn-limpiar');

    // Variables
    let timeoutBusqueda = null;

    // Eventos
    if (filtroMedicamentoInput) {
        filtroMedicamentoInput.addEventListener('input', manejarInputMedicamento);
        filtroMedicamentoInput.addEventListener('focus', mostrarResultadosSiHay);
        filtroMedicamentoInput.addEventListener('blur', ocultarResultadosConRetraso);
    }

    if (filtroColor) {
        filtroColor.addEventListener('change', filtrarTabla);
    }

    if (btnFiltrar) {
        btnFiltrar.addEventListener('click', filtrarTabla);
    }

    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', limpiarFiltros);
    }

    // Funciones de autocompletado
    function manejarInputMedicamento() {
        clearTimeout(timeoutBusqueda);
        const query = filtroMedicamentoInput.value.trim();
        
        if (query.length < 2) {
            resultadosFiltro.style.display = 'none';
            filtroMedicamentoId.value = '';
            return;
        }
        
        timeoutBusqueda = setTimeout(() => {
            buscarMedicamentos(query);
        }, 300);
    }

    function buscarMedicamentos(query) {
        fetch(`/api/medicamentos/buscar/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                mostrarResultadosBusqueda(data);
            })
            .catch(error => {
                console.error('Error al buscar medicamentos:', error);
                resultadosFiltro.style.display = 'none';
            });
    }

    function mostrarResultadosBusqueda(medicamentos) {
        resultadosFiltro.innerHTML = '';
        
        if (medicamentos.length === 0) {
            const item = document.createElement('div');
            item.className = 'list-group-item';
            item.textContent = 'No se encontraron medicamentos';
            resultadosFiltro.appendChild(item);
        } else {
            medicamentos.forEach(medicamento => {
                const item = document.createElement('div');
                item.className = 'list-group-item';
                item.innerHTML = `
                    <strong>${medicamento.clave}</strong> - ${medicamento.descripcion}
                    <small class="text-muted d-block">${medicamento.presentacion || 'UNIDAD'}</small>
                `;
                item.addEventListener('click', () => seleccionarMedicamento(medicamento));
                resultadosFiltro.appendChild(item);
            });
        }
        
        resultadosFiltro.style.display = 'block';
    }

    function seleccionarMedicamento(medicamento) {
        filtroMedicamentoInput.value = medicamento.descripcion;
        filtroMedicamentoId.value = medicamento.id;
        resultadosFiltro.style.display = 'none';
        filtrarTabla(); // Filtrar automáticamente al seleccionar
    }

    function mostrarResultadosSiHay() {
        if (resultadosFiltro.innerHTML.trim() !== '') {
            resultadosFiltro.style.display = 'block';
        }
    }

    function ocultarResultadosConRetraso() {
        setTimeout(() => {
            resultadosFiltro.style.display = 'none';
        }, 200);
    }

    // Funciones de filtrado
    function filtrarTabla() {
        const filtroTexto = filtroMedicamentoInput.value.toLowerCase();
        const filtroId = filtroMedicamentoId.value;
        const filtroColorValor = filtroColor ? filtroColor.value : '';

        const filas = document.querySelectorAll('.medicamentos-table tbody tr');
        let filasVisibles = 0;

        filas.forEach(fila => {
            const textoFila = fila.querySelector('.campo-descripcion').value.toLowerCase();
            const idMedicamento = fila.querySelector('.campo-descripcion').dataset.medicamentoId;
            const colorFila = fila.dataset.color || '';
            
            let mostrar = true;

            if (filtroTexto && !textoFila.includes(filtroTexto)) {
                mostrar = false;
            }

            if (filtroId && idMedicamento !== filtroId) {
                mostrar = false;
            }

            if (filtroColorValor && colorFila !== filtroColorValor) {
                mostrar = false;
            }

            fila.style.display = mostrar ? '' : 'none';
            if (mostrar) filasVisibles++;
        });
    }

    function limpiarFiltros() {
    if (filtroMedicamentoInput) {
        filtroMedicamentoInput.value = '';
        if (filtroMedicamentoId) filtroMedicamentoId.value = '';
    }
    if (filtroColor) filtroColor.value = '';
    if (resultadosFiltro) resultadosFiltro.style.display = 'none';
    if (typeof filtrarTabla === 'function') filtrarTabla();
    }

        window.filtrarTabla = filtrarTabla;
        window.limpiarFiltros = limpiarFiltros;
    });

// En filtros.js - Actualizar la función guardarFila
function guardarFila(loteId) {
    const fila = document.querySelector(`tr[data-id="${loteId}"]`);
    if (!fila) {
        alert('Error: No se encontró la fila con ID ' + loteId);
        return;
    }

    const datos = {
        lote_codigo: fila.querySelector(`input[name="lote_codigo_${loteId}"]`).value,
        existencia: fila.querySelector(`input[name="existencia_${loteId}"]`).value,
        cpm: fila.querySelector(`input[name="cpm_${loteId}"]`).value,
        presentacion: fila.querySelector(`select[name="presentacion_${loteId}"]`).value,
        fecha_caducidad: fila.querySelector(`input[name="fecha_caducidad_${loteId}"]`).value,
        csrfmiddlewaretoken: document.querySelector('[name=csrfmiddlewaretoken]').value
    };

    fetch(`/editar_lote/${loteId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(datos)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error HTTP: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.mensaje) {
            alert('✓ Lote actualizado correctamente');
            fila.dataset.existencia = datos.existencia;
            fila.dataset.cpm = datos.cpm;
            fila.dataset.fecha = datos.fecha_caducidad; // Actualizar dataset
        } else {
            alert('✗ Error: ' + (data.error || 'Error desconocido'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('✗ Error al conectar con el servidor: ' + error.message);
    });
}