document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('form-medicamento');
    const claveInput = document.getElementById('id_clave');
    const descripcionInput = document.getElementById('id_descripcion');
    const esAntibiotico = document.getElementById('id_es_antibiotico');
    const datosAntibiotico = document.getElementById('datos-antibiotico');
    const codigoAtc = document.getElementById('id_codigo_atc');
    const categoriaAware = document.getElementById('id_categoria_aware');
    const valorAtc = document.getElementById('id_valor_atc');
    const estadoCatalogo = document.getElementById('estado-catalogo');

    let consultaCatalogoPendiente = null;

    if (claveInput) {
        claveInput.addEventListener('input', function () {
            this.value = this.value.toUpperCase();
        });
    }

    if (codigoAtc) {
        codigoAtc.addEventListener('input', function () {
            this.value = this.value.toUpperCase();
        });

        codigoAtc.addEventListener('blur', consultarCatalogo);
    }

    if (esAntibiotico) {
        esAntibiotico.addEventListener('change', actualizarSeccionAntibiotico);
        actualizarSeccionAntibiotico();
    }

    if (form) {
        form.addEventListener('submit', function (event) {
            const errores = [];

            const clave = claveInput ? claveInput.value.trim() : '';
            const descripcion = descripcionInput
                ? descripcionInput.value.trim()
                : '';

            if (!clave) {
                errores.push('La clave del medicamento es obligatoria.');
            } else if (clave.length < 3) {
                errores.push(
                    'La clave debe tener al menos 3 caracteres.'
                );
            }

            if (!descripcion) {
                errores.push('La descripción es obligatoria.');
            } else if (descripcion.length < 5) {
                errores.push(
                    'La descripción debe tener al menos 5 caracteres.'
                );
            }

            if (esAntibiotico && esAntibiotico.checked) {
                const via = document.getElementById(
                    'id_via_administracion'
                );

                const gramos = document.getElementById(
                    'id_gramos_por_pieza'
                );

                if (!via || !via.value) {
                    errores.push(
                        'Selecciona la vía de administración.'
                    );
                }

                if (!codigoAtc || !codigoAtc.value.trim()) {
                    errores.push(
                        'Captura el código ATC del antibiótico.'
                    );
                }

                if (!gramos || gramos.value === '') {
                    errores.push(
                        'Captura los gramos por pieza.'
                    );
                }
            }

            if (errores.length > 0) {
                event.preventDefault();
                mostrarErrores(errores);
                return;
            }

            const boton = form.querySelector(
                'button[type="submit"]'
            );

            if (boton) {
                boton.disabled = true;
                boton.innerHTML =
                    '<i class="fas fa-spinner fa-spin"></i> Registrando...';
            }
        });
    }

    async function consultarCatalogo() {
        if (!esAntibiotico || !esAntibiotico.checked || !codigoAtc) {
            return;
        }

        const codigo = codigoAtc.value.trim().toUpperCase();

        if (!codigo) {
            actualizarEstadoCatalogo('', '');
            return;
        }

        if (consultaCatalogoPendiente) {
            consultaCatalogoPendiente.abort();
        }

        consultaCatalogoPendiente = new AbortController();

        actualizarEstadoCatalogo(
            'Consultando catálogo...',
            'loading'
        );

        try {
            const url = `/api/catalogo-antibioticos/buscar/?codigo_atc=${encodeURIComponent(codigo)}`;

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                signal: consultaCatalogoPendiente.signal
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error || 'No fue posible consultar el catálogo.'
                );
            }

            if (!data.encontrado) {
                actualizarEstadoCatalogo(
                    'Código no encontrado. Captura los valores manualmente.',
                    'warning'
                );
                return;
            }

            if (categoriaAware && data.categoria_aware) {
                categoriaAware.value = data.categoria_aware;
            }

            if (
                valorAtc &&
                data.valor_atc !== null &&
                data.valor_atc !== undefined
            ) {
                valorAtc.value = data.valor_atc;
            }

            actualizarEstadoCatalogo(
                'Datos encontrados en el catálogo.',
                'success'
            );
        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }

            actualizarEstadoCatalogo(
                'No se pudo consultar el catálogo.',
                'error'
            );
        }
    }

    function actualizarSeccionAntibiotico() {
        if (!datosAntibiotico || !esAntibiotico) {
            return;
        }

        const visible = esAntibiotico.checked;

        datosAntibiotico.hidden = !visible;
        datosAntibiotico.classList.toggle('is-visible', visible);

        if (!visible) {
            limpiarCamposAntibiotico();
            return;
        }

        if (codigoAtc && codigoAtc.value.trim()) {
            consultarCatalogo();
        }
    }

    function limpiarCamposAntibiotico() {
        const campos = [
            'id_via_administracion',
            'id_codigo_atc',
            'id_categoria_aware',
            'id_gramos_por_pieza',
            'id_valor_atc'
        ];

        campos.forEach(function (id) {
            const campo = document.getElementById(id);

            if (campo) {
                campo.value = '';
            }
        });

        actualizarEstadoCatalogo('', '');
    }

    function actualizarEstadoCatalogo(texto, tipo) {
        if (!estadoCatalogo) {
            return;
        }

        estadoCatalogo.textContent = texto;
        estadoCatalogo.className = 'catalog-status';

        if (tipo) {
            estadoCatalogo.classList.add(`catalog-status-${tipo}`);
        }
    }
});

function limpiarFormulario() {
    const form = document.getElementById('form-medicamento');

    if (!form) {
        return;
    }

    form.reset();

    const datosAntibiotico = document.getElementById('datos-antibiotico');

    if (datosAntibiotico) {
        datosAntibiotico.hidden = true;
        datosAntibiotico.classList.remove('is-visible');
    }

    const estadoCatalogo = document.getElementById('estado-catalogo');

    if (estadoCatalogo) {
        estadoCatalogo.textContent = '';
        estadoCatalogo.className = 'catalog-status';
    }

    document
        .querySelectorAll('.alert-danger')
        .forEach(function (alerta) {
            alerta.remove();
        });

    const clave = document.getElementById('id_clave');

    if (clave) {
        clave.focus();
    }
}

function mostrarErrores(errores) {
    document
        .querySelectorAll('.alert-danger.js-alert')
        .forEach(function (alerta) {
            alerta.remove();
        });

    const alerta = document.createElement('div');

    alerta.className = 'alert alert-danger js-alert';

    alerta.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <div>${errores.join('<br>')}</div>
    `;

    const formulario = document.getElementById('form-medicamento');

    if (formulario) {
        formulario.prepend(alerta);
        alerta.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
    }
}