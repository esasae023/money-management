/**
 * static/js/main.js
 * Logika Global: Sidebar & Toast Notification
 */

// --- 1. LOGIC SIDEBAR TOGGLE ---
function toggleSidebar() {
    document.body.classList.toggle('sb-expanded');
    const isExpanded = document.body.classList.contains('sb-expanded');
    sessionStorage.setItem('sidebarState', isExpanded ? 'expanded' : 'collapsed');
}

// --- 2. MAIN EVENT LISTENER ---
document.addEventListener("DOMContentLoaded", () => {
    
    // A. Hapus class preload agar transisi sidebar aktif kembali
    document.body.classList.remove('preload');

    // B. Cek apakah kita di halaman Login (Reset Sidebar)
    if (window.location.pathname.includes('/login')) {
        sessionStorage.removeItem('sidebarState');
        document.body.classList.remove('sb-expanded');
    }

    // --- 3. LOGIC TOAST NOTIFICATION ---
    const toasts = document.querySelectorAll('.custom-toast');
    
    toasts.forEach(t => {
        // Fungsi untuk menutup toast
        const closeToast = (immediate = false) => {
            t.classList.remove('active-toast'); // Hilangkan opacity (efek fade out)
            
            // Jika immediate (diklik manual), langsung hilangkan lebih cepat
            const delay = immediate ? 200 : 600;

            setTimeout(() => {
                if (t.parentNode) t.parentNode.removeChild(t);
            }, delay); 
        };

        // 1. Animasi Masuk (Slide In)
        setTimeout(() => {
            t.classList.add('active-toast');
        }, 100);

        // 2. Timer Auto Close (5 Detik)
        const autoCloseTimer = setTimeout(() => {
            closeToast(false);
        }, 5000);

        // 3. Event Listener Tombol Close
        const closeBtn = t.querySelector('.close-toast-btn');
        if (closeBtn) {
            // Gunakan onclick langsung agar lebih robust menimpa event lain
            closeBtn.onclick = function(e) {
                // Hentikan timer otomatis agar tidak crash
                clearTimeout(autoCloseTimer);
                
                // Tutup segera
                console.log("Toast ditutup manual.");
                closeToast(true);
            };
        }
    });
});