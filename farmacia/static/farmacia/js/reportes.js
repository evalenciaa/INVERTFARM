// ===== VARIABLES GLOBALES =====
let currentPage = 1;
const itemsPerPage = 10;
let salidasData = [];
let charts = {};

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    loadData();
    initializeEventListeners();
    setDefaultDates();
});

// ===== GESTIÓN DE TABS =====
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

// ===== CARGAR DATOS =====
async function loadData() {
    try {
        // Cargar KPIs
        const responseKPIs = await fetch('/api/reportes/kpis/');
        const dataKPIs = await responseKPIs.json();
        
        if (dataKPIs.success) {
            const kpis = dataKPIs.kpis;
            animateValue('totalSalidas', 0, kpis.total_salidas, 1500);
            animateValue('totalMedicamentos', 0, kpis.total_medicamentos, 1500);
            animateValue('totalPacientes', 0, kpis.total_pacientes, 1500);
            animateValue('valorTotal', 0, kpis.valor_total, 1500, true);
        }
        
        // Cargar salidas
        const responseSalidas = await fetch('/api/reportes/salidas/');
        const dataSalidas = await responseSalidas.json();
        
        if (dataSalidas.success) {
            salidasData = dataSalidas.data;
            loadTabContent('historial');
        }
        
    } catch (error) {
        console.error('Error cargando datos:', error);
        showNotification('Error al cargar los datos', 'error');
    }
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
            <td><strong>${item.medicamento}</strong></td>
            <td><span class="badge badge-success">${item.cantidad} unidades</span></td>
            <td>${item.paciente}</td>
            <td>${item.responsable}</td>
            <td><span class="badge ${item.tipo_badge}">${item.tipo}</span></td>
            <td><strong>$${item.valor.toLocaleString()}</strong></td>
            <td>
                <button class="btn-action" onclick="verDetalle(${item.id})" title="Ver detalle">
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
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
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

  // Si el canvas está en 0x0 (tab no visible o aún no renderiza), no sirve
  if (canvas.width === 0 || canvas.height === 0) return null;

  try {
    return canvas.toDataURL('image/png', 1.0);
  } catch (e) {
    console.warn(`No se pudo capturar canvas ${canvasId}:`, e);
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
function filtrarPorFechas() {
    const fechaInicio = document.getElementById('fechaInicio').value;
    const fechaFin = document.getElementById('fechaFin').value;
    
    if (!fechaInicio || !fechaFin) {
        showNotification('Por favor selecciona ambas fechas', 'warning');
        return;
    }
    
    const filtered = salidasData.filter(item => {
        return item.fecha >= fechaInicio && item.fecha <= fechaFin;
    });
    
    currentPage = 1;
    loadHistorialTable(filtered);
    showNotification(`Se encontraron ${filtered.length} registros`, 'success');
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
    const doc = new jsPDF();
    
    // Agregar logo (1236x175 = proporción ~7:1)
    const logoUrl = '/static/farmacia/img/logo.jpg';
    doc.addImage(logoUrl, 'JPEG', 14, 10, 80, 12); // Ancho 80mm, Alto 12mm
    
    // Título
    doc.setFontSize(18);
    doc.text('Historial de Salidas', 14, 30);
    
    // Fecha de generación
    doc.setFontSize(10);
    doc.text(`Generado: ${new Date().toLocaleString('es-MX')}`, 14, 37);
    
    // Línea divisoria
    doc.setLineWidth(0.5);
    doc.line(14, 42, 196, 42);
    
    // Preparar datos de la tabla
    const rows = [];
    const tbody = document.getElementById('tableSalidasBody');
    
    if (tbody) {
        tbody.querySelectorAll('tr').forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 7) {
                rows.push([
                    cells[0].textContent.trim(),
                    cells[1].textContent.trim(),
                    cells[2].textContent.trim(),
                    cells[3].textContent.trim(),
                    cells[4].textContent.trim(),
                    cells[5].textContent.trim(),
                    cells[6].textContent.trim()
                ]);
            }
        });
    }
    
    // Crear tabla
    doc.autoTable({
        startY: 46,
        head: [['ID', 'Fecha', 'Medicamento', 'Cant.', 'Paciente', 'Responsable', 'Valor']],
        body: rows,
        theme: 'grid',
        styles: { fontSize: 8 },
        headStyles: { fillColor: [139, 0, 0] }
    });
    
    doc.save('Historial_Salidas.pdf');
}

async function exportarMedicamentosPDF() {
    const jsPDF = getJsPDF();
    const doc = new jsPDF();


  // Logo
  const logoUrl = window.STATIC_LOGO_URL;
  doc.addImage(logoUrl, 'JPEG', 14, 10, 80, 12);

  // Título
  doc.setFontSize(18);
  doc.text('Top 10 Medicamentos Más Dispensados', 14, 30);

  // Fecha
  doc.setFontSize(10);
  doc.text(`Generado: ${new Date().toLocaleString('es-MX')}`, 14, 37);

  // Línea
  doc.setLineWidth(0.5);
  doc.line(14, 42, 196, 42);

  // 1) CHART (si existe)
  // Ubicación pensada para una hoja portrait
  // (ancho util ~ 182mm)
  const okChart = addCanvasToPDF(doc, 'chartMedicamentos', 14, 46, 182, 80);

  // 2) TABLA (ranking)
  const rows = [];
  const ranking = document.getElementById('rankingMedicamentos');

  if (ranking) {
    ranking.querySelectorAll('.ranking-item').forEach((item, index) => {
      const nombre = item.querySelector('.ranking-name')?.textContent.trim() || 'N/A';
      const cantidad = item.querySelector('.ranking-value')?.textContent.trim() || '0';
      rows.push([String(index + 1), nombre, cantidad]);
    });
  }

  // Si hubo chart, baja la tabla; si no, úsala desde arriba
  const startY = okChart ? 46 + 80 + 8 : 46;

  doc.autoTable({
    startY,
    head: [['#', 'Medicamento', 'Cantidad Dispensada']],
    body: rows,
    theme: 'grid',
    styles: { fontSize: 10 },
    headStyles: { fillColor: [139, 0, 0] }
  });

  doc.save('TopMedicamentos.pdf');
}


async function exportarPacientesPDF() {
    const jsPDF = getJsPDF();
    const doc = new jsPDF();


  // Logo
  const logoUrl = window.STATIC_LOGO_URL;
  doc.addImage(logoUrl, 'JPEG', 14, 10, 80, 12);

  // Título
  doc.setFontSize(18);
  doc.text('Pacientes Frecuentes', 14, 30);

  // Fecha
  doc.setFontSize(10);
  doc.text(`Generado: ${new Date().toLocaleString('es-MX')}`, 14, 37);

  // Línea
  doc.setLineWidth(0.5);
  doc.line(14, 42, 196, 42);

  // 1) CHART (dona)
  const okChart = addCanvasToPDF(doc, 'chartPacientes', 14, 46, 182, 85);

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

  const startY = okChart ? 46 + 85 + 8 : 46;

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
    const doc = new jsPDF('landscape');



  // Logo
  const logoUrl = window.STATIC_LOGO_URL;
  doc.addImage(logoUrl, 'JPEG', 14, 10, 100, 15);

  // Título
  doc.setFontSize(18);
  doc.text('Tendencias Temporales', 14, 32);

  // Fecha
  doc.setFontSize(10);
  doc.text(`Generado: ${new Date().toLocaleString('es-MX')}`, 14, 39);

  // Línea
  doc.setLineWidth(0.5);
  doc.line(14, 44, 280, 44);

  // Chart principal (línea)
  addCanvasToPDF(doc, 'chartTendencias', 14, 50, 260, 85);

  // Charts secundarios (abajo, 2 columnas)
  // Ajusta alturas si lo ves apretado
  addCanvasToPDF(doc, 'chartDiasSemana', 14, 140, 128, 55);
  addCanvasToPDF(doc, 'chartHoras', 146, 140, 128, 55);

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
    const wb = XLSX.utils.book_new();
    
    // Preparar datos
    const data = [['ID', 'Fecha', 'Medicamento', 'Cantidad', 'Paciente', 'Responsable', 'Valor']];
    
    const tbody = document.getElementById('tableSalidasBody');
    if (tbody) {
        tbody.querySelectorAll('tr').forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 7) {
                data.push([
                    cells[0].textContent.trim(),
                    cells[1].textContent.trim(),
                    cells[2].textContent.trim(),
                    cells[3].textContent.trim(),
                    cells[4].textContent.trim(),
                    cells[5].textContent.trim(),
                    cells[6].textContent.trim()
                ]);
            }
        });
    }
    
    const ws = XLSX.utils.aoa_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, 'Historial');
    XLSX.writeFile(wb, 'Historial_Salidas.xlsx');
}

async function exportarMedicamentosExcel() {
  const workbook = new ExcelJS.Workbook();

  // Hoja 1: Chart
  const wsChart = workbook.addWorksheet('Chart');
  wsChart.getCell('A1').value = 'Top 10 Medicamentos - Gráfica';
  wsChart.getCell('A1').font = { bold: true, size: 14 };

  const imgBase64 = await canvasToPngBase64('chartMedicamentos');
  if (imgBase64) {
    const imageId = workbook.addImage({ base64: imgBase64, extension: 'png' });
    // Ubicación aproximada en celdas
    wsChart.addImage(imageId, {
      tl: { col: 0, row: 2 },   // A3
      ext: { width: 900, height: 420 }
    });
  } else {
    wsChart.getCell('A3').value = 'No se pudo capturar la gráfica (canvas vacío).';
  }

  // Hoja 2: Datos
  const wsData = workbook.addWorksheet('Top Medicamentos');
  wsData.addRow(['#', 'Medicamento', 'Cantidad Dispensada']).font = { bold: true };

  const ranking = document.getElementById('rankingMedicamentos');
  if (ranking) {
    ranking.querySelectorAll('.ranking-item').forEach((item, index) => {
      const nombre = item.querySelector('.ranking-name')?.textContent.trim() || '';
      const cantidad = item.querySelector('.ranking-value')?.textContent.trim() || '0';
      wsData.addRow([index + 1, nombre, Number(String(cantidad).replace(/[^\d.]/g, '')) || cantidad]);
    });
  }

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

  // Hoja 1: Chart
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

  // Hoja 2: Datos
  const wsData = workbook.addWorksheet('Pacientes');
  wsData.addRow(['#', 'Paciente', 'Total Visitas', 'Medicamentos', 'Última Visita', 'Gasto Total']).font = { bold: true };

  const tbody = document.getElementById('tablePacientesBody');
  if (tbody) {
    tbody.querySelectorAll('tr').forEach(row => {
      const cells = row.querySelectorAll('td');
      if (cells.length >= 6) {
        wsData.addRow([
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

  // Hoja 1: Charts
  const wsChart = workbook.addWorksheet('Charts');
  wsChart.getCell('A1').value = 'Tendencias - Gráficas';
  wsChart.getCell('A1').font = { bold: true, size: 14 };
  wsChart.getCell('A2').value = `Generado: ${new Date().toLocaleString('es-MX')}`;

  const c1 = await canvasToPngBase64('chartTendencias');
  const c2 = await canvasToPngBase64('chartDiasSemana');
  const c3 = await canvasToPngBase64('chartHoras');

  let rowOffset = 3;

  if (c1) {
    const id1 = workbook.addImage({ base64: c1, extension: 'png' });
    wsChart.addImage(id1, { tl: { col: 0, row: rowOffset }, ext: { width: 1100, height: 420 } });
    rowOffset += 22;
  }

  if (c2) {
    const id2 = workbook.addImage({ base64: c2, extension: 'png' });
    wsChart.addImage(id2, { tl: { col: 0, row: rowOffset }, ext: { width: 540, height: 320 } });
  }

  if (c3) {
    const id3 = workbook.addImage({ base64: c3, extension: 'png' });
    wsChart.addImage(id3, { tl: { col: 8, row: rowOffset }, ext: { width: 540, height: 320 } });
  }

  // Hoja 2: Nota / (si luego quieres, aquí ponemos meses y totales desde tu API)
  const wsData = workbook.addWorksheet('Datos');
  wsData.addRow(['Reporte de Tendencias']).font = { bold: true };
  wsData.addRow(['Generado:', new Date().toLocaleString('es-MX')]);
  wsData.addRow([]);
  wsData.addRow(['Nota:', 'Los datos detallados se pueden agregar aquí (meses/totales).']);

  const buffer = await workbook.xlsx.writeBuffer();
  downloadArrayBufferExcel(buffer, 'Tendencias_Temporales.xlsx');
}


function setDefaultDates() {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    
    document.getElementById('fechaInicio').value = firstDay.toISOString().split('T')[0];
    document.getElementById('fechaFin').value = today.toISOString().split('T')[0];
}

function verDetalle(id) {
    alert(`Ver detalle de salida #${id}`);
    // Aquí implementarías la lógica para mostrar el detalle
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
