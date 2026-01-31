document.addEventListener("DOMContentLoaded", () => {
    
    // 1. Sidebar Logic (Dari kode lama)
    document.body.classList.remove('preload');
    if (window.location.pathname.includes('/login') || window.location.pathname.includes('/register')) {
        sessionStorage.removeItem('sidebarState');
        document.body.classList.remove('sb-expanded');
    }

    // 2. Toast Notification Logic
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function(toastEl) {
        return new bootstrap.Toast(toastEl, { autohide: true, delay: 4000 });
    });
    toastList.forEach(toast => toast.show());

    // 3. [BARU] Logic Modal Recovery Code
    // Mencari elemen trigger tersembunyi yang dikirim dari server
    const trigger = document.getElementById('recovery-data-trigger');
    
    if (trigger) {
        // Ambil data dari atribut HTML (Best Practice)
        const msg = trigger.dataset.message;
        const code = trigger.dataset.code;
        
        // Masukkan data ke dalam Modal
        const msgEl = document.getElementById('recovery-message-text');
        const codeEl = document.getElementById('display-recovery-code');
        
        if(msgEl) msgEl.innerText = msg;
        if(codeEl) codeEl.innerText = code;
        
        // Tampilkan Modal menggunakan Bootstrap API
        const modalEl = document.getElementById('recoveryModal');
        if (modalEl) {
            var myModal = new bootstrap.Modal(modalEl);
            myModal.show();
        }
    }
});

// Fungsi Toggle Sidebar
function toggleSidebar() {
    document.body.classList.toggle('sb-expanded');
    const isExpanded = document.body.classList.contains('sb-expanded');
    sessionStorage.setItem('sidebarState', isExpanded ? 'expanded' : 'collapsed');
}

// [BARU] Fungsi Copy to Clipboard (Global)
// Menerima ID elemen target sebagai parameter
function copyToClipboard(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    // Ambil teks asli (jika ada dataset value, gunakan itu, jika tidak ambil innerText)
    const textToCopy = el.dataset.value || el.innerText;
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        alert("Kode berhasil disalin ke clipboard!");
    }).catch(err => {
        console.error('Gagal menyalin: ', err);
    });
}

// [BARU] Toggle Blur Effect
function toggleBlur(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.classList.toggle('revealed');
}