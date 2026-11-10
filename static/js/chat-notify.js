// Значок непрочитанных сообщений: живое обновление на любой странице через ws/notify/.
(function () {
    const badges = document.querySelectorAll('[data-chat-badge]');
    if (!badges.length || !('WebSocket' in window)) return;
    // на странице самого чата он и так открыт — но значок всё равно обновляем
    let retry = 0;

    function render(total) {
        badges.forEach((badge) => {
            badge.textContent = total > 99 ? '99+' : String(total);
            badge.hidden = !total;
        });
    }

    function connect() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const socket = new WebSocket(`${proto}://${location.host}/ws/notify/`);
        socket.onopen = () => { retry = 0; };
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'unread') render(data.total);
        };
        socket.onclose = (event) => {
            if (event.code === 4401) return;
            setTimeout(connect, Math.min(30000, 2000 * 2 ** retry++));
        };
    }

    connect();
})();
