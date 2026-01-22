// Fungsi Render Grafik Garis (Trend)
function renderLine(id, labels, inc, exp) {
    if(!document.getElementById(id)) return;
    new Chart(document.getElementById(id), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Masuk', data: inc, borderColor: '#198754', backgroundColor: 'rgba(25, 135, 84, 0.1)', tension: 0.3, fill: true },
                { label: 'Keluar', data: exp, borderColor: '#dc3545', backgroundColor: 'rgba(220, 53, 69, 0.1)', tension: 0.3, fill: true }
            ]
        }, options: { responsive: true, maintainAspectRatio: false }
    });
}

// Fungsi Render Grafik Pie
function renderPie(id, labels, data, colors) {
    if(!document.getElementById(id)) return;
    new Chart(document.getElementById(id), {
        type: 'doughnut',
        data: { labels: labels, datasets: [{ data: data, backgroundColor: colors }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
    });
}

// Fungsi Render Bar Comparison (Kiri vs Kanan)
function renderBarCompare(id, income, expense, balance) {
    if(!document.getElementById(id)) return;
    
    // Helper parse IDR string ke Float
    const parseIdr = (str) => { 
        if(!str) return 0; 
        return parseFloat(str.toString().replace(/[^0-9,-]/g, '').replace(',', '.')); 
    };
    
    const incVal = parseIdr(income);
    const expVal = parseIdr(expense);
    const balVal = parseIdr(balance);

    new Chart(document.getElementById(id), {
        type: 'bar',
        data: {
            labels: ['Masuk', 'Keluar', 'Saldo'],
            datasets: [{
                data: [incVal, expVal, balVal],
                backgroundColor: ['#198754', '#dc3545', '#0d6efd'],
                borderRadius: 5, maxBarThickness: 40 
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
                        label: function(ctx) {
                            let val = ctx.raw;
                            let percent = incVal > 0 ? ((val / incVal) * 100).toFixed(1) + '%' : '0%';
                            return `Rp ${val.toLocaleString('id-ID')} (${percent})`;
                        }
                    }
                }
            },
            scales: { x: { display: false }, y: { grid: { display: false } } },
        },
        plugins: [{
            id: 'percentLabel',
            afterDatasetsDraw(chart) {
                const { ctx } = chart;
                chart.data.datasets.forEach((dataset, i) => {
                    const meta = chart.getDatasetMeta(i);
                    meta.data.forEach((bar, index) => {
                        const value = dataset.data[index];
                        let percent = incVal > 0 ? (value / incVal * 100).toFixed(1) + '%' : '0%';
                        ctx.font = 'bold 11px sans-serif';
                        ctx.fillStyle = '#666';
                        ctx.textAlign = 'left';
                        ctx.textBaseline = 'middle';
                        ctx.fillText(percent, bar.x + 5, bar.y);
                    });
                });
            }
        }]
    });
}

// Logic Ganti Mode (Semua / Bersih / Kotor)
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