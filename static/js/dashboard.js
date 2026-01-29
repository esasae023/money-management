/**
 * static/js/dashboard.js
 * VERSI: CHROME DESKTOP SPECIFIC FIX
 * Fix untuk: Animasi pie chart tidak jalan di Chrome Desktop (tapi OK di Mobile & Inspect)
 * Root cause: Hardware acceleration & compositor layer di Chrome Desktop
 */

console.log("🚀 DASHBOARD JS - CHROME DESKTOP COMPOSITOR FIX");

const chartInstances = {};

// HELPER: Force GPU rendering pada canvas
function forceGPURendering(canvas) {
    if (!canvas) return;
    
    // Force compositing layer dengan CSS tricks
    canvas.style.willChange = 'transform';
    canvas.style.transform = 'translateZ(0)';
    canvas.style.backfaceVisibility = 'hidden';
    
    // Trigger reflow
    void canvas.offsetHeight;
    
    // Reset will-change setelah animasi (cleanup)
    setTimeout(() => {
        canvas.style.willChange = 'auto';
    }, 2000);
}

function resetCanvas(elementId) {
    if (chartInstances[elementId]) {
        chartInstances[elementId].destroy();
        delete chartInstances[elementId];
    }
    
    const canvas = document.getElementById(elementId);
    if (!canvas) return null;
    
    const ctx = canvas.getContext('2d', {
        // PENTING: Alpha channel untuk Chrome Desktop
        alpha: true,
        desynchronized: false, // Sinkron dengan compositor
        willReadFrequently: false
    });
    
    if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    
    return canvas;
}

// 1. Fungsi Render Grafik Garis
function renderLine(elementId, labels, dataIncome, dataExpense) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;
    
    forceGPURendering(canvas);

    const chart = new Chart(canvas, {
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
    
    chartInstances[elementId] = chart;
}

// 2. Fungsi Render Grafik Pie - CHROME DESKTOP FIX
function renderPie(elementId, labels, dataValues, colors) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;

    const hasData = dataValues && dataValues.length > 0 && !dataValues.every(v => v === 0);
    const finalData = hasData ? dataValues : [1];
    const finalLabels = hasData ? labels : ['Tidak ada data'];
    const finalColors = hasData ? colors : ['#e9ecef'];

    // *** KUNCI UTAMA: Force GPU rendering SEBELUM create chart ***
    forceGPURendering(canvas);
    
    // Gunakan setTimeout DAN requestAnimationFrame combo
    setTimeout(() => {
        requestAnimationFrame(() => {
            const chart = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: finalLabels,
                    datasets: [{
                        data: finalData,
                        backgroundColor: finalColors,
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    // Optimasi untuk Chrome Desktop compositor
                    animation: {
                        animateRotate: true,
                        animateScale: true,
                        duration: 1200, // Sedikit lebih cepat untuk performa
                        easing: 'easeOutQuart',
                        // Callback untuk force repaint
                        onProgress: function(animation) {
                            // Trigger repaint di Chrome Desktop
                            if (animation.currentStep % 5 === 0) {
                                canvas.style.opacity = 0.9999;
                                canvas.style.opacity = 1;
                            }
                        },
                        onComplete: function() {
                            console.log(`✅ Pie ${elementId} animated`);
                            // Cleanup GPU hints
                            canvas.style.willChange = 'auto';
                        }
                    },
                    plugins: {
                        legend: { 
                            position: 'right', 
                            labels: { 
                                boxWidth: 12, 
                                font: { size: 10 },
                                padding: 10
                            } 
                        },
                        tooltip: {
                            enabled: hasData,
                            callbacks: {
                                label: function(context) {
                                    if (!hasData) return 'Tidak ada data';
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${percentage}%`;
                                }
                            }
                        }
                    }
                }
            });
            
            chartInstances[elementId] = chart;
        });
    }, 0);
}

// 3. Fungsi Render Bar Comparison
function renderBarCompare(elementId, strIncome, strExpense, strBalance) {
    const canvas = resetCanvas(elementId);
    if (!canvas) return;
    
    forceGPURendering(canvas);

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

    const chart = new Chart(canvas, {
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
            animation: {
                duration: 2000,
                easing: 'easeOutQuart',
                x: {
                    from: 0
                }
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
    
    chartInstances[elementId] = chart;
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

function destroyAllCharts() {
    Object.keys(chartInstances).forEach(key => {
        if (chartInstances[key]) {
            chartInstances[key].destroy();
            delete chartInstances[key];
        }
    });
}