/**
 * Django Admin Custom JavaScript
 * 管理画面のサイドバー制御とインタラクション
 */

document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const hamburgerMenu = document.getElementById('hamburgerMenu');
    const sidebar = document.getElementById('premiumSidebar');
    const mobileBackdrop = document.getElementById('mobileOverlayBackdrop');
    const body = document.body;
    
    // State management
    let sidebarState = {
        isCollapsed: true, // デフォルトで折りたたまれている
        isMobile: window.innerWidth <= 1200,
        autoHideTimer: null,
        isOverlay: false,
        isShowing: false // サイドバーが表示されているかどうか
    };
    
    // Initialize sidebar state
    function initializeSidebar() {
        updateSidebarState();
        // デフォルトでサイドバーは非表示
        sidebar.classList.add('collapsed');
        body.classList.add('sidebar-collapsed');
        updateToggleIcon();
    }
    
    // Update sidebar state based on screen size
    function updateSidebarState() {
        const oldIsMobile = sidebarState.isMobile;
        sidebarState.isMobile = window.innerWidth <= 1200;
        
        if (oldIsMobile !== sidebarState.isMobile) {
            // Screen size category changed
            if (sidebarState.isMobile) {
                // Switched to mobile
                sidebar.classList.add('collapsed');
                body.classList.remove('sidebar-collapsed');
                sidebarState.isCollapsed = true;
                hideMobileSidebar();
            } else {
                // Switched to desktop
                sidebar.classList.remove('mobile-show', 'collapsed');
                mobileBackdrop.classList.remove('active');
                body.classList.remove('sidebar-overlay');
                sidebarState.isCollapsed = false;
                sidebarState.isOverlay = false;
            }
        }
    }
    
    // Toggle sidebar
    function toggleSidebar() {
        if (sidebarState.isMobile) {
            toggleMobileSidebar();
        } else {
            toggleDesktopSidebar();
        }
        updateToggleIcon();
        
        // Save preference to localStorage
        localStorage.setItem('sidebarCollapsed', sidebarState.isCollapsed);
    }

    // Toggle sidebar with hamburger menu
    function toggleSidebarWithHamburger() {
        if (sidebarState.isShowing) {
            hideSidebar();
        } else {
            showSidebar();
        }
        updateHamburgerIcon();
    }

    // Show sidebar
    function showSidebar() {
        sidebarState.isShowing = true;
        sidebarState.isCollapsed = false;
        sidebar.classList.remove('collapsed');
        sidebar.classList.add('show');
        body.classList.remove('sidebar-collapsed', 'sidebar-overlay');
        body.classList.add('sidebar-show');
    }

    // Hide sidebar
    function hideSidebar() {
        sidebarState.isShowing = false;
        sidebarState.isCollapsed = true;
        sidebar.classList.add('collapsed');
        sidebar.classList.remove('show');
        body.classList.add('sidebar-collapsed');
        body.classList.remove('sidebar-show', 'sidebar-overlay');
    }
    
    // Toggle desktop sidebar
    function toggleDesktopSidebar() {
        sidebarState.isCollapsed = !sidebarState.isCollapsed;
        
        if (sidebarState.isCollapsed) {
            body.classList.add('sidebar-collapsed');
            body.classList.remove('sidebar-show', 'sidebar-overlay');
            sidebar.classList.add('collapsed');
            sidebar.classList.remove('show');
            sidebarState.isOverlay = false;
        } else {
            body.classList.remove('sidebar-collapsed');
            body.classList.add('sidebar-show');
            body.classList.remove('sidebar-overlay');
            sidebar.classList.remove('collapsed');
            sidebar.classList.add('show');
            sidebarState.isOverlay = false;
        }
    }
    
    // Toggle mobile sidebar
    function toggleMobileSidebar() {
        const isShowing = sidebar.classList.contains('mobile-show');
        
        if (isShowing) {
            hideMobileSidebar();
        } else {
            showMobileSidebar();
        }
    }
    
    // Show mobile sidebar
    function showMobileSidebar() {
        sidebar.classList.add('mobile-show');
        mobileBackdrop.classList.add('active');
        body.classList.add('sidebar-overlay');
        body.style.overflow = 'hidden';
    }
    
    // Hide mobile sidebar
    function hideMobileSidebar() {
        sidebar.classList.remove('mobile-show');
        mobileBackdrop.classList.remove('active');
        body.classList.remove('sidebar-overlay');
        body.style.overflow = '';
    }
    
    // Update toggle icon
    function updateToggleIcon() {
        const icon = sidebarToggle.querySelector('i');
        
        if (sidebarState.isMobile) {
            const isShowing = sidebar.classList.contains('mobile-show');
            icon.className = isShowing ? 'fas fa-times' : 'fas fa-bars';
            sidebarToggle.classList.toggle('active', isShowing);
        } else {
            const isShowing = sidebar.classList.contains('collapsed');
            icon.className = isShowing ? 'fas fa-bars' : 'fas fa-times';
            sidebarToggle.classList.toggle('active', !isShowing);
        }
    }

    // Update hamburger icon
    function updateHamburgerIcon() {
        const icon = hamburgerMenu.querySelector('i');
        icon.className = sidebarState.isShowing ? 'fas fa-times' : 'fas fa-bars';
        hamburgerMenu.classList.toggle('active', sidebarState.isShowing);
    }
    
    // Auto-hide functionality for desktop
    function setupAutoHide() {
        if (!sidebarState.isMobile && sidebarState.isCollapsed) {
            sidebar.addEventListener('mouseenter', showTemporary);
            sidebar.addEventListener('mouseleave', hideTemporary);
        } else {
            sidebar.removeEventListener('mouseenter', showTemporary);
            sidebar.removeEventListener('mouseleave', hideTemporary);
        }
    }
    
    function showTemporary() {
        if (sidebarState.isCollapsed && !sidebarState.isMobile) {
            clearTimeout(sidebarState.autoHideTimer);
            sidebar.style.transform = 'translateX(0)';
            sidebar.style.zIndex = '1002';
            body.classList.add('sidebar-overlay');
        }
    }
    
    function hideTemporary() {
        if (sidebarState.isCollapsed && !sidebarState.isMobile) {
            sidebarState.autoHideTimer = setTimeout(() => {
                sidebar.style.transform = 'translateX(-100%)';
                sidebar.style.zIndex = '1001';
                body.classList.remove('sidebar-overlay');
            }, 300);
        }
    }
    
    // Load saved preference
    function loadSavedPreference() {
        const saved = localStorage.getItem('sidebarCollapsed');
        if (saved !== null && !sidebarState.isMobile) {
            sidebarState.isCollapsed = saved === 'true';
            if (sidebarState.isCollapsed) {
                body.classList.add('sidebar-collapsed');
                sidebar.classList.add('collapsed');
            } else {
                body.classList.add('sidebar-overlay');
            }
        }
    }
    
    // Event listeners
    sidebarToggle.addEventListener('click', toggleSidebar);
    hamburgerMenu.addEventListener('click', toggleSidebarWithHamburger);
    
    // Close mobile sidebar when clicking backdrop
    mobileBackdrop.addEventListener('click', hideMobileSidebar);
    
    // Close mobile sidebar when clicking outside
    document.addEventListener('click', function(e) {
        if (sidebarState.isMobile && 
            sidebar.classList.contains('mobile-show') &&
            !sidebar.contains(e.target) && 
            !sidebarToggle.contains(e.target)) {
            hideMobileSidebar();
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        clearTimeout(sidebarState.autoHideTimer);
        updateSidebarState();
        setupAutoHide();
        updateToggleIcon();
    });
    
    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebarState.isMobile && sidebar.classList.contains('mobile-show')) {
            hideMobileSidebar();
        }
    });
    
    // Active navigation highlighting
    function highlightActiveNavigation() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && currentPath.includes(href) && href !== '/admin/') {
                link.classList.add('active');
            } else if (href === '/admin/' && currentPath === '/admin/') {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }
    
    // Touch gesture support for mobile
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    });
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipeGesture();
    });
    
    function handleSwipeGesture() {
        const swipeThreshold = 100;
        const swipeDistance = touchEndX - touchStartX;
        
        if (sidebarState.isMobile) {
            if (swipeDistance > swipeThreshold && touchStartX < 50) {
                // Swipe right from left edge - show sidebar
                showMobileSidebar();
            } else if (swipeDistance < -swipeThreshold && sidebar.classList.contains('mobile-show')) {
                // Swipe left - hide sidebar
                hideMobileSidebar();
            }
        }
    }
    
    // Initialize everything
    loadSavedPreference();
    initializeSidebar();
    updateHamburgerIcon();
    setupAutoHide();
    highlightActiveNavigation();
});
