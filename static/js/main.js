/**
 * static/js/main.js
 * Logika Global: Sidebar & Toast Notification (Bootstrap Version)
 */

document.addEventListener("DOMContentLoaded", () => {
    
    // 1. LOGIC SIDEBAR (Hanya jalan jika elemen ada)
    document.body.classList.remove('preload');
    
    // Cek apakah di halaman login? Reset sidebar state
    if (window.location.pathname.includes('/login') || window.location.pathname.includes('/register')) {
        sessionStorage.removeItem('sidebarState');
        document.body.classList.remove('sb-expanded');
    }

    // 2. LOGIC TOAST NOTIFICATION (NEW DESIGN - BOOTSTRAP API)
    // Mencari semua elemen dengan class .toast (bukan .custom-toast)
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    
    var toastList = toastElList.map(function(toastEl) {
        // Init Bootstrap Toast dengan autohide 4 detik
        return new bootstrap.Toast(toastEl, { autohide: true, delay: 4000 });
    });
    
    // Tampilkan semua toast yang ada
    toastList.forEach(toast => toast.show());

    console.log("🚀 Main JS Loaded: Sidebar & Toasts Ready");
});

// Fungsi Toggle Sidebar (Dipanggil oleh tombol di HTML)
function toggleSidebar() {
    document.body.classList.toggle('sb-expanded');
    const isExpanded = document.body.classList.contains('sb-expanded');
    sessionStorage.setItem('sidebarState', isExpanded ? 'expanded' : 'collapsed');
}