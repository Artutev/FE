// Чат EventTown: WebSocket с переподключением, «печатает…», в сети, подгрузка истории, ✓/✓✓ прочитано.
(function () {
    const room = document.getElementById('chatRoom');
    if (!room) return;

    const me = Number(room.dataset.me);
    const kind = room.dataset.kind;
    const conversationId = room.dataset.conversation;
    const feed = document.getElementById('chatFeed');
    const scroller = document.getElementById('chatScroll');
    const form = document.getElementById('chatForm');
    const input = document.getElementById('chatInput');
    const typingEl = document.getElementById('chatTyping');
    const statusEl = document.getElementById('chatStatus');
    const onlineEl = document.getElementById('chatOnline');
    const connEl = document.getElementById('chatConn');
    let moreBtn = document.getElementById('chatMore');
    let hasMore = room.dataset.hasMore === '1';

    const T = {
        today: etT('Сегодня', 'Today', 'Dnes'),
        yesterday: etT('Вчера', 'Yesterday', 'Včera'),
        typing: etT('печатает…', 'is typing…', 'píše…'),
        online: etT('в чате', 'here now', 'v chatu'),
        away: etT('не в чате', 'away', 'není v chatu'),
        onlineCount: etT('сейчас в чате: ', 'here now: ', 'právě v chatu: '),
        failed: etT('Не отправлено. Нажмите, чтобы повторить.', 'Not sent. Tap to retry.', 'Neodesláno. Klepnutím zopakujete.'),
        rate: etT('Слишком много сообщений подряд, подождите немного.', 'Too many messages in a row, wait a moment.', 'Příliš mnoho zpráv za sebou, chvíli počkejte.'),
        forbidden: etT('Писать в этот чат больше нельзя.', "You can't write in this chat anymore.", 'Do tohoto chatu už psát nemůžete.'),
        sent: etT('Отправлено', 'Sent', 'Odesláno'),
        read: etT('Прочитано', 'Read', 'Přečteno'),
        readBy: etT('Прочитали: ', 'Read by: ', 'Přečetli: '),
    };

    // ---------- read receipts ----------
    // user_id -> до какого момента (мс) участник дочитал чат
    const reads = new Map();
    Object.entries(JSON.parse((document.getElementById('chatReads') || {}).textContent || '{}'))
        .forEach(([userId, iso]) => reads.set(Number(userId), Date.parse(iso)));

    function markRead(userId, ms) {
        if (!userId || userId === me || !ms) return false;
        if ((reads.get(userId) || 0) >= ms) return false;
        reads.set(userId, ms);
        return true;
    }

    function readersOf(ms) {
        let count = 0;
        reads.forEach((readAt, userId) => { if (userId !== me && readAt >= ms) count += 1; });
        return count;
    }

    const TICK_ONE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 12.5l4.5 4.5L19.5 6.5"/></svg>';
    const TICK_TWO = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1.5 12.5l4.5 4.5L16 7"/><path d="M10.5 16l1 1L22 6.5"/></svg>';

    function paintTick(row) {
        const tick = row.querySelector('.ch-tick');
        if (!tick) return;
        const count = readersOf(Number(row.dataset.ts));
        const isRead = count > 0;
        if (tick.dataset.read === String(isRead) && tick.dataset.count === String(count)) return;
        tick.dataset.read = String(isRead);
        tick.dataset.count = String(count);
        tick.innerHTML = isRead ? TICK_TWO : TICK_ONE;
        const label = !isRead ? T.sent : kind === 'event' ? `${T.readBy}${count}` : T.read;
        tick.title = label;
        tick.setAttribute('aria-label', label);
    }

    function paintTicks() {
        feed.querySelectorAll('.ch-msg.is-mine[data-id]').forEach(paintTick);
    }

    const timeFmt = new Intl.DateTimeFormat(window.etLocale || undefined, { hour: '2-digit', minute: '2-digit' });
    const dayFmt = new Intl.DateTimeFormat(window.etLocale || undefined, { day: 'numeric', month: 'long' });
    const seen = new Set();
    let lastDayKey = null;
    let firstDayKey = null;

    // ---------- rendering ----------
    function dayKey(date) { return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`; }

    function dayLabel(date) {
        const now = new Date();
        const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1);
        if (dayKey(date) === dayKey(now)) return T.today;
        if (dayKey(date) === dayKey(yesterday)) return T.yesterday;
        return dayFmt.format(date);
    }

    function daySeparator(date) {
        const el = document.createElement('div');
        el.className = 'ch-day';
        el.textContent = dayLabel(date);
        return el;
    }

    function avatarEl(author) {
        const el = document.createElement('span');
        el.className = 'avatar avatar--sm';
        if (author.avatar) {
            const img = document.createElement('img');
            img.src = author.avatar; img.alt = '';
            el.appendChild(img);
        } else {
            el.textContent = (author.username || '?').charAt(0).toUpperCase();
        }
        return el;
    }

    function bubble(message, pending) {
        const mine = message.author && message.author.id === me;
        const row = document.createElement('div');
        row.className = 'ch-msg' + (mine ? ' is-mine' : '') + (pending ? ' is-pending' : '');
        if (message.id) row.dataset.id = message.id;
        if (!mine && kind === 'event') row.appendChild(avatarEl(message.author));
        const body = document.createElement('div');
        body.className = 'ch-bubble';
        if (!mine && kind === 'event') {
            const name = document.createElement('span');
            name.className = 'ch-author';
            name.textContent = message.author.username;
            body.appendChild(name);
        }
        const text = document.createElement('span');
        text.className = 'ch-text';
        text.textContent = message.text; // только textContent — никакого HTML от пользователей
        body.appendChild(text);
        const meta = document.createElement('span');
        meta.className = 'ch-meta';
        const time = document.createElement('time');
        time.className = 'ch-time';
        const date = new Date(message.created_at || Date.now());
        time.dateTime = date.toISOString();
        time.textContent = timeFmt.format(date);
        meta.appendChild(time);
        if (mine && message.id) {
            row.dataset.ts = String(date.getTime());
            const tick = document.createElement('span');
            tick.className = 'ch-tick';
            tick.setAttribute('role', 'img');
            meta.appendChild(tick);
        }
        body.appendChild(meta);
        row.appendChild(body);
        if (mine && message.id) paintTick(row);
        return row;
    }

    function nearBottom() {
        return scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 120;
    }

    function scrollToBottom() { scroller.scrollTop = scroller.scrollHeight; }

    function append(message, pending) {
        if (message.id && seen.has(message.id)) return null;
        if (message.id) seen.add(message.id);
        const date = new Date(message.created_at || Date.now());
        if (dayKey(date) !== lastDayKey) {
            feed.appendChild(daySeparator(date));
            lastDayKey = dayKey(date);
            if (!firstDayKey) firstDayKey = lastDayKey;
        }
        if (message.author && message.id) markRead(message.author.id, date.getTime());
        const el = bubble(message, pending);
        feed.appendChild(el);
        return el;
    }

    function prepend(messages) {
        const anchor = moreBtn ? moreBtn.nextSibling : feed.firstChild;
        const fragment = document.createDocumentFragment();
        let prevKey = null;
        messages.forEach((message) => {
            if (seen.has(message.id)) return;
            seen.add(message.id);
            const date = new Date(message.created_at);
            if (dayKey(date) !== prevKey) {
                fragment.appendChild(daySeparator(date));
                prevKey = dayKey(date);
            }
            fragment.appendChild(bubble(message, false));
        });
        // убрать дублирующийся разделитель дня на стыке
        if (prevKey && prevKey === firstDayKey && anchor && anchor.classList && anchor.classList.contains('ch-day')) {
            anchor.remove();
        }
        firstDayKey = messages.length ? dayKey(new Date(messages[0].created_at)) : firstDayKey;
        const before = scroller.scrollHeight;
        feed.insertBefore(fragment, moreBtn ? moreBtn.nextSibling : feed.firstChild);
        scroller.scrollTop += scroller.scrollHeight - before;
    }

    // initial history
    const initial = JSON.parse(document.getElementById('chatInitial').textContent || '[]');
    initial.forEach((m) => append(m, false));
    paintTicks();
    scrollToBottom();

    // ---------- older messages ----------
    async function loadOlder() {
        if (!hasMore || !moreBtn) return;
        const first = feed.querySelector('.ch-msg[data-id]');
        const url = new URL(room.dataset.olderUrl, location.origin);
        if (first) url.searchParams.set('before', first.dataset.id);
        moreBtn.disabled = true;
        try {
            const data = await (await fetch(url, { credentials: 'same-origin' })).json();
            prepend(data.messages);
            hasMore = data.has_more;
        } finally {
            moreBtn.disabled = false;
            if (!hasMore) { moreBtn.remove(); moreBtn = null; }
        }
    }
    if (moreBtn) moreBtn.addEventListener('click', loadOlder);
    scroller.addEventListener('scroll', () => { if (scroller.scrollTop < 40) loadOlder(); });

    // ---------- socket ----------
    let socket = null;
    let retry = 0;
    const pending = new Map(); // client_id -> {el, text}

    function setConn(state) { if (connEl) connEl.dataset.state = state; }

    function connect() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        socket = new WebSocket(`${proto}://${location.host}/ws/chat/${conversationId}/`);
        setConn('connecting');
        socket.onopen = () => {
            retry = 0;
            setConn('open');
            send({ type: 'read' });
            // переотправить то, что не ушло, пока не было связи
            pending.forEach((item, clientId) => send({ type: 'message', text: item.text, client_id: clientId }));
        };
        socket.onmessage = (event) => handle(JSON.parse(event.data));
        socket.onclose = (event) => {
            setConn('closed');
            if (event.code === 4401 || event.code === 4403) return; // нет доступа — не переподключаемся
            const delay = Math.min(15000, 1000 * 2 ** retry++);
            setTimeout(connect, delay);
        };
    }

    function send(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
            return true;
        }
        return false;
    }

    let typingTimer = null;
    function handle(data) {
        if (data.type === 'message') {
            const item = data.client_id && pending.get(data.client_id);
            if (item) {
                item.el.remove();
                pending.delete(data.client_id);
            }
            const stick = nearBottom() || (data.message.author && data.message.author.id === me);
            append(data.message, false);
            if (stick) scrollToBottom();
            if (data.message.author && data.message.author.id !== me) {
                paintTicks();
                hideTyping();
                if (document.visibilityState === 'visible') send({ type: 'read' });
            }
        } else if (data.type === 'read') {
            if (markRead(data.user_id, Date.parse(data.read_at))) paintTicks();
        } else if (data.type === 'typing') {
            showTyping(data.username);
        } else if (data.type === 'presence') {
            const others = data.online.filter((id) => id !== me);
            if (statusEl) {
                statusEl.textContent = others.length ? T.online : T.away;
                statusEl.classList.toggle('is-online', others.length > 0);
            }
            if (onlineEl) onlineEl.textContent = others.length ? `${T.onlineCount}${others.length + 1} · ` : '';
        } else if (data.type === 'error') {
            const text = data.code === 'rate_limited' ? T.rate : data.code === 'forbidden' ? T.forbidden : data.detail;
            pending.forEach((item) => markFailed(item));
            alertBar(text);
        }
    }

    function showTyping(name) {
        typingEl.textContent = kind === 'event' ? `${name} ${T.typing}` : T.typing;
        typingEl.hidden = false;
        clearTimeout(typingTimer);
        typingTimer = setTimeout(hideTyping, 4000);
    }

    function hideTyping() { typingEl.hidden = true; }

    function alertBar(text) {
        typingEl.textContent = text;
        typingEl.hidden = false;
        typingEl.classList.add('is-error');
        setTimeout(() => { typingEl.classList.remove('is-error'); hideTyping(); }, 4000);
    }

    function markFailed(item) {
        item.el.classList.add('is-failed');
        item.el.title = T.failed;
    }

    // ---------- sending ----------
    async function postFallback(clientId, text) {
        const body = new URLSearchParams({ text, client_id: clientId });
        const token = (document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/) || [])[1];
        const response = await fetch(room.dataset.sendUrl, {
            method: 'POST', credentials: 'same-origin', body,
            headers: { 'X-CSRFToken': token ? decodeURIComponent(token) : '' },
        });
        if (!response.ok) throw new Error('send failed');
        const data = await response.json();
        handle({ type: 'message', message: data.message, client_id: clientId });
    }

    function submit() {
        const text = input.value.trim();
        if (!text) return;
        const clientId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const el = append({ text, created_at: new Date().toISOString(), author: { id: me } }, true);
        pending.set(clientId, { el, text });
        scrollToBottom();
        input.value = '';
        autosize();
        if (!send({ type: 'message', text, client_id: clientId })) {
            postFallback(clientId, text).catch(() => markFailed(pending.get(clientId)));
        }
    }

    feed.addEventListener('click', (event) => {
        const failed = event.target.closest('.ch-msg.is-failed');
        if (!failed) return;
        pending.forEach((item, clientId) => {
            if (item.el === failed) {
                failed.classList.remove('is-failed');
                if (!send({ type: 'message', text: item.text, client_id: clientId })) {
                    postFallback(clientId, item.text).catch(() => markFailed(item));
                }
            }
        });
    });

    function autosize() {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 160) + 'px';
        input.style.overflowY = input.scrollHeight > 160 ? 'auto' : 'hidden';
    }

    if (form) {
        let lastTyping = 0;
        form.addEventListener('submit', (event) => { event.preventDefault(); submit(); });
        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
                event.preventDefault();
                submit();
            }
        });
        input.addEventListener('input', () => {
            autosize();
            if (Date.now() - lastTyping > 2500) {
                lastTyping = Date.now();
                send({ type: 'typing' });
            }
        });
        if (window.matchMedia('(pointer: fine)').matches) input.focus();
    }

    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') send({ type: 'read' });
    });

    connect();
})();
