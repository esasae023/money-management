/**
 * static/js/dashboard.js
 * FITUR BARU: Tooltip Pie Chart menampilkan Nominal + Persentase.
 * (Termasuk perbaikan Animasi Bar & Smart Currency sebelumnya)
 */

console.log("🚀 DASHBOARD JS - PIE TOOLTIP ENHANCED");

// HELPER: Reset Canvas
function resetCanvas(elementId) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return null;
    const newCanvas = canvas.cloneNode(true);
    canvas.parentNode.replaceChild(newCanvas, canvas);
    return newCanvas;
}

// 1. Fungsi Render Grafik Garis (Trend)
function renderLine(elementId, labels, dataIncome, dataExpense) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;

    new Chart(canvas, {
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
            animation: {
                duration: 2000,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: { position: 'top' },
                tooltip: { mode: 'index', intersect: false }
            },
            interaction: { mode: 'nearest', axis: 'x', intersect: false }
        }
    });
}

// 2. Fungsi Render Grafik Pie (Donat) - DENGAN TOOLTIP PERSENTASE
function renderPie(elementId, labels, dataValues, colors) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;

    if (!dataValues || dataValues.length === 0 || dataValues.every(v => v === 0)) {
        return; 
    }

    new Chart(canvas, {
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
            animation: {
                duration: 2000,
                easing: 'easeOutQuart',
                animateRotate: true,
                animateScale: true
            },
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } },
                
                // --- BAGIAN INI YANG DIMODIFIKASI ---
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            // 1. Ambil Nama Label (Contoh: "Makan")
                            let label = context.label || '';
                            if (label) {
                                label += ': ';
                            }
                            
                            // 2. Ambil Nilai Rupiah
                            const value = context.raw;
                            
                            // 3. Hitung Total Semua Data untuk mencari Persentase
                            const dataset = context.chart.data.datasets[0].data;
                            const total = dataset.reduce((acc, curr) => acc + curr, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;

                            // 4. Format Rupiah
                            const formattedValue = "Rp " + value.toLocaleString('id-ID');

                            // 5. Gabungkan: "Makan: Rp 500.000 (25.5%)"
                            return `${label}${formattedValue} (${percentage}%)`;
                        }
                    }
                }
                // -------------------------------------
            }
        }
    });
}

// 3. Fungsi Render Bar Comparison
function renderBarCompare(elementId, strIncome, strExpense, strBalance) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;

    // --- LOGIKA MATA UANG (Smart Parsing) ---
    const parseIdr = (input) => {
        if (typeof input === 'number') return input;
        if (!input) return 0;
        let str = input.toString().replace(/[^0-9,.-]/g, '');

        if (str.includes('.') && str.includes(',')) {
            if (str.lastIndexOf('.') > str.lastIndexOf(',')) {
                str = str.replace(/,/g, ''); 
            } else {
                str = str.replace(/\./g, '').replace(',', '.');
            }
        } else if (str.includes(',')) {
            const parts = str.split(',');
            if (parts[parts.length - 1].length === 3 || parts.length > 2) {
                str = str.replace(/,/g, '');
            } else {
                str = str.replace(',', '.');
            }
        } else if (str.includes('.')) {
            const parts = str.split('.');
            if (parts[parts.length - 1].length === 3 || parts.length > 2) {
                str = str.replace(/\./g, '');
            }
        }
        return parseFloat(str) || 0;
    };

    const incVal = parseIdr(strIncome);
    const expVal = parseIdr(strExpense);
    const balVal = parseIdr(strBalance);
    const totalAll = Math.abs(incVal) + Math.abs(expVal) + Math.abs(balVal);

    new Chart(canvas, {
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
            indexAxis: 'y', // Horizontal
            responsive: true,
            maintainAspectRatio: false, 
            layout: { padding: { right: 50 } },
            animation: {
                duration: 2000,
                easing: 'easeOutQuart',
                x: { from: 0 } // Efek Geser
            },
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
    if(btn) { btn.classList.add('active'); movePill(btn); }
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