/**
 * static/js/dashboard.js
 * FINAL FIX V2: Logika Cerdas Deteksi Koma (Ribuan vs Desimal)
 */

// 1. Fungsi Render Grafik Garis
function renderLine(elementId, labels, dataIncome, dataExpense) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return; 

    const existingChart = Chart.getChart(ctx);
    if (existingChart) existingChart.destroy();

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels || [],
            datasets: [
                {
                    label: 'Pemasukan',
                    data: dataIncome || [],
                    borderColor: '#198754', 
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Pengeluaran',
                    data: dataExpense || [],
                    borderColor: '#dc3545', 
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: { mode: 'index', intersect: false }
            },
            interaction: { mode: 'nearest', axis: 'x', intersect: false }
        }
    });
}

// 2. Fungsi Render Grafik Pie
function renderPie(elementId, labels, dataValues, colors) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

    const existingChart = Chart.getChart(ctx);
    if (existingChart) existingChart.destroy();

    if (!dataValues || dataValues.length === 0 || dataValues.every(v => v === 0)) {
        return; 
    }

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels || [],
            datasets: [{
                data: dataValues || [],
                backgroundColor: colors || ['#ccc'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } }
            }
        }
    });
}

// 3. Fungsi Render Bar Comparison (SMART PARSING FIX)
function renderBarCompare(elementId, strIncome, strExpense, strBalance) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

    const existingChart = Chart.getChart(ctx);
    if (existingChart) existingChart.destroy();

    // --- LOGIKA PARSING ANGKA CERDAS ---
    const parseIdr = (input, label) => {
        // 1. Jika input murni angka, langsung pakai
        if (typeof input === 'number') return input;
        
        // 2. Jika kosong/null
        if (!input) return 0;

        let original = input.toString();
        // Hanya ambil angka, titik, koma, minus
        let str = original.replace(/[^0-9,.-]/g, '');

        // 3. DETEKSI FORMAT (US vs INDO)
        
        // Cek apakah ada Titik DAN Koma sekaligus?
        if (str.includes('.') && str.includes(',')) {
            // Jika posisi Titik > Koma (Contoh: 10,000.00) -> US Format
            if (str.lastIndexOf('.') > str.lastIndexOf(',')) {
                str = str.replace(/,/g, ''); // Hapus koma (ribuan)
                // Titik biarkan (desimal)
            } 
            // Jika posisi Koma > Titik (Contoh: 10.000,00) -> Indo Format
            else {
                str = str.replace(/\./g, ''); // Hapus titik (ribuan)
                str = str.replace(',', '.');  // Koma jadi titik (desimal)
            }
        }
        // Cek jika HANYA ada Koma (Kasus Anda: 11,161,000 atau 778,500)
        else if (str.includes(',')) {
            const parts = str.split(',');
            const lastPart = parts[parts.length - 1];

            // Jika di belakang koma pas 3 digit (Contoh: 500 atau 000)
            // ATAU jika komanya lebih dari satu (11,161,000)
            if (lastPart.length === 3 || parts.length > 2) {
                // Ini Ribuan (US Format) -> Hapus semua koma
                str = str.replace(/,/g, '');
            } else {
                // Ini Desimal (Indo Format) -> Ganti koma jadi titik
                str = str.replace(',', '.');
            }
        }
        // Cek jika HANYA ada Titik (Contoh: 10.000 atau 10.5)
        else if (str.includes('.')) {
            const parts = str.split('.');
            const lastPart = parts[parts.length - 1];
            
            // Jika di belakang titik pas 3 digit (10.000)
            if (lastPart.length === 3 || parts.length > 2) {
                // Ini Ribuan (Indo Format) -> Hapus semua titik
                str = str.replace(/\./g, '');
            } else {
                // Ini Desimal -> Biarkan
            }
        }

        let result = parseFloat(str) || 0;
        
        // Debugging di Console
        console.log(`[${label}] Input: "${original}" -> Parsed: ${result}`);
        
        return result;
    };

    const incVal = parseIdr(strIncome, 'Pemasukan');
    const expVal = parseIdr(strExpense, 'Pengeluaran');
    const balVal = parseIdr(strBalance, 'Saldo');

    const totalAll = Math.abs(incVal) + Math.abs(expVal) + Math.abs(balVal);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Masuk', 'Keluar', 'Saldo'],
            datasets: [{
                label: 'Nominal',
                data: [incVal, expVal, balVal],
                backgroundColor: ['#198754', '#dc3545', '#0d6efd'],
                borderRadius: 5,
                maxBarThickness: 40, 
            }]
        },
        options: {
            indexAxis: 'y', 
            responsive: true,
            maintainAspectRatio: false, 
            layout: { padding: { right: 50 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return "Rp " + context.raw.toLocaleString('id-ID');
                        }
                    }
                }
            },
            scales: { x: { display: false }, y: { grid: { display: false } } }
        },
        plugins: [{
            id: 'percentageLabel',
            afterDatasetsDraw(chart) {
                const { ctx, data } = chart;
                chart.getDatasetMeta(0).data.forEach((bar, index) => {
                    const value = data.datasets[0].data[index];
                    let percent = 0;
                    if (totalAll > 0) percent = (value / totalAll * 100).toFixed(1);

                    ctx.font = 'bold 11px sans-serif';
                    ctx.fillStyle = '#555';
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    
                    let xPos = value >= 0 ? bar.x + 5 : bar.x - 40;
                    if (value < 0 && percent === "0.0") xPos = bar.x + 5;
                    
                    ctx.fillText(percent + '%', xPos, bar.y);
                });
            }
        }]
    });
}

// 4. Logic Ganti Mode
function setMode(mode) {
    const secClean = document.getElementById('section-clean');
    const secDirty = document.getElementById('section-dirty');
    
    document.querySelectorAll('.glass-switch-btn').forEach(b => b.classList.remove('active'));
    
    let activeBtnId = '';
    if (mode === 'semua') {
        if(secClean) secClean.style.display = 'block'; 
        if(secDirty) secDirty.style.display = 'block';
        activeBtnId = 'btnSemua';
    } else if (mode === 'bersih') {
        if(secClean) secClean.style.display = 'block'; 
        if(secDirty) secDirty.style.display = 'none';
        activeBtnId = 'btnBersih';
    } else if (mode === 'kotor') {
        if(secClean) secClean.style.display = 'none'; 
        if(secDirty) secDirty.style.display = 'block';
        activeBtnId = 'btnKotor';
    }

    const btn = document.getElementById(activeBtnId);
    if(btn) {
        btn.classList.add('active');
        movePill(btn);
    }
}

function movePill(targetBtn) {
    const pill = document.getElementById('slidePill');
    if (pill && targetBtn) {
        const width = targetBtn.offsetWidth;
        const left = targetBtn.offsetLeft;
        pill.style.width = `${width}px`;
        pill.style.left = `${left}px`;
    }
}

window.addEventListener('resize', () => {
    const activeBtn = document.querySelector('.glass-switch-btn.active');
    if(activeBtn) movePill(activeBtn);
});