document.addEventListener('DOMContentLoaded', function () {
    let entradas = [];
    let medicamentoSeleccionado = null;
    const hoy = new Date().toISOString().split('T')[0];

    const buscarMedicamento = document.getElementById('buscar-medicamento');
    const resultadosBusqueda = document.getElementById('resultados-busqueda');
    const btnBuscar = document.getElementById('btn-buscar');
    const btnAgregar = document.getElementById('btn-agregar');
    const btnGuardar = document.getElementById('btn-guardar');
    const tipoEntrada = document.getElementById('tipo_entrada');
    const grupoInstitucion = document.getElementById('grupo-institucion');
    const grupoAlmacen = document.getElementById('grupo-almacen');
    const tablaEntradas = document.querySelector('#tabla-entradas tbody');
    const totalGeneral = document.getElementById('total-general');
    const recibidoPorInput = document.querySelector('input[name="recibido_por"]');

    const presentacionSelect = document.getElementById('presentacion');
    const loteInput = document.getElementById('lote');
    const caducidadInput = document.getElementById('caducidad');
    const cantidadInput = document.getElementById('cantidad');
    const precioUnitarioInput = document.getElementById('precio_unitario');
    const fechaInput = document.getElementById('fecha');
    const almacenSelect = document.getElementById('almacen');
    const institucionSelect = document.getElementById('institucion');
    const fuenteSelect = document.getElementById('fuente_financiamiento');
    const grupoFuente = document.getElementById('grupo-fuente-financiamiento');
    const contratoInput = document.getElementById('contrato');
    const procesoInput = document.getElementById('proceso');
    const folioEntradaInput = document.getElementById('folio_entrada');

    const claveMedicamentoInput = document.getElementById('clave_medicamento');
    const medicamentoIdInput = document.getElementById('medicamento_id');
    const nombreMedicamentoInput = document.getElementById('nombre_medicamento');
    const descripcionInput = document.getElementById('descripcion');

    const contenedorInfoMedicamento = document.getElementById('contenedor-info-medicamento');
    const infoClave = document.getElementById('info-clave');
    const infoDescripcion = document.getElementById('info-descripcion');
    const infoPresentacion = document.getElementById('info-presentacion');
    const infoEsAntibiotico = document.getElementById('info-es-antibiotico');
    const infoAntibioticoExtra = document.getElementById('info-antibiotico-extra');
    const infoVia = document.getElementById('info-via');
    const infoCodigoAtc = document.getElementById('info-codigo-atc');
    const infoAware = document.getElementById('info-aware');
    const infoGramos = document.getElementById('info-gramos');
    const infoValorAtc = document.getElementById('info-valor-atc');

    const confirmModal = document.getElementById('confirmModal');
    const confirmSaveBtn = document.getElementById('confirm-save');
    const closeModalTriggers = document.querySelectorAll('[data-close-modal]');

    let ultimoElementoEnfocado = null;

    if (fechaInput) fechaInput.value = hoy;
    if (caducidadInput) caducidadInput.min = hoy;

    if (buscarMedicamento) buscarMedicamento.addEventListener('input', debounce(buscarMedicamentos, 250));
    if (btnBuscar) btnBuscar.addEventListener('click', buscarMedicamentos);
    if (btnAgregar) btnAgregar.addEventListener('click', agregarEntrada);
    if (btnGuardar) btnGuardar.addEventListener('click', mostrarConfirmacion);
    if (confirmSaveBtn) confirmSaveBtn.addEventListener('click', guardarEntradas);
    if (tipoEntrada) tipoEntrada.addEventListener('change', toggleTipoEntrada);

    if (tablaEntradas) {
        tablaEntradas.addEventListener('click', function (e) {
            const btnEliminar = e.target.closest('.btn-eliminar-entrada');
            if (!btnEliminar) return;

            const index = parseInt(btnEliminar.dataset.index, 10);
            if (Number.isInteger(index)) {
                eliminarEntrada(index);
            }
        });
    }

    closeModalTriggers.forEach(trigger => {
        trigger.addEventListener('click', cerrarModalConfirmacion);
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && confirmModal && !confirmModal.hidden) {
            cerrarModalConfirmacion();
        }
    });

    document.addEventListener('click', function (e) {
        if (
            resultadosBusqueda &&
            !resultadosBusqueda.contains(e.target) &&
            buscarMedicamento &&
            !buscarMedicamento.contains(e.target) &&
            btnBuscar &&
            !btnBuscar.contains(e.target)
        ) {
            ocultarResultadosBusqueda();
        }
    });

    toggleTipoEntrada();

    function debounce(fn, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function mostrarNotificacion(tipo, mensaje) {
        const notification = document.createElement('div');
        notification.className = `notification notification--${mapearTipoNotificacion(tipo)}`;
        notification.textContent = mensaje;
        document.body.appendChild(notification);

        window.setTimeout(() => {
            notification.remove();
        }, 3500);
    }

    function mapearTipoNotificacion(tipo) {
        if (tipo === 'success') return 'success';
        if (tipo === 'warning') return 'warning';
        if (tipo === 'danger' || tipo === 'error') return 'danger';
        return 'info';
    }

    function buscarMedicamentos() {
        const query = buscarMedicamento.value.trim();

        if (query.length < 2) {
            ocultarResultadosBusqueda();
            return;
        }

        fetch(`/api/medicamentos/buscar/?q=${encodeURIComponent(query)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('No se pudo realizar la búsqueda.');
                }
                return response.json();
            })
            .then(data => {
                renderizarResultadosBusqueda(Array.isArray(data) ? data : []);
            })
            .catch(error => {
                console.error('Error al buscar medicamentos:', error);
                ocultarResultadosBusqueda();
                mostrarNotificacion('danger', 'Error al buscar medicamentos.');
            });
    }

    function renderizarResultadosBusqueda(medicamentos) {
        resultadosBusqueda.innerHTML = '';

        if (!medicamentos.length) {
            const item = document.createElement('div');
            item.className = 'list-group-item';
            item.textContent = 'No se encontraron medicamentos';
            resultadosBusqueda.appendChild(item);
            mostrarResultadosBusqueda();
            return;
        }

        medicamentos.forEach(medicamento => {
            const item = document.createElement('div');
            item.className = 'list-group-item';
            item.innerHTML = `
                <strong>${escapeHtml(medicamento.clave || '')}</strong> - ${escapeHtml(medicamento.descripcion || '')}
                <small>${escapeHtml(medicamento.presentacion || 'UNIDAD')}</small>
            `;
            item.addEventListener('click', function () {
                seleccionarMedicamento(medicamento);
            });
            resultadosBusqueda.appendChild(item);
        });

        mostrarResultadosBusqueda();
    }

    function seleccionarMedicamento(medicamento) {
        medicamentoSeleccionado = medicamento;

        claveMedicamentoInput.value = medicamento.clave || '';
        medicamentoIdInput.value = medicamento.id || '';
        nombreMedicamentoInput.value = medicamento.descripcion || '';
        descripcionInput.value = medicamento.descripcion || '';

        infoClave.textContent = medicamento.clave || '-';
        infoDescripcion.textContent = medicamento.descripcion || '-';
        infoPresentacion.textContent = medicamento.presentacion || obtenerTextoPresentacionActual() || '-';

        const esAntibiotico = Boolean(
            medicamento.es_antibiotico === true ||
            medicamento.antibiotico === true ||
            medicamento.tipo === 'ANTIBIOTICO' ||
            medicamento.categoria === 'ANTIBIOTICO'
        );

        infoEsAntibiotico.textContent = esAntibiotico ? 'Sí' : 'No';

        if (esAntibiotico) {
            infoVia.textContent = medicamento.via_administracion || medicamento.via || '-';
            infoCodigoAtc.textContent = medicamento.codigo_atc || '-';
            infoAware.textContent = medicamento.categoria_aware || medicamento.aware || '-';
            infoGramos.textContent = medicamento.gramos_por_pieza || medicamento.gramos || '-';
            infoValorAtc.textContent = medicamento.valor_atc || '-';
            infoAntibioticoExtra.hidden = false;
        } else {
            infoVia.textContent = '-';
            infoCodigoAtc.textContent = '-';
            infoAware.textContent = '-';
            infoGramos.textContent = '-';
            infoValorAtc.textContent = '-';
            infoAntibioticoExtra.hidden = true;
        }

        contenedorInfoMedicamento.hidden = false;
        buscarMedicamento.value = '';
        ocultarResultadosBusqueda();
        presentacionSelect.focus();
    }


    function toggleTipoEntrada() {
        const esTransferencia = tipoEntrada.value === 'TRANSFERENCIA';

        grupoInstitucion.hidden = !esTransferencia;
        grupoAlmacen.hidden = esTransferencia;

        institucionSelect.required = esTransferencia;
        institucionSelect.disabled = !esTransferencia;

        almacenSelect.required = !esTransferencia;
        almacenSelect.disabled = esTransferencia;

        fuenteSelect.required = !esTransferencia;

        if (esTransferencia) {
            almacenSelect.value = '';
            fuenteSelect.value = '';
        } else {
            institucionSelect.value = '';
        }
    }

    function agregarEntrada() {
        limpiarValidaciones();

        const lote = loteInput.value.trim().toUpperCase();
        const cantidad = parseInt(cantidadInput.value, 10);
        const precioUnitario = parseFloat(precioUnitarioInput.value);

        if (!medicamentoIdInput.value) {
            mostrarNotificacion('warning', 'Seleccione un medicamento antes de agregarlo.');
            buscarMedicamento.focus();
            return;
        }

        if (entradas.some(e => e.lote.toUpperCase() === lote)) {
            mostrarNotificacion('warning', 'Este lote ya fue agregado a la lista.');
            loteInput.focus();
            return;
        }

        const camposBase = [
            'clave_medicamento',
            'presentacion',
            'lote',
            'caducidad',
            'cantidad',
            'precio_unitario',
            'tipo_entrada',
            'proceso'
        ];

        if (tipoEntrada.value === 'TRANSFERENCIA') {
            camposBase.push('institucion');
        } else if (tipoEntrada.value === 'ALMACEN') {
            camposBase.push('almacen', 'fuente_financiamiento');
        }

        const esValido = validarCampos(camposBase);
        if (!esValido) {
            mostrarNotificacion('danger', 'Complete todos los campos obligatorios.');
            return;
        }

        if (!Number.isInteger(cantidad) || cantidad <= 0) {
            cantidadInput.classList.add('is-invalid');
            mostrarNotificacion('warning', 'La cantidad debe ser mayor a cero.');
            cantidadInput.focus();
            return;
        }

        if (Number.isNaN(precioUnitario) || precioUnitario < 0) {
            precioUnitarioInput.classList.add('is-invalid');
            mostrarNotificacion('warning', 'Ingrese un precio unitario válido.');
            precioUnitarioInput.focus();
            return;
        }

        const entrada = {
            medicamento_id: medicamentoIdInput.value,
            clave: claveMedicamentoInput.value,
            nombre: nombreMedicamentoInput.value,
            descripcion: descripcionInput.value,
            presentacion: presentacionSelect.options[presentacionSelect.selectedIndex]?.text || '',
            presentacion_id: presentacionSelect.value,
            lote: lote,
            caducidad: caducidadInput.value,
            cantidad: cantidad,
            precio_unitario: precioUnitario,
            tipo_entrada: tipoEntrada.value,
            institucion: institucionSelect.value,
            institucion_texto: institucionSelect.options[institucionSelect.selectedIndex]?.text || '',
            almacen: almacenSelect.value,
            almacen_texto: almacenSelect.options[almacenSelect.selectedIndex]?.text || '',
            fuente_financiamiento: fuenteSelect.value,
            fuente_financiamiento_texto: fuenteSelect.options[fuenteSelect.selectedIndex]?.text || '',
            contrato: contratoInput.value.trim(),
            proceso: procesoInput.value.trim(),
            folio_entrada: folioEntradaInput ? folioEntradaInput.value.trim() : '',
            es_antibiotico: medicamentoSeleccionado?.es_antibiotico || false,
            via_administracion: medicamentoSeleccionado?.via_administracion || medicamentoSeleccionado?.via || '',
            codigo_atc: medicamentoSeleccionado?.codigo_atc || '',
            categoria_aware: medicamentoSeleccionado?.categoria_aware || medicamentoSeleccionado?.aware || '',
            gramos_por_pieza: medicamentoSeleccionado?.gramos_por_pieza || medicamentoSeleccionado?.gramos || '',
            valor_atc: medicamentoSeleccionado?.valor_atc || ''
        };

        entrada.total = entrada.cantidad * entrada.precio_unitario;

        entradas.push(entrada);
        actualizarTabla();
        limpiarCamposCaptura();
        mostrarNotificacion('success', 'Medicamento agregado a la lista.');
    }

    function validarCampos(ids) {
        let valido = true;

        ids.forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;

            const valor = (el.value || '').trim();
            if (!valor) {
                el.classList.add('is-invalid');
                valido = false;
            }
        });

        return valido;
    }

    function limpiarValidaciones() {
        document.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });
    }

    function actualizarTabla() {
        tablaEntradas.innerHTML = '';

        if (!entradas.length) {
            totalGeneral.textContent = formatearMoneda(0);
            return;
        }

        let granTotal = 0;

        entradas.forEach((entrada, index) => {
            granTotal += entrada.total;

            const fila = document.createElement('tr');
            fila.innerHTML = `
                <td>${escapeHtml(entrada.clave)}</td>
                <td>${escapeHtml(entrada.nombre)}</td>
                <td>${escapeHtml(entrada.presentacion)}</td>
                <td>${escapeHtml(entrada.lote)}</td>
                <td>${escapeHtml(formatearFecha(entrada.caducidad))}</td>
                <td>${entrada.cantidad}</td>
                <td>${formatearMoneda(entrada.precio_unitario)}</td>
                <td>${formatearMoneda(entrada.total)}</td>
                <td>
                    <button
                        type="button"
                        class="btn-action btn-eliminar-entrada"
                        data-index="${index}"
                        aria-label="Eliminar entrada"
                        title="Eliminar entrada"
                    >
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tablaEntradas.appendChild(fila);
        });

        totalGeneral.textContent = formatearMoneda(granTotal);
    }

    function eliminarEntrada(index) {
        entradas.splice(index, 1);
        actualizarTabla();
        mostrarNotificacion('info', 'Entrada eliminada de la lista.');
    }

    function limpiarCamposCaptura() {
        presentacionSelect.value = '';
        loteInput.value = '';
        caducidadInput.value = '';
        cantidadInput.value = '';
        precioUnitarioInput.value = '';
        buscarMedicamento.value = '';

        claveMedicamentoInput.value = '';
        medicamentoIdInput.value = '';
        nombreMedicamentoInput.value = '';
        descripcionInput.value = '';

        medicamentoSeleccionado = null;
        contenedorInfoMedicamento.hidden = true;
        infoAntibioticoExtra.hidden = true;

        presentacionSelect.focus();
    }

    function mostrarConfirmacion() {
        if (!entradas.length) {
            mostrarNotificacion('warning', 'No hay entradas para guardar.');
            return;
        }

        ultimoElementoEnfocado = document.activeElement;
        confirmModal.hidden = false;
        document.body.style.overflow = 'hidden';

        if (confirmSaveBtn) {
            confirmSaveBtn.focus();
        }
    }

    function cerrarModalConfirmacion() {
        confirmModal.hidden = true;
        document.body.style.overflow = '';

        if (ultimoElementoEnfocado && typeof ultimoElementoEnfocado.focus === 'function') {
            ultimoElementoEnfocado.focus();
        }
    }

    async function guardarEntradas() {
        if (!entradas.length) {
            cerrarModalConfirmacion();
            mostrarNotificacion('warning', 'No hay entradas para guardar.');
            return;
        }

        confirmSaveBtn.disabled = true;
        btnGuardar.disabled = true;

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        const payload = {
            folio: folioEntradaInput ? folioEntradaInput.value.trim() : '',
            fecha: fechaInput.value,
            tipo_entrada: tipoEntrada.value,
            almacen: almacenSelect.value || null,
            institucion: institucionSelect.value || null,
            fuente_financiamiento: fuenteSelect.value,
            contrato: contratoInput.value.trim(),
            proceso: procesoInput.value.trim(),
            recibido_por: recibidoPorInput ? recibidoPorInput.value : '',
            observaciones: '',
            detalles: entradas.map(item => ({
                medicamento_id: item.medicamento_id,
                presentacion_id: item.presentacion_id,
                lote: item.lote,
                caducidad: item.caducidad,
                cantidad: item.cantidad,
                precio_unitario: item.precio_unitario
            }))
        };

        try {
            const response = await fetch('/api/entradas/guardar/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'No se pudieron guardar las entradas.');
            }

            await descargarPdfEntrada(payload);

            cerrarModalConfirmacion();
            mostrarNotificacion('success', `Entrada ${data.folio || payload.folio} guardada correctamente.`);

            entradas = [];
            actualizarTabla();
            resetFormularioCompleto();

        } catch (error) {
            console.error('Error al guardar entradas:', error);
            mostrarNotificacion('danger', error.message || 'Ocurrió un error al guardar.');
        } finally {
            confirmSaveBtn.disabled = false;
            btnGuardar.disabled = false;
        }
    }

    async function descargarPdfEntrada(payloadGuardado) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        const totalGeneralCalculado = entradas.reduce((acc, item) => acc + (Number(item.total) || 0), 0);

        const payloadPdf = {
            folio: payloadGuardado.folio,
            fecha: payloadGuardado.fecha,
            tipo_entrada: payloadGuardado.tipo_entrada,
            almacen_nombre: payloadGuardado.tipo_entrada === 'ALMACEN'
                ? (almacenSelect.options[almacenSelect.selectedIndex]?.text || 'N/A')
                : (institucionSelect.options[institucionSelect.selectedIndex]?.text || 'N/A'),
            fuente_financiamiento_nombre: fuenteSelect.options[fuenteSelect.selectedIndex]?.text || 'N/A',
            proceso: payloadGuardado.proceso,
            items: entradas.map(item => ({
                nombre: item.nombre,
                lote: item.lote,
                presentacion: item.presentacion,
                cantidad: item.cantidad,
                precio_unitario: item.precio_unitario,
                total: item.total
            })),
            total: totalGeneralCalculado
        };

        const response = await fetch('/api/generar-reporte-pdf/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payloadPdf)
        });

        if (!response.ok) {
            let mensaje = 'No se pudo generar el PDF.';
            try {
                const errorData = await response.json();
                mensaje = errorData.error || mensaje;
            } catch (_) {}
            throw new Error(mensaje);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ENTRADA_${payloadGuardado.folio || 'REPORTE'}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    }

    function generarReportePDF() {
        if (!entradas.length) {
            mostrarNotificacion('warning', 'No hay datos para generar el PDF.');
            return;
        }

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/farmacia/entradas/reporte/pdf/';
        form.target = '_blank';

        agregarCampoOculto(form, 'csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]')?.value || '');
        agregarCampoOculto(form, 'entradas', JSON.stringify(entradas));
        agregarCampoOculto(form, 'fecha', fechaInput.value);
        agregarCampoOculto(form, 'tipo_entrada', tipoEntrada.value);
        agregarCampoOculto(form, 'almacen', almacenSelect.value);
        agregarCampoOculto(form, 'institucion', institucionSelect.value);
        agregarCampoOculto(form, 'fuente_financiamiento', fuenteSelect.value);
        agregarCampoOculto(form, 'contrato', contratoInput.value.trim());
        agregarCampoOculto(form, 'proceso', procesoInput.value.trim());
        agregarCampoOculto(form, 'folio_entrada', folioEntradaInput ? folioEntradaInput.value.trim() : '');

        document.body.appendChild(form);
        form.submit();
        form.remove();
    }

    function agregarCampoOculto(form, nombre, valor) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = nombre;
        input.value = valor;
        form.appendChild(input);
    }

    function resetFormularioCompleto() {
        buscarMedicamento.value = '';
        presentacionSelect.value = '';
        loteInput.value = '';
        caducidadInput.value = '';
        cantidadInput.value = '';
        precioUnitarioInput.value = '';
        tipoEntrada.value = '';
        almacenSelect.value = '';
        institucionSelect.value = '';
        fuenteSelect.value = '';
        contratoInput.value = '';
        procesoInput.value = '';

        if (folioEntradaInput) {
            folioEntradaInput.value = '';
        }

        claveMedicamentoInput.value = '';
        medicamentoIdInput.value = '';
        nombreMedicamentoInput.value = '';
        descripcionInput.value = '';

        medicamentoSeleccionado = null;
        contenedorInfoMedicamento.hidden = true;
        infoAntibioticoExtra.hidden = true;
        ocultarResultadosBusqueda();
        limpiarValidaciones();
        toggleTipoEntrada();

        if (fechaInput) fechaInput.value = hoy;
        if (caducidadInput) caducidadInput.min = hoy;

        buscarMedicamento.focus();
    }

    function mostrarResultadosBusqueda() {
        resultadosBusqueda.style.display = 'block';
        resultadosBusqueda.classList.add('is-visible');
    }

    function ocultarResultadosBusqueda() {
        resultadosBusqueda.style.display = 'none';
        resultadosBusqueda.classList.remove('is-visible');
    }

    function obtenerTextoPresentacionActual() {
        return presentacionSelect.options[presentacionSelect.selectedIndex]?.text || '';
    }

    function formatearMoneda(valor) {
        return new Intl.NumberFormat('es-MX', {
            style: 'currency',
            currency: 'MXN'
        }).format(Number(valor) || 0);
    }

    function formatearFecha(fecha) {
        if (!fecha) return '';
        const partes = fecha.split('-');
        if (partes.length !== 3) return fecha;
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }

    function escapeHtml(texto) {
        return String(texto ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }
});