/**
 * static/js/main.js
 * Logika Global: Sidebar & Toast Notification (Bootstrap Version)
 */

document.addEventListener("DOMContentLoaded", () => {
    
    // 1. LOGIC SIDEBAR (Hanya jalan jika elemen ada)
    document.body.classList.remove('preload');
    
    if (window.location.pathname.includes('/login') || window.location.pathname.includes('/register')) {
        sessionStorage.removeItem('sidebarState');
        document.body.classList.remove('sb-expanded');
    }

    // 2. LOGIC TOAST NOTIFICATION
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function(toastEl) {
        return new bootstrap.Toast(toastEl, { autohide: true, delay: 4000 });
    });
    toastList.forEach(toast => toast.show());

    // 3. [BARU] LOGIC MODAL RECOVERY CODE
    // Cek apakah ada data tersembunyi dari Flask flash
    const trigger = document.getElementById('recovery-data-trigger');
    if (trigger) {
        const msg = trigger.getAttribute('data-message');
        const code = trigger.getAttribute('data-code');
        
        // Isi data ke Modal
        const msgEl = document.getElementById('recovery-message-text');
        const codeEl = document.getElementById('display-recovery-code');
        
        if(msgEl) msgEl.innerText = msg;
        if(codeEl) codeEl.innerText = code;
        
        // Tampilkan Modal
        // Pastikan bootstrap sudah terload (ada di base.html)
        var myModal = new bootstrap.Modal(document.getElementById('recoveryModal'));
        myModal.show();
    }

    console.log("🚀 Main JS Loaded: Sidebar, Toasts & Modal Ready");
});

// Fungsi Toggle Sidebar
function toggleSidebar() {
    document.body.classList.toggle('sb-expanded');
    const isExpanded = document.body.classList.contains('sb-expanded');
    sessionStorage.setItem('sidebarState', isExpanded ? 'expanded' : 'collapsed');
}

// [BARU] Fungsi Copy Code di Modal
function copyRecoveryCode() {
    const codeText = document.getElementById('display-recovery-code').innerText;
    navigator.clipboard.writeText(codeText).then(() => {
        alert("Kode berhasil disalin ke clipboard!");
    }).catch(err => {
        console.error('Gagal menyalin: ', err);
    });
}