/**
 * static/js/dashboard.js
 * VERSI: V3 - ANIMASI COUNTING FIX
 */

console.log("🚀 DASHBOARD JS V3 LOADED");

// =========================================
// 1. FUNGSI ANIMASI ANGKA (HITUNG MAJU)
// =========================================
function animateCountUp(elementId, endValue, duration = 2000) {
    const obj = document.getElementById(elementId);
    if (!obj || endValue === 0) return;

    let startTimestamp = null;
    const startValue = 0;

    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const currentVal = Math.floor(easeOutQuart * (endValue - startValue) + startValue);
        
        obj.innerHTML = "Rp " + currentVal.toLocaleString('id-ID');
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            obj.innerHTML = "Rp " + endValue.toLocaleString('id-ID');
        }
    };
    window.requestAnimationFrame(step);
}

function initCountingAnimation() {
    const targetIds = [
        'clean-income-val', 'clean-expense-val', 'clean-balance-val', 
        'dirty-income-val', 'dirty-expense-val', 'dirty-balance-val'
    ];

    targetIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            const rawText = el.innerText;
            // Hapus semua karakter kecuali angka dan minus
            // Ini lebih aman karena data Anda dari Python sudah bulat (.0f)
            let cleanStr = rawText.replace(/[^0-9-]/g, ''); 
            
            const finalNumber = parseFloat(cleanStr) || 0;
            el.innerHTML = "Rp 0"; // Reset ke 0
            
            setTimeout(() => {
                 animateCountUp(id, finalNumber);
            }, Math.random() * 300);
        }
    });
}

// =========================================
// 2. FUNGSI RENDER GRAFIK (HELPER)
// =========================================
function resetCanvas(elementId) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return null;
    const newCanvas = canvas.cloneNode(true);
    canvas.parentNode.replaceChild(newCanvas, canvas);
    return newCanvas;
}

// Render Line
function renderLine(elementId, labels, dataIncome, dataExpense) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;
    new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels || [],
            datasets: [
                { label: 'Pemasukan', data: dataIncome || [], borderColor: '#198754', backgroundColor: 'rgba(25, 135, 84, 0.1)', tension: 0.3, fill: true },
                { label: 'Pengeluaran', data: dataExpense || [], borderColor: '#dc3545', backgroundColor: 'rgba(220, 53, 69, 0.1)', tension: 0.3, fill: true }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            animation: { duration: 2000, easing: 'easeOutQuart' },
            plugins: { legend: { position: 'top' }, tooltip: { mode: 'index', intersect: false } },
            interaction: { mode: 'nearest', axis: 'x', intersect: false }
        }
    });
}

// Render Pie (Dengan Tooltip Lengkap)
function renderPie(elementId, labels, dataValues, colors) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;
    if (!dataValues || dataValues.length === 0 || dataValues.every(v => v === 0)) return;

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: labels || [],
            datasets: [{ data: dataValues || [], backgroundColor: colors || ['#ccc'], borderWidth: 1 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            animation: { duration: 2000, easing: 'easeOutQuart', animateRotate: true, animateScale: true },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (label) label += ': ';
                            const value = context.raw;
                            const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}Rp ${value.toLocaleString('id-ID')} (${percentage}%)`;
                        }
                    }
                },
                legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } }
            }
        }
    });
}

// Render Bar (Dengan Animasi Geser & Fix Mata Uang)
function renderBarCompare(elementId, strIncome, strExpense, strBalance) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;

    const parseIdr = (input) => {
        if (typeof input === 'number') return input;
        if (!input) return 0;
        let str = input.toString().replace(/[^0-9,.-]/g, '');
        // Logika Smart Parsing
        if (str.includes('.') && str.includes(',')) {
            if (str.lastIndexOf('.') > str.lastIndexOf(',')) str = str.replace(/,/g, ''); 
            else str = str.replace(/\./g, '').replace(',', '.');
        } else if (str.includes(',')) {
            const parts = str.split(',');
            if (parts[parts.length - 1].length === 3 || parts.length > 2) str = str.replace(/,/g, '');
            else str = str.replace(',', '.');
        } else if (str.includes('.')) {
            const parts = str.split('.');
            if (parts[parts.length - 1].length === 3 || parts.length > 2) str = str.replace(/\./g, '');
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
                borderRadius: 5, maxBarThickness: 40, 
            }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false, 
            layout: { padding: { right: 50 } },
            animation: { duration: 2000, easing: 'easeOutQuart', x: { from: 0 } },
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: function(context) { return "Rp " + context.raw.toLocaleString('id-ID'); } } }
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
                    ctx.font = 'bold 11px sans-serif'; ctx.fillStyle = '#555'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
                    let xPos = value >= 0 ? bar.x + 5 : bar.x - 40;
                    if (value < 0 && percent === "0.0") xPos = bar.x + 5;
                    ctx.fillText(percent + '%', xPos, bar.y);
                });
            }
        }]
    });
}

// 3. LOGIC GANTI MODE
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
        pill.style.width = `${targetBtn.offsetWidth}px`;
        pill.style.left = `${targetBtn.offsetLeft}px`;
    }
}
window.addEventListener('resize', () => {
    const activeBtn = document.querySelector('.glass-switch-btn.active');
    if(activeBtn) movePill(activeBtn);
});