(function () {
    'use strict';

    const datosNode = document.getElementById('datos-grafica-aware');
    const canvas = document.getElementById('grafica-aware');
    const selector = document.getElementById('tipo-grafica-aware');
    const estadoVacio = document.getElementById('grafica-aware-vacia');

    if (!datosNode || !canvas || !selector) return;

    let datos;
    try {
        datos = JSON.parse(datosNode.textContent);
    } catch (error) {
        console.error('No fue posible leer los datos AWaRe.', error);
        return;
    }

    const sumatorias = datos.sumatorias.map(Number);
    const porcentajes = datos.porcentajes.map(Number);
    const sinDatos = sumatorias.every(valor => valor === 0);

    if (sinDatos) {
        canvas.hidden = true;
        estadoVacio.hidden = false;
        selector.disabled = true;
        return;
    }

    if (typeof Chart === 'undefined') {
        canvas.hidden = true;
        estadoVacio.hidden = false;
        estadoVacio.querySelector('span').textContent =
            'No fue posible cargar la gráfica. La tabla conserva los datos calculados.';
        return;
    }

    const colores = ['#315b20', '#ffb700', '#9b0000'];
    let grafica;

    function crearGrafica(tipo) {
        if (grafica) grafica.destroy();

        const esBarras = tipo === 'bar';
        grafica = new Chart(canvas, {
            type: tipo,
            data: {
                labels: datos.etiquetas,
                datasets: [{
                    label: 'Porcentaje del total DDD/ATC',
                    data: porcentajes,
                    backgroundColor: colores,
                    borderColor: esBarras ? colores : '#ffffff',
                    borderWidth: esBarras ? 1 : 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: !esBarras,
                        position: 'right',
                    },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                const indice = context.dataIndex;
                                return ` ${datos.etiquetas[indice]}: ${sumatorias[indice].toLocaleString('es-MX', {
                                    maximumFractionDigits: 4,
                                })} DDD (${porcentajes[indice].toFixed(2)}%)`;
                            },
                        },
                    },
                },
                scales: esBarras ? {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: valor => `${valor}%`,
                        },
                        title: {
                            display: true,
                            text: 'Porcentaje del total DDD/ATC',
                        },
                    },
                } : {},
            },
        });
    }

    crearGrafica(selector.value);
    selector.addEventListener('change', () => crearGrafica(selector.value));
}());
