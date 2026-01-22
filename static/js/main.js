function toggleSidebar() {
    document.body.classList.toggle('sb-expanded');
    const isExpanded = document.body.classList.contains('sb-expanded');
    sessionStorage.setItem('sidebarState', isExpanded ? 'expanded' : 'collapsed');
}

window.addEventListener('load', () => {
    document.body.classList.remove('preload');
    
    // --- LOGIC TOAST NOTIFICATION ---
    const toasts = document.querySelectorAll('.custom-toast');
    
    toasts.forEach(t => {
        // 1. Masuk
        setTimeout(() => {
            t.classList.add('active-toast');
        }, 100);

        const closeToast = () => {
            t.classList.remove('active-toast'); 
            setTimeout(() => {
                if (t.parentNode) t.parentNode.removeChild(t);
            }, 600); 
        };

        // 2. Auto Keluar
        const autoCloseTimer = setTimeout(closeToast, 5000);

        // 3. Manual Keluar
        const closeBtn = t.querySelector('.close-toast-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                clearTimeout(autoCloseTimer); 
                closeToast();
            });
        }
        
        // Cek jika kita sedang di halaman Login
        if (window.location.pathname.includes('/login')) {
            // Hapus ingatan posisi sidebar saat logout/login
            sessionStorage.removeItem('sidebarState');
            document.body.classList.remove('sb-expanded');
        }
    });
});