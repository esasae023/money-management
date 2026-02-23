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

/* =========================================
   THEME MANAGER (LIGHT / DARK MODE)
   ========================================= */
function toggleTheme(e) {
    if (e) e.preventDefault();
    
    const htmlEl = document.documentElement;
    const currentTheme = htmlEl.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    // Nyalakan efek transisi sesaat sebelum tema diubah
    document.body.classList.add('theme-in-transition');

    // Set tema dan simpan di LocalStorage
    htmlEl.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    updateThemeUI(newTheme);
    
    // Trigger event untuk memberitahu Chart.js jika ada grafik yang perlu digambar ulang
    window.dispatchEvent(new Event('themeChanged'));

    // Matikan efek transisi setelah 400 milidetik (sesuai durasi CSS)
    setTimeout(() => {
        document.body.classList.remove('theme-in-transition');
    }, 400);
}

function updateThemeUI(theme) {
    const isDark = theme === 'dark';
    
    // Update ikon dan teks di Desktop
    document.querySelectorAll('.theme-icon-desktop').forEach(icon => {
        icon.className = isDark ? 'theme-icon-desktop bi bi-sun' : 'theme-icon-desktop bi bi-moon';
    });
    document.querySelectorAll('.theme-text-desktop').forEach(text => {
        text.innerText = isDark ? 'Mode Terang' : 'Mode Gelap';
    });

    // Update ikon dan teks di Mobile Drawer
    document.querySelectorAll('.theme-icon-mobile').forEach(icon => {
        icon.className = isDark ? 'theme-icon-mobile bi bi-sun fs-4 me-3' : 'theme-icon-mobile bi bi-moon fs-4 me-3';
    });
    document.querySelectorAll('.theme-text-mobile').forEach(text => {
        text.innerText = isDark ? 'Beralih ke Mode Terang' : 'Beralih ke Mode Gelap';
    });
}

// Sinkronisasi tombol saat halaman pertama kali dimuat
document.addEventListener("DOMContentLoaded", () => {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
    updateThemeUI(currentTheme);
});