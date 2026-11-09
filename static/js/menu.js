document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('menuToggle');
    const menu = document.getElementById('headerMenu');

    if (!toggle || !menu) return;

    const closeMenu = () => {
        menu.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
    };

    toggle.addEventListener('click', () => {
        const isOpen = menu.classList.toggle('is-open');
        toggle.setAttribute('aria-expanded', String(isOpen));
    });

    menu.addEventListener('click', (event) => {
        if (event.target.closest('a')) closeMenu();
    });

    document.addEventListener('click', (event) => {
        if (!menu.contains(event.target) && !toggle.contains(event.target)) closeMenu();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeMenu();
    });

    // Language dropdown: close on outside click / Escape
    document.querySelectorAll('.lang-menu').forEach((details) => {
        document.addEventListener('click', (event) => {
            if (!details.contains(event.target)) details.removeAttribute('open');
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') details.removeAttribute('open');
        });
    });
});