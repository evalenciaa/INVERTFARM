// ===== VARIABLES GLOBALES =====
let currentPage = 1;
const itemsPerPage = 10;
let salidasData = [];
let charts = {};

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeEventListeners();
    setDefaultDates();

    const fechaInicio = document.getElementById('fechaInicio')?.value || '';
    const fechaFin = document.getElementById('fechaFin')?.value || '';
    loadData(fechaInicio, fechaFin);
});


// ===== CARGAR DATOS =====

async function loadData(fechaInicio = '', fechaFin = '') {
    try {
        const params = new URLSearchParams();
        if (fechaInicio) params.append('fecha_inicio', fechaInicio);
        if (fechaFin) params.append('fecha_fin', fechaFin);

        const query = params.toString() ? `?${params.toString()}` : '';

        const responseKPIs = await fetch(`/api/reportes/kpis/${query}`);
        const dataKPIs = await responseKPIs.json();

        if (dataKPIs.success) {
            const kpis = dataKPIs.kpis;
            animateValue('totalSalidas', 0, kpis.total_salidas, 1500);
            animateValue('totalMedicamentos', 0, kpis.total_medicamentos, 1500);
            animateValue('totalPacientes', 0, kpis.total_pacientes, 1500);
            animateValue('valorTotal', 0, kpis.valor_total, 1500, true);
            animateValue('totalInstituciones', 0, kpis.total_instituciones, 1500);
        }

        const responseSalidas = await fetch(`/api/reportes/salidas/${query}`);
        const dataSalidas = await responseSalidas.json();

        if (dataSalidas.success) {
            salidasData = dataSalidas.data;
            currentPage = 1;

            const activeTab = getActiveTab();
            loadTabContent(activeTab);
        }

    } catch (error) {
        console.error('Error cargando datos:', error);
        showNotification('Error al cargar los datos', 'error');
    }
}

function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // Remover clase active de todos
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Activar tab seleccionado
            button.classList.add('active');
            document.getElementById(`tab-${tabId}`).classList.add('active');
            
            // Cargar contenido del tab
            loadTabContent(tabId);
        });
    });
}

// ===== GENERAR DATOS SIMULADOS =====
function generateMockData() {
    const medicamentos = [
        'Paracetamol 500mg', 'Ibuprofeno 400mg', 'Amoxicilina 500mg',
        'Omeprazol 20mg', 'Losartán 50mg', 'Metformina 850mg',
        'Atorvastatina 20mg', 'Salbutamol Inhalador', 'Diclofenaco Gel',
        'Ranitidina 150mg', 'Captopril 25mg', 'Clonazepam 2mg'
    ];
    
    const pacientes = [
        'Juan Pérez García', 'María López Martínez', 'Carlos Rodríguez Sánchez',
        'Ana González Fernández', 'Luis Hernández Torres', 'Carmen Díaz Ruiz',
        'José Martín Gómez', 'Isabel Jiménez Moreno', 'Francisco Álvarez Castro',
        'Laura Romero Ortiz'
    ];
    
    const responsables = [
        'Dr. Roberto Méndez', 'Dra. Patricia Flores', 'Enf. Miguel Ángel Ruiz',
        'Dra. Sofía Ramírez'
    ];
    
    const data = [];
    const today = new Date();
    
    for (let i = 0; i < 150; i++) {
        const fecha = new Date(today);
        fecha.setDate(fecha.getDate() - Math.floor(Math.random() * 90));
        
        data.push({
            id: 1000 + i,
            fecha: fecha.toISOString().split('T')[0],
            hora: `${String(Math.floor(Math.random() * 12) + 8).padStart(2, '0')}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
            medicamento: medicamentos[Math.floor(Math.random() * medicamentos.length)],
            cantidad: Math.floor(Math.random() * 10) + 1,
            paciente: pacientes[Math.floor(Math.random() * pacientes.length)],
            responsable: responsables[Math.floor(Math.random() * responsables.length)],
            valor: Math.floor(Math.random() * 500) + 50
        });
    }
    
    return data.sort((a, b) => new Date(b.fecha) - new Date(a.fecha));
}

// ===== ACTUALIZAR KPIs =====
function updateKPIs() {
    const totalSalidas = salidasData.length;
    const totalMedicamentos = salidasData.reduce((sum, item) => sum + item.cantidad, 0);
    const pacientesUnicos = new Set(salidasData.map(item => item.paciente)).size;
    const valorTotal = salidasData.reduce((sum, item) => sum + item.valor, 0);
    
    animateValue('totalSalidas', 0, totalSalidas, 1500);
    animateValue('totalMedicamentos', 0, totalMedicamentos, 1500);
    animateValue('totalPacientes', 0, pacientesUnicos, 1500);
    animateValue('valorTotal', 0, valorTotal, 1500, true);
}

// ===== ANIMACIÓN DE NÚMEROS =====
function animateValue(id, start, end, duration, isCurrency = false) {
    const element = document.getElementById(id);
    const range = end - start;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const current = Math.floor(start + (range * progress));
        
        if (isCurrency) {
            element.textContent = `$${current.toLocaleString()}`;
        } else {
            element.textContent = current.toLocaleString();
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ===== CARGAR CONTENIDO POR TAB =====
function loadTabContent(tabId) {
    switch(tabId) {
        case 'historial':
            loadHistorialTable();
            break;
        case 'medicamentos':
            loadMedicamentosCharts();
            break;
        case 'pacientes':
            loadPacientesCharts();
            break;
        case 'tendencias':
            loadTendenciasCharts();
            break;
        case 'lento-movimiento':
            loadLentoMovimientoTable();
            break;
    }
}

// ===== TAB 1: HISTORIAL DE SALIDAS =====
function loadHistorialTable(filteredData = null) {
    const data = filteredData || salidasData;
    const tbody = document.getElementById('tableSalidasBody');
    
    // Paginación
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = data.slice(startIndex, endIndex);
    
    // Generar HTML
    tbody.innerHTML = pageData.map(item => `
        <tr>
            <td><strong>#${item.id}</strong></td>
            <td>${formatDate(item.fecha)}</td>
            <td>${item.clave || 'N/A'}</td>
            <td><strong>${item.medicamento}</strong></td>
            <td>${item.lote || 'N/A'}</td>
            <td>${item.caducidad && item.caducidad !== 'N/A' ? formatDate(item.caducidad) : 'N/A'}</td>
            <td><span class="badge badge-success">${item.cantidad} unidades</span></td>
            <td>${item.tipo === 'Transferencia' ? item.destino : item.paciente}</td>
            <td>${item.responsable}</td>
            <td><span class="badge ${item.tipo_badge}">${item.tipo}</span></td>
            <td><strong>$${Number(item.valor || 0).toLocaleString()}</strong></td>
            <td>
                <button class="btn-action" onclick="verDetalle('${item.pdf_url || ''}')" title="Ver comprobante">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        </tr>
    `).join('');
    
    // Actualizar paginación
    updatePagination(data.length);
}

// ===== TAB 2: MEDICAMENTOS MÁS DISPENSADOS =====
function loadMedicamentosCharts() {
  // Calcular top medicamentos
  const medicamentosCounts = {};
  salidasData.forEach(item => {
    medicamentosCounts[item.medicamento] = (medicamentosCounts[item.medicamento] || 0) + item.cantidad;
  });

  const topMedicamentos = Object.entries(medicamentosCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  // Destruir gráfica anterior si existe
  if (charts.medicamentos) {
    charts.medicamentos.destroy();
  }

  const coloresRanking = [
    '#d4af37', // oro
    '#c0c0c0', // plata
    '#cd7f32', // bronce
    'rgba(117,0,0,0.85)',
    'rgba(117,0,0,0.75)',
    'rgba(117,0,0,0.65)',
    'rgba(117,0,0,0.55)',
    'rgba(117,0,0,0.45)',
    'rgba(117,0,0,0.35)',
    'rgba(117,0,0,0.25)'
  ];

  const selector = document.getElementById('chartTypeMed');
  const tipoInicial = selector?.value || 'bar';

  const buildData = () => ({
    labels: topMedicamentos.map(i => i[0]),
    datasets: [{
      label: 'Unidades Dispensadas',
      data: topMedicamentos.map(i => i[1]),
      backgroundColor: coloresRanking.slice(0, topMedicamentos.length),
      borderColor: coloresRanking.slice(0, topMedicamentos.length),
      borderWidth: 1,
      borderRadius: 8
    }]
  });

  const buildOptions = (tipoSeleccionado) => {
    const isHorizontal = (tipoSeleccionado === 'barHorizontal');
    const isPieLike = (tipoSeleccionado === 'pie' || tipoSeleccionado === 'doughnut');

    // Opciones base
    const opts = {
        responsive: true,
        maintainAspectRatio: false,
        devicePixelRatio: 3,   // <-- clave para que el canvas salga HD
        plugins: {
            legend: { display: false },
            title: { display: false }
        }
    };


    // Pie / doughnut no usan scales
    if (isPieLike) return opts;

    // Barras (vertical u horizontal)
    opts.indexAxis = isHorizontal ? 'y' : 'x';
    opts.scales = {
      // En horizontal: X = valores, Y = categorías
      // En vertical:   Y = valores, X = categorías
      x: isHorizontal
        ? { beginAtZero: true, ticks: { font: { size: 12, weight: 'bold' } } }
        : { ticks: { font: { size: 11 }, maxRotation: 45, minRotation: 45 } },

      y: isHorizontal
        ? { ticks: { font: { size: 11 } } }
        : { beginAtZero: true, ticks: { font: { size: 12, weight: 'bold' } } }
    };

    return opts;
  };

  const getChartType = (tipoSeleccionado) => {
    // Chart.js v4: horizontalBar NO existe; es bar + indexAxis:'y'
    if (tipoSeleccionado === 'barHorizontal') return 'bar';
    return tipoSeleccionado; // 'bar' | 'pie' | 'doughnut'
  };

  // Crear gráfica
  const ctx = document.getElementById('chartMedicamentos').getContext('2d');
  charts.medicamentos = new Chart(ctx, {
    type: getChartType(tipoInicial),
    data: buildData(),
    options: buildOptions(tipoInicial)
  });

  // Generar ranking
  loadRankingMedicamentos(topMedicamentos);

  // Cambio de tipo (sin duplicar listeners)
  if (selector) {
    selector.onchange = function () {
      const tipo = this.value;

      charts.medicamentos.config.type = getChartType(tipo);
      charts.medicamentos.options = buildOptions(tipo);

      charts.medicamentos.update();
    };
  }
}

// ===== RANKING DE MEDICAMENTOS =====
function loadRankingMedicamentos(topMedicamentos) {
    const rankingContainer = document.getElementById('rankingMedicamentos');
    
    rankingContainer.innerHTML = topMedicamentos.map((item, index) => {
        let rankClass = 'default';
        if (index === 0) rankClass = 'gold';
        else if (index === 1) rankClass = 'silver';
        else if (index === 2) rankClass = 'bronze';
        
        return `
            <div class="ranking-item">
                <div class="ranking-number ${rankClass}">${index + 1}</div>
                <div class="ranking-info">
                    <div class="ranking-name">${item[0]}</div>
                    <div class="ranking-detail">${item[1]} unidades dispensadas</div>
                </div>
                <div class="ranking-value">${item[1]}</div>
            </div>
        `;
    }).join('');
}

// ===== TAB 3: PACIENTES FRECUENTES =====
function loadPacientesCharts() {
    // Calcular top pacientes
    const pacientesCounts = {};
    const pacientesValor = {};
    const pacientesUltimaVisita = {};
    
    salidasData.forEach(item => {
        pacientesCounts[item.paciente] = (pacientesCounts[item.paciente] || 0) + 1;
        pacientesValor[item.paciente] = (pacientesValor[item.paciente] || 0) + item.valor;
        
        if (!pacientesUltimaVisita[item.paciente] || new Date(item.fecha) > new Date(pacientesUltimaVisita[item.paciente])) {
            pacientesUltimaVisita[item.paciente] = item.fecha;
        }
    });
    
    const topPacientes = Object.entries(pacientesCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
    // Destruir gráfica anterior
    if (charts.pacientes) {
        charts.pacientes.destroy();
    }
    
    // Crear gráfica de dona
    const ctx = document.getElementById('chartPacientes').getContext('2d');
    charts.pacientes = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: topPacientes.map(item => item[0]),
            datasets: [{
                data: topPacientes.map(item => item[1]),
                backgroundColor: [
                    '#667eea', '#764ba2', '#f093fb', '#f5576c',
                    '#4facfe', '#00f2fe', '#fa709a', '#fee140',
                    '#30cfd0', '#330867'
                ],
                borderWidth: 3,
                borderColor: 'white'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            devicePixelRatio: 3,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        font: {
                            size: 11
                        },
                        padding: 15
                    }
                }
            }
        }
    });
    
    // Cargar tabla de pacientes
    loadPacientesTable(topPacientes, pacientesCounts, pacientesValor, pacientesUltimaVisita);
}

// ===== TABLA DE PACIENTES =====
function loadPacientesTable(topPacientes, counts, valores, ultimaVisita) {
    const tbody = document.getElementById('tablePacientesBody');
    
    tbody.innerHTML = topPacientes.map((item, index) => `
        <tr>
            <td><strong>${index + 1}</strong></td>
            <td>${item[0]}</td>
            <td><span class="badge badge-success">${item[1]} visitas</span></td>
            <td>${counts[item[0]]} medicamentos</td>
            <td>${formatDate(ultimaVisita[item[0]])}</td>
            <td><strong>$${valores[item[0]].toLocaleString()}</strong></td>
        </tr>
    `).join('');
}

// ===== TAB 4: TENDENCIAS TEMPORALES =====
function loadTendenciasCharts() {
    // Gráfica de tendencias mensuales
    loadTendenciasMensuales();
    
    // Gráfica de días de la semana
    loadDistribucionDias();
    
    // Gráfica de horas pico
    loadHorasPico();
}

// ===== TENDENCIAS MENSUALES =====
function loadTendenciasMensuales() {
    const mesesLabels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    const mesesData = new Array(12).fill(0);
    
    salidasData.forEach(item => {
        const mes = new Date(item.fecha).getMonth();
        mesesData[mes]++;
    });
    
    if (charts.tendencias) {
        charts.tendencias.destroy();
    }
    
    const ctx = document.getElementById('chartTendencias').getContext('2d');
    charts.tendencias = new Chart(ctx, {
        type: 'line',
        data: {
            labels: mesesLabels,
            datasets: [{
                label: 'Salidas de Medicamentos',
                data: mesesData,
                borderColor: '#750000',
                backgroundColor: 'rgba(117, 0, 0, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 3,
                pointRadius: 6,
                pointBackgroundColor: '#750000',
                pointBorderColor: 'white',
                pointBorderWidth: 2,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            devicePixelRatio: 3,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    }
                }
            }
        }
    });
}

// ===== DISTRIBUCIÓN POR DÍAS =====
function loadDistribucionDias() {
    const diasLabels = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
    const diasData = new Array(7).fill(0);
    
    salidasData.forEach(item => {
        const dia = new Date(item.fecha).getDay();
        const diaIndex = dia === 0 ? 6 : dia - 1; // Ajustar domingo
        diasData[diaIndex]++;
    });
    
    if (charts.diasSemana) {
        charts.diasSemana.destroy();
    }
    
    const ctx = document.getElementById('chartDiasSemana').getContext('2d');
    charts.diasSemana = new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: diasLabels,
            datasets: [{
                data: diasData,
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(118, 75, 162, 0.8)',
                    'rgba(240, 147, 251, 0.8)',
                    'rgba(245, 87, 108, 0.8)',
                    'rgba(79, 172, 254, 0.8)',
                    'rgba(0, 242, 254, 0.8)',
                    'rgba(250, 112, 154, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            devicePixelRatio: 3,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// ===== HORAS PICO =====
function loadHorasPico() {
    const horasData = new Array(12).fill(0); // 8 AM a 8 PM
    const horasLabels = [];
    
    for (let i = 8; i <= 19; i++) {
        horasLabels.push(`${i}:00`);
    }
    
    salidasData.forEach(item => {
        const hora = parseInt(item.hora.split(':')[0]);
        if (hora >= 8 && hora <= 19) {
            horasData[hora - 8]++;
        }
    });
    
    if (charts.horas) {
        charts.horas.destroy();
    }
    
    const ctx = document.getElementById('chartHoras').getContext('2d');
    charts.horas = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: horasLabels,
            datasets: [{
                label: 'Dispensaciones por Hora',
                data: horasData,
                backgroundColor: 'rgba(79, 172, 254, 0.8)',
                borderColor: 'rgba(79, 172, 254, 1)',
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            devicePixelRatio: 3,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// ===== TAB 5: MEDICAMENTOS DE LENTO MOVIMIENTO =====
async function loadLentoMovimientoTable() {
    try {
        const fechaInicio = document.getElementById('fechaInicio')?.value || '';
        const fechaFin = document.getElementById('fechaFin')?.value || '';

        const params = new URLSearchParams();
        if (fechaInicio) params.append('fecha_inicio', fechaInicio);
        if (fechaFin) params.append('fecha_fin', fechaFin);

        const query = params.toString() ? `?${params.toString()}` : '';
        const response = await fetch(`/api/medicamentos-lento-movimiento/${query}`);
        const data = await response.json();

        const tbody = document.getElementById('tableLentoMovimientoBody');
        const totalEl = document.getElementById('totalLentoMovimiento');

        if (data.success && data.data.length > 0) {
            tbody.innerHTML = data.data.map(item => `
                <tr>
                    <td>${item.clave}</td>
                    <td>${item.descripcion}</td>
                    <td>${item.lote}</td>
                    <td>${item.caducidad}</td>
                    <td>${item.salidas}</td>
                    <td>${item.existencia_actual}</td>
                </tr>
            `).join('');
            totalEl.textContent = `${data.total} lotes`;
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align:center;">
                        No se encontraron medicamentos de lento movimiento en el periodo.
                    </td>
                </tr>
            `;
            totalEl.textContent = '0 lotes';
        }
    } catch (error) {
        console.error('Error cargando lento movimiento:', error);
        showNotification('Error al cargar medicamentos de lento movimiento', 'error');
    }
}

// ===== PAGINACIÓN =====
function updatePagination(totalItems) {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    document.getElementById('currentPage').textContent = currentPage;
    document.getElementById('totalPages').textContent = totalPages;
    
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages;
}

function getActiveTab() {
    const activeBtn = document.querySelector('.tab-btn.active');
    return activeBtn ? activeBtn.getAttribute('data-tab') : 'historial';
}

function safeGetCanvasImage(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  if (canvas.width === 0 || canvas.height === 0) return null;

  try {
    // Chart.js v3/v4: obtener instancia y exportar directo (mejor calidad)
    const chart = (window.Chart && window.Chart.getChart) ? window.Chart.getChart(canvas) : null;
    if (chart && typeof chart.toBase64Image === 'function') {
      return chart.toBase64Image('image/png', 1.0);
    }

    // Fallback: lo que ya tenías (por si no encuentra el chart)
    return canvas.toDataURL('image/png', 1.0);
  } catch (e) {
    console.warn('No se pudo capturar canvas', canvasId, e);
    return null;
  }
}


function addCanvasToPDF(doc, canvasId, x, y, w, h) {
  const imgData = safeGetCanvasImage(canvasId);
  if (!imgData) return false;
  doc.addImage(imgData, 'PNG', x, y, w, h);
  return true;
}

function getJsPDF() {
  // jsPDF UMD expone: window.jspdf.jsPDF
  if (window.jspdf && window.jspdf.jsPDF) return window.jspdf.jsPDF;

  // fallback (por si algún día cambias el build)
  if (window.jsPDF) return window.jsPDF;

  throw new Error('jsPDF no está cargado (window.jspdf.jsPDF no existe).');
}

async function elementToPngBase64(elementId) {
  const element = document.getElementById(elementId);
  if (!element) return null;

  if (typeof html2canvas === 'undefined') {
    console.warn('html2canvas no está cargado. Agrega: <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>');
    return null;
  }

  try {
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#FFFFFF'
    });

    return canvas.toDataURL('image/png', 1.0);
  } catch (e) {
    console.warn('Error capturando tabla:', e);
    return null;
  }
}




// ===== EVENT LISTENERS =====
function initializeEventListeners() {
    // Paginación
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadHistorialTable();
        }
    });
    
    document.getElementById('nextPage').addEventListener('click', () => {
        const totalPages = Math.ceil(salidasData.length / itemsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            loadHistorialTable();
        }
    });
    
    // Filtros
    document.getElementById('filtrarFechas').addEventListener('click', filtrarPorFechas);

    const btnExportarSinMovimiento = document.getElementById('btnExportarSinMovimiento');
    if (btnExportarSinMovimiento) {
        btnExportarSinMovimiento.addEventListener('click', abrirModalExportarSinMovimiento);
    }

    const btnExportarLentoMovimiento = document.getElementById('btnExportarLentoMovimiento');
    if (btnExportarLentoMovimiento) {
        btnExportarLentoMovimiento.addEventListener('click', abrirModalExportarLentoMovimiento);
    }
    
    // Botón Exportar PDF
    document.getElementById('exportPDF').addEventListener('click', async function() {
        const activeTab = getActiveTab();
        
        try {
            switch(activeTab) {
                case 'historial':
                    await exportarHistorialPDF();
                    break;
                case 'medicamentos':
                    await exportarMedicamentosPDF();
                    break;
                case 'pacientes':
                    await exportarPacientesPDF();
                    break;
                case 'tendencias':
                    await exportarTendenciasPDF();
                    break;
                default:
                    alert('Vista no disponible para exportar');
            }
        } catch (error) {
            console.error('Error al exportar PDF:', error);
            alert('Error al generar el PDF');
        }
    });


    // Botón Exportar Excel
    document.getElementById('exportExcel').addEventListener('click', async function() {
        const activeTab = getActiveTab();
        
        try {
            switch(activeTab) {
                case 'historial':
                    await exportarHistorialExcel();
                    break;
                case 'medicamentos':
                    await exportarMedicamentosExcel();
                    break;
                case 'pacientes':
                    await exportarPacientesExcel();
                    break;
                case 'tendencias':
                    await exportarTendenciasExcel();
                    break;
                default:
                    alert('Vista no disponible para exportar');
            }
        } catch (error) {
            console.error('Error al exportar Excel:', error);
            alert('Error al generar el Excel');
        }
    });

    // Actualizar
    document.getElementById('refreshData').addEventListener('click', () => {
        location.reload();
    });
}

// ===== FILTRAR POR FECHAS =====
async function filtrarPorFechas() {
    const fechaInicio = document.getElementById('fechaInicio').value;
    const fechaFin = document.getElementById('fechaFin').value;

    if (!fechaInicio || !fechaFin) {
        showNotification('Por favor selecciona ambas fechas', 'warning');
        return;
    }

    await loadData(fechaInicio, fechaFin);
    showNotification('Reporte filtrado correctamente', 'success');
}

// ===== EXPORTAR A PDF =====
function exportToPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    // Título
    doc.setFontSize(18);
    doc.text('Reporte de Salidas - INVENTFARM', 14, 20);
    
    doc.setFontSize(11);
    doc.text(`Fecha de generación: ${new Date().toLocaleDateString()}`, 14, 28);
    
    // Tabla
    doc.autoTable({
        startY: 35,
        head: [['ID', 'Fecha', 'Medicamento', 'Cantidad', 'Paciente', 'Valor']],
        body: salidasData.map(item => [
            item.id,
            formatDate(item.fecha),
            item.medicamento,
            item.cantidad,
            item.paciente,
            `$${item.valor}`
        ]),
        theme: 'striped',
        headStyles: { fillColor: [117, 0, 0] }
    });
    
    doc.save('reporte-salidas.pdf');
    showNotification('PDF exportado correctamente', 'success');
}

// ===== EXPORTAR A EXCEL =====
function exportToExcel() {
    const ws = XLSX.utils.json_to_sheet(salidasData.map(item => ({
        'ID': item.id,
        'Fecha': item.fecha,
        'Hora': item.hora,
        'Medicamento': item.medicamento,
        'Cantidad': item.cantidad,
        'Paciente': item.paciente,
        'Responsable': item.responsable,
        'Valor': item.valor
    })));
    
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Salidas');
    
    XLSX.writeFile(wb, 'reporte-salidas.xlsx');
    showNotification('Excel exportado correctamente', 'success');
}

// ===== MODAL EXPORTAR SIN MOVIMIENTO =====
function abrirModalExportarSinMovimiento() {
    document.getElementById('modal-overlay-sin-movimiento').style.display = 'block';
    document.getElementById('modal-exportar-sin-movimiento').style.display = 'flex';
}

function cerrarModalExportarSinMovimiento() {
    document.getElementById('modal-overlay-sin-movimiento').style.display = 'none';
    document.getElementById('modal-exportar-sin-movimiento').style.display = 'none';
}

function descargarSinMovimientoExcel() {
    const fechaInicio = document.getElementById('fechaInicio')?.value || '';
    const fechaFin = document.getElementById('fechaFin')?.value || '';

    const params = new URLSearchParams();
    if (fechaInicio) params.append('fecha_inicio', fechaInicio);
    if (fechaFin) params.append('fecha_fin', fechaFin);

    const url = `/reportes/medicamentos-sin-movimiento/excel/?${params.toString()}`;
    window.open(url, '_blank');
    cerrarModalExportarSinMovimiento();
}

function descargarSinMovimientoPDF() {
    const fechaInicio = document.getElementById('fechaInicio')?.value || '';
    const fechaFin = document.getElementById('fechaFin')?.value || '';

    const params = new URLSearchParams();
    if (fechaInicio) params.append('fecha_inicio', fechaInicio);
    if (fechaFin) params.append('fecha_fin', fechaFin);

    const url = `/reportes/medicamentos-sin-movimiento/pdf/?${params.toString()}`;
    window.open(url, '_blank');
    cerrarModalExportarSinMovimiento();
}

// ===== MODAL EXPORTAR LENTO MOVIMIENTO =====
function abrirModalExportarLentoMovimiento() {
    document.getElementById('modal-overlay-lento-movimiento').style.display = 'block';
    document.getElementById('modal-exportar-lento-movimiento').style.display = 'flex';
}

function cerrarModalExportarLentoMovimiento() {
    document.getElementById('modal-overlay-lento-movimiento').style.display = 'none';
    document.getElementById('modal-exportar-lento-movimiento').style.display = 'none';
}

function descargarLentoMovimientoExcel() {
    const fechaInicio = document.getElementById('fechaInicio')?.value || '';
    const fechaFin = document.getElementById('fechaFin')?.value || '';

    const params = new URLSearchParams();
    if (fechaInicio) params.append('fecha_inicio', fechaInicio);
    if (fechaFin) params.append('fecha_fin', fechaFin);

    const url = `/reportes/medicamentos-lento-movimiento/excel/?${params.toString()}`;
    window.open(url, '_blank');
    cerrarModalExportarLentoMovimiento();
}

function descargarLentoMovimientoPDF() {
    const fechaInicio = document.getElementById('fechaInicio')?.value || '';
    const fechaFin = document.getElementById('fechaFin')?.value || '';

    const params = new URLSearchParams();
    if (fechaInicio) params.append('fecha_inicio', fechaInicio);
    if (fechaFin) params.append('fecha_fin', fechaFin);

    const url = `/reportes/medicamentos-lento-movimiento/pdf/?${params.toString()}`;
    window.open(url, '_blank');
    cerrarModalExportarLentoMovimiento();
}

// ===== UTILIDADES =====
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-MX', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

async function exportarHistorialPDF() {
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF('p', 'mm', 'letter');
      // Fuentes Unicode
      doc.addFileToVFS('DejaVuSans.ttf', window.DEJAVU_SANS_TTF_BASE64);
      doc.addFont('DejaVuSans.ttf', 'DejaVuSans', 'normal');

      doc.addFileToVFS('DejaVuSans-Bold.ttf', window.DEJAVU_SANS_BOLD_TTF_BASE64);
      doc.addFont('DejaVuSans-Bold.ttf', 'DejaVuSans', 'bold');


      const pageWidth = 215.9;
      const pageHeight = 279.4;
      const margin = 10;
      const availableWidth = pageWidth - (2 * margin);

      // Logo ancho completo (similar al reporte de salida)
      const logoUrl = '/static/farmacia/img/logo.jpg';
      doc.addImage(logoUrl, 'JPEG', margin, 8, availableWidth, 25);

      // Título
      doc.setFontSize(18);
      doc.setFont('DejaVuSans', 'bold');
      doc.text('Historial de Salidas', pageWidth / 2, 40, { align: 'center' });

      // Fecha
      doc.setFontSize(10);
      doc.setFont('DejaVuSans', 'normal');
      doc.text(`Generado: ${new Date().toLocaleString('es-MX')}`, pageWidth / 2, 47, { align: 'center' });

      // Línea
      doc.setLineWidth(0.5);
      doc.line(margin, 50, pageWidth - margin, 50);

      // Helpers (tipo Paragraph)
      const cleanText = (v) => {
        if (v === null || v === undefined) return '';
        return String(v)
            .replace(/\u00A0/g, ' ') // NBSP -> espacio normal
            .replace(/\s+/g, ' ')
            .trim();
        };

      const formatFechaYMD = (dateString) => {
            if (!dateString) return '';
            const d = new Date(dateString);
            if (isNaN(d.getTime())) return cleanText(dateString);
            // dd/mm/yyyy
            return d.toLocaleDateString('es-MX', { year: 'numeric', month: '2-digit', day: '2-digit' });
      };

      // Construir rows desde salidasData (todos los datos)
    const rows = salidasData
        .map(item => [
            formatFechaYMD(item.fecha),
            cleanText(item.clave),
            cleanText(item.medicamento),
            cleanText(item.lote),
            item.caducidad && item.caducidad !== 'N/A' ? formatFechaYMD(item.caducidad) : 'N/A',
            cleanText(item.cantidad),
            cleanText(item.tipo === 'Transferencia' ? (item.destino || 'N/A') : item.paciente),
            cleanText(item.responsable),
            (item.valor !== undefined && item.valor !== null) ? `$${Number(item.valor).toLocaleString('es-MX')}` : '$0'
        ]);
        doc.autoTable({
            startY: 55,
            margin: { left: margin, right: margin, top: 10, bottom: 10 },
            head: [['Fecha', 'Clave', 'Medicamento', 'Lote', 'Caducidad', 'Cant.', 'Paciente/Destino', 'Responsable', 'Valor']],
            body: rows,
            theme: 'grid',
            styles: {
                font: 'DejaVuSans',
                fontSize: 7,
                cellPadding: 2,
                overflow: 'linebreak',
                valign: 'top',
                halign: 'left',
                lineWidth: 0.2
            },
            headStyles: {
                font: 'DejaVuSans',
                fillColor: [139, 0, 0],
                textColor: [255, 255, 255],
                fontStyle: 'bold',
                fontSize: 7,
                halign: 'center',
                valign: 'middle',
                cellPadding: 2
            },
            columnStyles: {
                0: { cellWidth: 20, halign: 'center' },   // Fecha
                1: { cellWidth: 16, halign: 'center' },   // Clave
                2: { cellWidth: 46, halign: 'left' },     // Medicamento
                3: { cellWidth: 18, halign: 'center' },   // Lote
                4: { cellWidth: 18, halign: 'center' },   // Caducidad
                5: { cellWidth: 12, halign: 'center' },   // Cant.
                6: { cellWidth: 28, halign: 'left' },     // Paciente/Destino
                7: { cellWidth: 22.9, halign: 'left' },   // Responsable
                8: { cellWidth: 15, halign: 'right' }     // Valor
            },
            didParseCell: function (data) {
                if (data.section === 'head' && data.column.index === 5) {
                    data.cell.text = ['Cant.'];
                }
                if (data.section === 'body' && data.column.index === 2) {
                    data.cell.styles.valign = 'top';
                    data.cell.styles.fontSize = 6.7;
                }
            },
            alternateRowStyles: { fillColor: [248, 249, 250] },
            didDrawPage: function (data) {
                const pageCount = doc.internal.getNumberOfPages();
                doc.setFontSize(8);
                doc.setFont('DejaVuSans', 'normal');
                doc.text(`Página ${data.pageNumber} de ${pageCount}`, pageWidth / 2, pageHeight - 8, { align: 'center' });
            }
        });

      doc.save('Historial_Salidas.pdf');
}



async function exportarMedicamentosPDF() {
  const jsPDF = getJsPDF();
  const doc = new jsPDF('p', 'mm', 'letter');

  doc.addFileToVFS('DejaVuSans.ttf', window.DEJAVU_SANS_TTF_BASE64);
  doc.addFont('DejaVuSans.ttf', 'DejaVuSans', 'normal');

  doc.addFileToVFS('DejaVuSans-Bold.ttf', window.DEJAVU_SANS_BOLD_TTF_BASE64);
  doc.addFont('DejaVuSans-Bold.ttf', 'DejaVuSans', 'bold');

  const margin = 10;

  const cleanText = (v) => (v ?? '')
    .toString()
    .replace(/\u00A0/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  // Logo
  const logoUrl = window.STATIC_LOGO_URL;
  doc.addImage(logoUrl, 'JPEG', margin, 8, 195.9, 25);

  // Título
  doc.setFontSize(18);
  doc.setFont('DejaVuSans', 'bold');
  doc.text('Top 10 Medicamentos Más Dispensados', 105, 40, { align: 'center' });

  // Fecha
  doc.setFontSize(10);
  doc.setFont('DejaVuSans', 'normal');
  doc.text(`Generado: ${new Date().toLocaleString('es-MX')}`, 105, 47, { align: 'center' });

  // Línea
  doc.setLineWidth(0.5);
  doc.line(margin, 50, 200, 50);

  // Chart
  const okChart = addCanvasToPDF(doc, 'chartMedicamentos', margin, 55, 195.9, 80);

  // Rows
  const rows = [];
  const ranking = document.getElementById('rankingMedicamentos');

  if (ranking) {
    ranking.querySelectorAll('.ranking-item').forEach((item, index) => {
      const nombre = item.querySelector('.ranking-name')?.textContent || 'N/A';
      const cantidad = item.querySelector('.ranking-value')?.textContent || '0';
      rows.push([String(index + 1), cleanText(nombre), cleanText(cantidad)]);
    });
  }

  const startY = okChart ? 55 + 80 + 8 : 55;

    const pageWidth = doc.internal.pageSize.getWidth();  // 215.9
    const marginX = 10;
    const usableWidth = pageWidth - (marginX * 2);  // 195.9

    doc.autoTable({
    startY,
    margin: { left: marginX, right: marginX },
    head: [['#', 'Medicamento', 'Cantidad Dispensada']],
    body: rows,
    theme: 'grid',  // ← VUELVE AL GRID
    styles: {
        font: 'DejaVuSans',
        fontSize: 10,
        overflow: 'linebreak',
        valign: 'top',
        cellPadding: 2,
        // lineWidth: 0  ← QUITA ESTA LÍNEA, déjalo por defecto
    },
    headStyles: {
        font: 'DejaVuSans',
        fillColor: [139, 0, 0],
        textColor: [255, 255, 255],
        fontStyle: 'bold'
    },
    columnStyles: {
        0: { cellWidth: 12, halign: 'center' },
        1: { cellWidth: 136, halign: 'left', fontSize: 9 },  // ← 2mm menos, font 9
        2: { cellWidth: 47, halign: 'right' }
        }
    });

  doc.save('TopMedicamentos.pdf');
}


async function exportarPacientesPDF() {
  const jsPDF = getJsPDF();
  const doc = new jsPDF();

  // Logo - AMPLIAR: de 80x12 a 195.9x25 (como el anterior PDF)
  const logoUrl = window.STATIC_LOGO_URL;
  doc.addImage(logoUrl, 'JPEG', 10, 8, 195.9, 25);

  // Título
  doc.setFontSize(18);
  doc.text('Pacientes Frecuentes', 14, 40);

  // Fecha
  doc.setFontSize(10);
  doc.text(`Generado: ${new Date().toLocaleString('es-MX')}`, 14, 47);

  // Línea
  doc.setLineWidth(0.5);
  doc.line(10, 52, 200, 52);

  // 1) CHART (dona) - MEJORAR CALIDAD: aumentar tamaño + `devicePixelRatio: 3`
  const okChart = addCanvasToPDF(doc, 'chartPacientes', 14, 56, 182, 85);

  // 2) TABLA (detalle)
  const rows = [];
  const tbody = document.getElementById('tablePacientesBody');

  if (tbody) {
    tbody.querySelectorAll('tr').forEach(row => {
      const cells = row.querySelectorAll('td');
      if (cells.length === 6) {
        rows.push([
          cells[0].textContent.trim(),
          cells[1].textContent.trim(),
          cells[2].textContent.trim(),
          cells[3].textContent.trim(),
          cells[4].textContent.trim(),
          cells[5].textContent.trim()
        ]);
      }
    });
  }

  const startY = okChart ? 56 + 85 + 8 : 56;

  doc.autoTable({
    startY,
    head: [['#', 'Paciente', 'Visitas', 'Medicamentos', 'Última Visita', 'Gasto']],
    body: rows,
    theme: 'grid',
    styles: { fontSize: 9 },
    headStyles: { fillColor: [139, 0, 0] }
  });

  doc.save('PacientesFrecuentes.pdf');
}


async function exportarTendenciasPDF() {
  const jsPDF = getJsPDF();
  const doc = new jsPDF('landscape', 'mm', 'letter');

  const margin = 10;

  // Medidas hoja
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const usableW = pageW - margin * 2;

  // Logo banner
  const logoUrl = window.STATIC_LOGO_URL;
  doc.addImage(logoUrl, 'JPEG', margin, 8, usableW, 25);

  // Título / fecha / línea
  doc.setFontSize(18);
  doc.text('Tendencias Temporales', margin, 40);

  doc.setFontSize(10);
  doc.text(`Generado: ${new Date().toLocaleString('es-MX')}`, margin, 47);

  // (Opcional) rango del filtro
  const fi = document.getElementById('fechaInicio')?.value;
  const ff = document.getElementById('fechaFin')?.value;
  if (fi && ff) doc.text(`Rango: ${fi} a ${ff}`, margin, 52);

  doc.setLineWidth(0.5);
  doc.line(margin, 56, pageW - margin, 56);

  // Helper wrap con límite de líneas
  const drawParagraphLimited = (text, x, y, maxW, maxLines, lineH = 4) => {
    const lines = doc.splitTextToSize(text, maxW).slice(0, maxLines);
    doc.text(lines, x, y);
    return y + (lines.length * lineH);
  };

  // ===== ANCLAS (no se mueven) =====
  const chartTopY = 66;                 // chart grande fijo
  const chartTopH = 78;                 // un poco menos alto para dejar espacio abajo
  const bottomChartsY = 162;            // charts de abajo fijo
  const bottomChartH = 45;              // más bajo para que no choque con el borde
  const gapX = 5;
  const leftW = (usableW - gapX) / 2;

  // Texto contextual arriba del chart grande (máximo 2 líneas)
  doc.setFontSize(10);
  drawParagraphLimited(
    'La gráfica superior muestra el total de salidas por mes (conteo de registros). Abajo se muestran patrones por día de la semana y por hora para identificar días y horarios con mayor carga.',
    margin, 60, usableW, 2
  );

  // Chart grande
  addCanvasToPDF(doc, 'chartTendencias', margin, chartTopY, usableW, chartTopH);

  // Títulos + texto arriba de los charts de abajo (sin mover los charts)
  const bottomTitleY = bottomChartsY - 10;  // texto siempre encima
  doc.setFontSize(11);
  doc.text('Patrones de operación', margin, bottomTitleY);

  doc.setFontSize(9);
  drawParagraphLimited(
    'Distribución de salidas por día (Lun–Dom). Útil para ver qué días se atiende más.',
    margin, bottomTitleY + 4, leftW, 2
  );

  const rightX = margin + leftW + gapX;
  drawParagraphLimited(
    'Salidas por hora (8:00–19:00). Útil para detectar horas pico y planear personal.',
    rightX, bottomTitleY + 4, leftW, 2
  );

  // Charts de abajo (ANCLADOS)
  addCanvasToPDF(doc, 'chartDiasSemana', margin, bottomChartsY, leftW, bottomChartH);
  addCanvasToPDF(doc, 'chartHoras', rightX, bottomChartsY, leftW, bottomChartH);

  doc.save('TendenciasTemporales.pdf');
}



// ===== FUNCIONES DE EXPORTACIÓN EXCEL =====

async function canvasToPngBase64(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || canvas.width === 0 || canvas.height === 0) return null;

  // dataURL: "data:image/png;base64,...."
  return canvas.toDataURL('image/png', 1.0);
}

function downloadArrayBufferExcel(buffer, filename) {
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
}


async function exportarHistorialExcel() {
  const workbook = new ExcelJS.Workbook();

  // ===== HOJA 1: Tabla de datos (TODOS) =====
  const wsData = workbook.addWorksheet('Historial');

  const headerRow = wsData.addRow(['Fecha', 'Clave', 'Medicamento', 'Lote', 'Caducidad', 'Cantidad', 'Paciente/Destino', 'Responsable', 'Tipo de Salida', 'Precio']); 

  headerRow.font = { bold: true, color: { rgb: 'FFFFFF' }, size: 11 };
  headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { rgb: 'C00000' } };
  headerRow.alignment = { horizontal: 'center', vertical: 'center' };

    const allRows = salidasData
        .map(item => [
            String(item.fecha ?? ''),
            String(item.clave ?? 'N/A'),
            String(item.medicamento ?? ''),
            String(item.lote ?? 'N/A'),
            String(item.caducidad ?? 'N/A'),
            String(item.cantidad ?? ''),
            String(item.tipo === 'Transferencia' ? (item.destino ?? 'N/A') : (item.paciente ?? '')),
            String(item.responsable ?? ''),
            String(item.tipo ?? ''),
            String(item.valor ?? '')
        ]);

  allRows.forEach((r, idx) => {
    const newRow = wsData.addRow(r);

    if ((idx + 1) % 2 === 0) {
      newRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { rgb: 'F8F9FA' } };
    }
    newRow.alignment = { horizontal: 'left', vertical: 'center' };
  });

    wsData.columns = [
        { width: 14 },  // Fecha
        { width: 12 },  // Clave
        { width: 40 },  // Medicamento
        { width: 14 },  // Lote
        { width: 14 },  // Caducidad
        { width: 10 },  // Cantidad
        { width: 26 },  // Paciente/Destino
        { width: 24 },  // Responsable
        { width: 16 },  // Tipo de Salida
        { width: 12 }   // Precio
    ];

  const buffer = await workbook.xlsx.writeBuffer();
  downloadArrayBufferExcel(buffer, 'Historial_Salidas.xlsx');
}




async function exportarMedicamentosExcel() {
  const workbook = new ExcelJS.Workbook();

  // ===== HOJA 1: Chart (Gráfica) =====
  const wsChart = workbook.addWorksheet('Chart');
  wsChart.getCell('A1').value = 'Top 10 Medicamentos - Gráfica';
  wsChart.getCell('A1').font = { bold: true, size: 14 };

  const imgBase64 = await canvasToPngBase64('chartMedicamentos');
  if (imgBase64) {
    const imageId = workbook.addImage({ base64: imgBase64, extension: 'png' });
    wsChart.addImage(imageId, {
      tl: { col: 0, row: 2 },
      ext: { width: 900, height: 420 }
    });
  } else {
    wsChart.getCell('A3').value = 'No se pudo capturar la gráfica (canvas vacío).';
  }

  // ===== HOJA 2: Datos (Ranking) =====
  const wsData = workbook.addWorksheet('Top Medicamentos');

  // Header
  const headerRow = wsData.addRow(['#', 'Medicamento', 'Cantidad Dispensada']);
  headerRow.font = { bold: true, color: { rgb: 'FFFFFF' }, size: 11 };
  headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { rgb: 'C00000' } };
  headerRow.alignment = { horizontal: 'center', vertical: 'center' };

  // Calcular ranking desde salidasData (igual que en la gráfica)
  const medicamentosCounts = {};
  (salidasData || []).forEach(item => {
    medicamentosCounts[item.medicamento] = (medicamentosCounts[item.medicamento] || 0) + item.cantidad;
  });

  const topMedicamentos = Object.entries(medicamentosCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  // Agregar filas
  topMedicamentos.forEach((med, idx) => {
    const newRow = wsData.addRow([idx + 1, med[0], med[1]]);
    newRow.alignment = { horizontal: 'center', vertical: 'center' };
  });

  wsData.columns = [
    { width: 6 },
    { width: 70 },
    { width: 22 }
  ];

  const buffer = await workbook.xlsx.writeBuffer();
  downloadArrayBufferExcel(buffer, 'Top_Medicamentos.xlsx');
}



async function exportarPacientesExcel() {
  const workbook = new ExcelJS.Workbook();

  // ===== Hoja 1: Chart =====
  const wsChart = workbook.addWorksheet('Chart');
  wsChart.getCell('A1').value = 'Pacientes Frecuentes - Gráfica';
  wsChart.getCell('A1').font = { bold: true, size: 14 };

  const imgBase64 = await canvasToPngBase64('chartPacientes');
  if (imgBase64) {
    const imageId = workbook.addImage({ base64: imgBase64, extension: 'png' });
    wsChart.addImage(imageId, {
      tl: { col: 0, row: 2 },
      ext: { width: 900, height: 420 }
    });
  } else {
    wsChart.getCell('A3').value = 'No se pudo capturar la gráfica (canvas vacío).';
  }

  // ===== Hoja 2: Datos (TODOS) =====
  const wsData = workbook.addWorksheet('Pacientes');

  const headerRow = wsData.addRow([
    '#', 'Paciente', 'Total Visitas', 'Medicamentos', 'Última Visita', 'Gasto Total'
  ]);
  headerRow.font = { bold: true, color: { rgb: 'FFFFFF' }, size: 11 };
  headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { rgb: 'C00000' } };
  headerRow.alignment = { horizontal: 'center', vertical: 'center' };

  // Construir métricas desde salidasData (sin depender del DOM)
  const counts = {};              // visitas (salidas) por paciente
  const valores = {};             // gasto total
  const ultimaVisita = {};        // fecha última
  const medicamentosUnicos = {};  // Set de medicamentos por paciente

  (salidasData || []).forEach(item => {
    const p = item.paciente ?? '';
    if (!p) return;

    counts[p] = (counts[p] || 0) + 1;
    valores[p] = (valores[p] || 0) + Number(item.valor || 0);

    if (!medicamentosUnicos[p]) medicamentosUnicos[p] = new Set();
    if (item.medicamento) medicamentosUnicos[p].add(item.medicamento);

    const f = item.fecha ? new Date(item.fecha) : null;
    if (f && !isNaN(f.getTime())) {
      const prev = ultimaVisita[p] ? new Date(ultimaVisita[p]) : null;
      if (!prev || f > prev) ultimaVisita[p] = item.fecha;
    }
  });

  // TOP_N: null para exportar todos, o 10/50/etc.
  const TOP_N = null;

  let pacientesOrdenados = Object.entries(counts)
    .sort((a, b) => b[1] - a[1]); // por visitas desc

  if (TOP_N) pacientesOrdenados = pacientesOrdenados.slice(0, TOP_N);

  pacientesOrdenados.forEach(([paciente, totalVisitas], idx) => {
    wsData.addRow([
      idx + 1,
      paciente,
      totalVisitas,
      (medicamentosUnicos[paciente]?.size || 0),
      String(ultimaVisita[paciente] ?? ''),
      Number(valores[paciente] || 0)
    ]);
  });

  wsData.columns = [
    { width: 6 },
    { width: 40 },
    { width: 15 },
    { width: 15 },
    { width: 16 },
    { width: 16 }
  ];

  const buffer = await workbook.xlsx.writeBuffer();
  downloadArrayBufferExcel(buffer, 'Pacientes_Frecuentes.xlsx');
}



async function exportarTendenciasExcel() {
  const workbook = new ExcelJS.Workbook();

  const headerStyle = (cell) => {
    cell.font = { bold: true, color: { rgb: 'FFFFFF' }, size: 11 };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { rgb: 'C00000' } };
    cell.alignment = { horizontal: 'center', vertical: 'center' };
  };

  // ====== DATA desde salidasData (igual que tus charts) ======
  // 1) Mensual
  const mesesLabels = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']; // igual que UI [file:49]
  const mesesData = new Array(12).fill(0);
  (salidasData || []).forEach(item => {
    const d = item.fecha ? new Date(item.fecha) : null;
    if (!d || isNaN(d.getTime())) return;
    mesesData[d.getMonth()] += 1;
  });

  // 2) Días semana (Lun..Dom), con domingo al final (igual que UI) [file:49]
  const diasLabels = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  const diasData = new Array(7).fill(0);
  (salidasData || []).forEach(item => {
    const d = item.fecha ? new Date(item.fecha) : null;
    if (!d || isNaN(d.getTime())) return;
    const dia = d.getDay();              // 0=Dom..6=Sáb
    const idx = (dia === 0) ? 6 : dia-1; // mover domingo al final (igual que UI) [file:49]
    diasData[idx] += 1;
  });

  // 3) Horas pico (8:00–19:00), 12 slots (igual que UI) [file:49]
  const horasLabels = [];
  for (let i = 8; i <= 19; i++) horasLabels.push(`${i}:00`);
  const horasData = new Array(12).fill(0);
  (salidasData || []).forEach(item => {
    const hRaw = item.hora ? String(item.hora) : '';
    const hora = parseInt(hRaw.split(':')[0], 10);
    if (!Number.isFinite(hora)) return;
    if (hora >= 8 && hora <= 19) horasData[hora - 8] += 1;
  });

  // Helper para crear hoja con imagen + tabla
  const buildSheet = async ({ sheetName, title, canvasId, labels, values }) => {
    const ws = workbook.addWorksheet(sheetName);

    ws.getCell('A1').value = title;
    ws.getCell('A1').font = { bold: true, size: 14 };
    ws.getCell('A2').value = `Generado: ${new Date().toLocaleString('es-MX')}`;

    // Imagen
    const img = await canvasToPngBase64(canvasId);
    if (img) {
      const imageId = workbook.addImage({ base64: img, extension: 'png' });
      ws.addImage(imageId, { tl: { col: 0, row: 3 }, ext: { width: 980, height: 380 } });
    } else {
      ws.getCell('A4').value = 'No se pudo capturar la gráfica (canvas vacío).';
    }

    // Tabla de datos (debajo)
    const startRow = 24;
    const headerRow = ws.getRow(startRow);
    headerRow.getCell(1).value = 'Etiqueta';
    headerRow.getCell(2).value = 'Total';
    headerStyle(headerRow.getCell(1));
    headerStyle(headerRow.getCell(2));

    labels.forEach((lab, i) => {
      ws.getCell(`A${startRow + 1 + i}`).value = lab;
      ws.getCell(`B${startRow + 1 + i}`).value = values[i];
    });

    ws.columns = [{ width: 20 }, { width: 12 }];
  };

  // ====== 3 hojas ======
  await buildSheet({
    sheetName: 'Mensual',
    title: 'Tendencias Mensuales (Salidas por mes)',
    canvasId: 'chartTendencias',
    labels: mesesLabels,
    values: mesesData
  });

  await buildSheet({
    sheetName: 'Días',
    title: 'Distribución por Día (Lun–Dom)',
    canvasId: 'chartDiasSemana',
    labels: diasLabels,
    values: diasData
  });

  await buildSheet({
    sheetName: 'Horas',
    title: 'Horas Pico (8:00–19:00)',
    canvasId: 'chartHoras',
    labels: horasLabels,
    values: horasData
  });

  const buffer = await workbook.xlsx.writeBuffer();
  downloadArrayBufferExcel(buffer, 'Tendencias_Temporales.xlsx');
}



function setDefaultDates() {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    
    document.getElementById('fechaInicio').value = firstDay.toISOString().split('T')[0];
    document.getElementById('fechaFin').value = today.toISOString().split('T')[0];
}

function verDetalle(pdfUrl) {
    if (!pdfUrl) {
        alert('No hay comprobante disponible para esta salida.');
        return;
    }
    window.open(pdfUrl, '_blank');
}

function showNotification(message, type) {
    // Implementar sistema de notificaciones
    console.log(`${type.toUpperCase()}: ${message}`);
}


// ===== BOTONES DE ACCIÓN EN TABLA =====
const style = document.createElement('style');
style.textContent = `
    .btn-action {
        padding: 8px 12px;
        border: none;
        background: #750000;
        color: white;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 0.9rem;
    }
    
    .btn-action:hover {
        background: #a00000;
        transform: scale(1.1);
    }
`;
document.head.appendChild(style);
