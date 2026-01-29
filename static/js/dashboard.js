/**
 * static/js/dashboard.js
 * FIXED: Masalah parsing desimal yang membuat angka melonjak 10x-100x lipat.
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

// 3. Fungsi Render Bar Comparison (FIXED PARSING LOGIC)
function renderBarCompare(elementId, strIncome, strExpense, strBalance) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

    const existingChart = Chart.getChart(ctx);
    if (existingChart) existingChart.destroy();

    // --- LOGIKA PARSING BARU (LEBIH AMAN) ---
    const parseIdr = (input) => {
        // 1. Jika input sudah berupa angka (bukan teks), langsung kembalikan
        if (typeof input === 'number') return input;
        
        // 2. Jika kosong/null
        if (!input) return 0;

        let str = input.toString();

        // 3. Deteksi Format
        // Jika mengandung KOMA (Format Indo: 10.000,00), maka hapus titik ribuan
        if (str.includes(',')) {
            str = str.replace(/\./g, ''); // Hapus titik ribuan
            str = str.replace(',', '.');  // Ganti koma jadi titik desimal
        } else {
            // Jika TIDAK mengandung koma, asumsi format Raw/Inggris (10000.00)
            // Hapus karakter aneh (misal "Rp "), TAPI JANGAN HAPUS TITIK DESIMAL
            str = str.replace(/[^0-9.-]/g, ''); 
        }

        return parseFloat(str) || 0;
    };

    const incVal = parseIdr(strIncome);
    const expVal = parseIdr(strExpense);
    const balVal = parseIdr(strBalance);

    // Hitung Total Absolut untuk Persentase (Agar persentase minus tetap masuk akal)
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
                    
                    // Gunakan totalAll (absolute sum) agar tidak error saat ada minus
                    if (totalAll > 0) percent = (value / totalAll * 100).toFixed(1);

                    ctx.font = 'bold 11px sans-serif';
                    ctx.fillStyle = '#555';
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    
                    // Jika batang minus (ke kiri), taruh teks di sebelah kanan axis 0 biar rapi
                    // Atau simpelnya taruh di ujung batang
                    let xPos = value >= 0 ? bar.x + 5 : bar.x - 35; 
                    
                    ctx.fillText(percent + '%', xPos, bar.y);
                });
            }
        }]
    });
}

// 4. Logic Ganti Mode dengan Efek Sliding
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