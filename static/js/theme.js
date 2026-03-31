// Theme Switcher
(function() {
    const THEME_KEY = 'theme_preference';
    const DARK_MODE_CLASS = 'dark-mode';
    
    // Get saved theme preference or detect from system
    function getPreferredTheme() {
        const saved = localStorage.getItem(THEME_KEY);
        if (saved) {
            return saved;
        }
        
        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        
        return 'light';
    }
    
    // Apply theme to DOM
    function applyTheme(theme) {
        const html = document.documentElement;
        
        if (theme === 'dark') {
            html.classList.add(DARK_MODE_CLASS);
        } else {
            html.classList.remove(DARK_MODE_CLASS);
        }
        
        // Save preference
        localStorage.setItem(THEME_KEY, theme);
    }
    
    // Initialize theme on page load
    function initTheme() {
        const theme = getPreferredTheme();
        applyTheme(theme);
    }
    
    // Toggle theme
    function toggleTheme() {
        const html = document.documentElement;
        const isDark = html.classList.contains(DARK_MODE_CLASS);
        const newTheme = isDark ? 'light' : 'dark';
        
        applyTheme(newTheme);
        updateButtonIcon();
    }
    
    // Update button icon based on current theme
    function updateButtonIcon() {
        const button = document.getElementById('theme-toggle-btn');
        if (!button) return;
        
        const isDark = document.documentElement.classList.contains(DARK_MODE_CLASS);
        button.textContent = isDark ? '☀️' : '🌙';
        button.setAttribute('aria-label', isDark ? 'Переключить на светлую тему' : 'Переключить на темную тему');
    }
    
    // Listen for system theme changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(THEME_KEY)) {
                applyTheme(e.matches ? 'dark' : 'light');
                updateButtonIcon();
            }
        });
    }
    
    // Make functions globally available
    window.themeToggle = {
        init: initTheme,
        toggle: toggleTheme,
        updateIcon: updateButtonIcon
    };
    
    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initTheme();
            updateButtonIcon();
        });
    } else {
        initTheme();
        updateButtonIcon();
    }
    
    // Initialize immediately to prevent flashing
    initTheme();
})();
