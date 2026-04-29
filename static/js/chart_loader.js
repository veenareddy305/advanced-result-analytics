// ================= GLOBAL =================
let charts = {};

// destroy old charts (important for filters)
function destroyCharts() {
    Object.values(charts).forEach(c => c.destroy());
    charts = {};
}

// ================= LINE CHART =================
function loadLineChart(id, labels, data, labelName="Trend") {
    const ctx = document.getElementById(id);
    if (!ctx) return;

    charts[id] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: labelName,
                data: data,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59,130,246,0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 4
            }]
        },
        options: baseOptions('Category', labelName)
    });
}

// ================= BAR CHART =================
function loadBarChart(id, labels, data, labelName="Data") {
    const ctx = document.getElementById(id);
    if (!ctx) return;

    charts[id] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: labelName,
                data: data,
                backgroundColor: '#10b981',
                borderRadius: 6
            }]
        },
        options: baseOptions('Category', labelName)
    });
}

// ================= MULTI DATASET (GROUPED) =================
function loadMultiBarChart(id, labels, datasets) {
    const ctx = document.getElementById(id);
    if (!ctx) return;

    charts[id] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: baseOptions('Category', 'Values')
    });
}

// ================= DOUGHNUT =================
function loadDoughnutChart(id, labels, data) {
    const ctx = document.getElementById(id);
    if (!ctx) return;

    charts[id] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ['#10b981','#ef4444','#3b82f6','#f59e0b','#8b5cf6']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

// ================= SGPA DISTRIBUTION =================
function loadSGPAChart(id, labels, data) {
    loadBarChart(id, labels, data, "SGPA Distribution");
}

// ================= BATCH COMPARISON =================
function loadBatchChart(id, labels, data) {
    loadBarChart(id, labels, data, "Batch Performance %");
}

// ================= COMMON OPTIONS =================
function baseOptions(xLabel, yLabel) {
    return {
        responsive: true,
        maintainAspectRatio: false,

        plugins: {
            legend: {
                display: true,
                position: 'top'
            },
            tooltip: {
                mode: 'index',
                intersect: false
            }
        },

        scales: {
            x: {
                title: {
                    display: true,
                    text: xLabel
                },
                grid: {
                    display: false
                }
            },
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: yLabel
                }
            }
        }
    };
}