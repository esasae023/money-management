/**
 * static/js/dashboard.js
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

// 3. Fungsi Render Bar Comparison
function renderBarCompare(elementId, strIncome, strExpense, strBalance) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

    const existingChart = Chart.getChart(ctx);
    if (existingChart) existingChart.destroy();

    const parseIdr = (str) => {
        if (!str) return 0;
        let clean = str.toString().replace(/[^0-9,-]/g, '').replace(',', '.');
        return parseFloat(clean) || 0;
    };

    const incVal = parseIdr(strIncome);
    const expVal = parseIdr(strExpense);
    const balVal = parseIdr(strBalance);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Masuk', 'Keluar', 'Saldo'],
            datasets: [{
                label: 'Nominal',
                data: [incVal, expVal, balVal],
                backgroundColor: ['#198754', '#dc3545', '#0d6efd'],
                borderRadius: 5,
                maxBarThickness: 50
            }]
        },
        options: {
            indexAxis: 'y', 
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let val = context.raw;
                            return "Rp " + val.toLocaleString('id-ID');
                        }
                    }
                }
            },
            scales: { x: { display: false }, y: { grid: { display: false } } }
        }
    });
}

// 4. Logic Ganti Mode dengan Efek Sliding (Geser Background)
function setMode(mode) {
    const secClean = document.getElementById('section-clean');
    const secDirty = document.getElementById('section-dirty');
    
    // 1. Reset: Hapus class active dari SEMUA tombol switch
    document.querySelectorAll('.glass-switch-btn').forEach(b => b.classList.remove('active'));
    
    // 2. Tentukan Tombol Aktif & Atur Section
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

    // 3. Tambah class active & Jalankan Animasi Slide
    const btn = document.getElementById(activeBtnId);
    if(btn) {
        btn.classList.add('active');
        movePill(btn); // Fungsi geser background
    }
}

// Helper: Menggeser Background Putih (Slide Pill)
function movePill(targetBtn) {
    const pill = document.getElementById('slidePill');
    if (pill && targetBtn) {
        // Ambil lebar dan posisi tombol yang diklik
        const width = targetBtn.offsetWidth;
        const left = targetBtn.offsetLeft;
        
        // Terapkan ke pill
        pill.style.width = `${width}px`;
        pill.style.left = `${left}px`; // Geser pill ke posisi tombol
    }
}

// Tambahkan event listener agar saat layar di-resize, pill tetap pas
window.addEventListener('resize', () => {
    const activeBtn = document.querySelector('.glass-switch-btn.active');
    if(activeBtn) movePill(activeBtn);
});