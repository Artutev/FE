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
                const nextPanel = documentFragment.querySelector('[data-panel="all"]');
                const currentPanel = document.querySelector('[data-panel="all"]');
                if (nextPanel && currentPanel) currentPanel.replaceWith(nextPanel);
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

    tabs.forEach((tab) => tab.addEventListener('click', () => {
        const selectedTab = tab.dataset.tab;
        tabs.forEach((item) => item.classList.toggle('is-active', item === tab));
        panels.forEach((panel) => panel.classList.toggle('is-active', panel.dataset.panel === selectedTab));
    }));
});