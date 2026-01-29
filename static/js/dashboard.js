/**
 * static/js/dashboard.js
 * VERSI: V15 - FINAL GRADIENT & GLASS
 */

console.log("🚀 DASHBOARD FINAL JS LOADED");

// =========================================
// 1. ANIMASI ANGKA (Count Up)
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
            let cleanStr = rawText.replace(/[^0-9-]/g, ''); 
            const finalNumber = parseFloat(cleanStr) || 0;
            el.innerHTML = "Rp 0"; 
            
            setTimeout(() => {
                 animateCountUp(id, finalNumber);
            }, Math.random() * 300);
        }
    });
}

// =========================================
// 2. FUNGSI RENDER GRAFIK
// =========================================
function resetCanvas(elementId) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return null;
    const newCanvas = canvas.cloneNode(true);
    canvas.parentNode.replaceChild(newCanvas, canvas);
    return newCanvas;
}

// Helper: Membuat Gradient Vertical (Pudar ke Bawah)
function createGradient(ctx, colorHex) {
    // Estimasi tinggi chart max 300px
    const gradient = ctx.createLinearGradient(0, 0, 0, 300); 
    
    // Convert Hex to RGB untuk transparansi
    let r = 0, g = 0, b = 0;
    if (colorHex.length === 7) {
        r = parseInt(colorHex.slice(1, 3), 16);
        g = parseInt(colorHex.slice(3, 5), 16);
        b = parseInt(colorHex.slice(5, 7), 16);
    }

    // Atas: Warna Asli (Solid 90%)
    gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.9)`);
    // Bawah: Warna Asli (Pudar 20%)
    gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.2)`); 
    
    return gradient;
}

// Render Line (Trend)
function renderLine(elementId, labels, dataIncome, dataExpense) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;
    new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels || [],
            datasets: [
                { label: 'Pemasukan', data: dataIncome || [], borderColor: '#059669', backgroundColor: 'rgba(5, 150, 105, 0.1)', tension: 0.3, fill: true },
                { label: 'Pengeluaran', data: dataExpense || [], borderColor: '#dc2626', backgroundColor: 'rgba(220, 38, 38, 0.1)', tension: 0.3, fill: true }
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

// Render Pie
function renderPie(elementId, labels, dataValues, colors) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;
    if (!dataValues || dataValues.length === 0 || dataValues.every(v => v === 0)) return;

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: labels || [],
            datasets: [{ data: dataValues || [], backgroundColor: colors || ['#ccc'], borderWidth: 2, borderColor: '#ffffff' }]
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

// Render Bar Comparison (DENGAN GRADASI)
function renderBarCompare(elementId, strIncome, strExpense, strBalance, colors) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;
    
    // Reset canvas untuk context baru
    const newCanvas = resetCanvas(elementId); 
    if (!newCanvas) return;
    
    const ctx = newCanvas.getContext('2d');

    const parseIdr = (input) => {
        if (typeof input === 'number') return input;
        if (!input) return 0;
        let str = input.toString().replace(/[^0-9,.-]/g, '');
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

    // Siapkan Warna (Gradient)
    const baseColors = colors || ['#059669', '#dc2626', '#2563eb'];
    const gradientColors = baseColors.map(c => createGradient(ctx, c));

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Masuk', 'Keluar', 'Saldo'],
            datasets: [{
                label: 'Nominal',
                data: [incVal, expVal, balVal],
                backgroundColor: gradientColors, // Pakai Gradasi
                borderColor: baseColors,         // Border Solid
                borderWidth: 1,
                borderRadius: 8,
                barPercentage: 0.6,
            }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false, 
            layout: { padding: { right: 50 } },
            animation: {
                duration: 2000,
                easing: 'easeOutQuart',
                x: {
                    from: 0
                }
            },
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
                    ctx.font = 'bold 11px sans-serif'; ctx.fillStyle = '#6b7280'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
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