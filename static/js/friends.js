document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.friends-tab');
    const panels = document.querySelectorAll('.friends-panel');
    const searchForm = document.getElementById('friendsSearchForm');
    const searchInput = searchForm ? searchForm.querySelector('input[name="q"]') : null;

    if (!tabs.length || !panels.length) return;

    if (searchInput && searchForm) {
        let searchTimer;
        let activeSearchRequest;

        const updateUsersPanel = async (url) => {
            if (activeSearchRequest) activeSearchRequest.abort();
            activeSearchRequest = new AbortController();
            try {
                const response = await fetch(url, {
                    headers: {'X-Requested-With': 'XMLHttpRequest'},
                    signal: activeSearchRequest.signal,
                });
                if (!response.ok) return;
                const html = await response.text();
                const documentFragment = new DOMParser().parseFromString(html, 'text/html');
                // заменяем только результаты, чтобы поле поиска не теряло фокус
                const nextResults = documentFragment.querySelector('[data-results]');
                const currentResults = document.querySelector('[data-results]');
                if (nextResults && currentResults) currentResults.replaceWith(nextResults);
            } catch (error) {
                if (error.name !== 'AbortError') console.error('User search failed:', error);
            }
        };

        searchInput.addEventListener('input', () => {
            window.clearTimeout(searchTimer);
            searchTimer = window.setTimeout(() => {
                const url = new URL(window.location.href);
                url.searchParams.set('q', searchInput.value.trim());
                url.searchParams.delete('page');
                window.history.replaceState({}, '', url);
                updateUsersPanel(url);
            }, 450);
        });

        searchForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const url = new URL(window.location.href);
            url.searchParams.set('q', searchInput.value.trim());
            url.searchParams.delete('page');
            window.history.replaceState({}, '', url);
            updateUsersPanel(url);
        });

        document.addEventListener('click', (event) => {
            const pageLink = event.target.closest('.friends-page-arrow');
            if (!pageLink) return;
            event.preventDefault();
            updateUsersPanel(pageLink.href);
            window.history.replaceState({}, '', pageLink.href);
        });
    }

    const showTab = (name) => {
        tabs.forEach((item) => {
            const on = item.dataset.tab === name;
            item.classList.toggle('is-active', on);
            item.setAttribute('aria-selected', String(on));
        });
        panels.forEach((panel) => panel.classList.toggle('is-active', panel.dataset.panel === name));
        if (name === 'all' && searchInput && window.matchMedia('(pointer: fine)').matches) searchInput.focus();
    };

    tabs.forEach((tab) => tab.addEventListener('click', () => showTab(tab.dataset.tab)));
    document.querySelectorAll('[data-go-tab]').forEach((button) => {
        button.addEventListener('click', () => showTab(button.dataset.goTab));
    });

    document.querySelectorAll('form[data-confirm]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            if (!window.confirm(form.dataset.confirm)) event.preventDefault();
        });
    });
});