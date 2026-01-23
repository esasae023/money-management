/**
 * static/js/dashboard.js
 * Berisi fungsi-fungsi untuk menggambar grafik dan mengatur tampilan (Mode).
 */

// 1. Fungsi Render Grafik Garis (Trend)
function renderLine(elementId, labels, dataIncome, dataExpense) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return; // Stop jika canvas tidak ditemukan

    // Hapus chart lama jika ada (mencegah tumpuk-menumpuk/flickering)
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
                    borderColor: '#198754', // Hijau
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Pengeluaran',
                    data: dataExpense || [],
                    borderColor: '#dc3545', // Merah
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

// 2. Fungsi Render Grafik Pie (Donat)
function renderPie(elementId, labels, dataValues, colors) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

    const existingChart = Chart.getChart(ctx);
    if (existingChart) existingChart.destroy();

    // Cek jika data kosong
    if (!dataValues || dataValues.length === 0 || dataValues.every(v => v === 0)) {
        // Opsional: Tampilkan teks "No Data" atau biarkan kosong
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

// 3. Fungsi Render Bar Comparison (Masuk vs Keluar vs Saldo)
function renderBarCompare(elementId, strIncome, strExpense, strBalance) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

    const existingChart = Chart.getChart(ctx);
    if (existingChart) existingChart.destroy();

    // Helper: Parse string "Rp 1.000.000" jadi float 1000000
    const parseIdr = (str) => {
        if (!str) return 0;
        // Hapus "Rp", titik, dan spasi, ganti koma dengan titik (jika desimal)
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
                backgroundColor: [
                    '#198754', // Hijau
                    '#dc3545', // Merah
                    '#0d6efd'  // Biru
                ],
                borderRadius: 5,
                maxBarThickness: 50
            }]
        },
        options: {
            indexAxis: 'y', // Horizontal Bar
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let val = context.raw;
                            // Format ulang ke Rupiah untuk tooltip
                            return "Rp " + val.toLocaleString('id-ID');
                        }
                    }
                }
            },
            scales: {
                x: { display: false }, // Sembunyikan garis grid X
                y: { grid: { display: false } } // Sembunyikan garis grid Y
            }
        }
    });
}

// 4. Logic Ganti Mode (Semua / Bersih / Kotor)
function setMode(mode) {
    const secClean = document.getElementById('section-clean');
    const secDirty = document.getElementById('section-dirty');
    
    // Reset tombol active
    document.querySelectorAll('.tgl-btn').forEach(b => b.classList.remove('active'));
    
    if (mode === 'semua') {
        if(secClean) secClean.style.display = 'block'; 
        if(secDirty) secDirty.style.display = 'block';
        const btn = document.getElementById('btnSemua');
        if(btn) btn.classList.add('active');
    } else if (mode === 'bersih') {
        if(secClean) secClean.style.display = 'block'; 
        if(secDirty) secDirty.style.display = 'none';
        const btn = document.getElementById('btnBersih');
        if(btn) btn.classList.add('active');
    } else if (mode === 'kotor') {
        if(secClean) secClean.style.display = 'none'; 
        if(secDirty) secDirty.style.display = 'block';
        const btn = document.getElementById('btnKotor');
        if(btn) btn.classList.add('active');
    }
}