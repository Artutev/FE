// Конструктор пригласительного: живое превью без перезагрузки.
(function () {
    const form = document.getElementById('cardForm');
    const stage = document.getElementById('previewStage');
    if (!form || !stage) return;
    const card = stage.querySelector('.ic');
    const catalog = JSON.parse(document.getElementById('cardCatalog').textContent);
    const paletteList = document.getElementById('paletteList');
    const accentPicker = document.getElementById('accentPicker');
    const accentInput = document.getElementById('accentInput');
    const accentReset = document.getElementById('accentReset');

    const value = (name) => (form.querySelector(`[name="${name}"]:checked`) || {}).value;
    const refresh = () => window.InviteCard && window.InviteCard.refresh(stage.parentElement);

    function applyColors() {
        const tpl = catalog.templates[value('template')];
        const pal = tpl.palettes[value('palette')] || Object.values(tpl.palettes)[0];
        card.style.setProperty('--ic-bg', pal.bg);
        card.style.setProperty('--ic-bg2', pal.bg2);
        card.style.setProperty('--ic-fg', pal.fg);
        card.style.setProperty('--ic-muted', pal.muted);
        card.style.setProperty('--ic-accent', accentInput.value || pal.accent);
        if (!accentInput.value) accentPicker.value = pal.accent;
    }

    function applyFont() {
        const font = catalog.fonts[value('font')];
        if (!font) return;
        card.style.setProperty('--ic-display', `'${font.display}'`);
        card.style.setProperty('--ic-body', `'${font.body}'`);
    }

    function applyClasses() {
        card.className = `ic ic--${value('template')} ic-bg--${value('background')}`;
        card.dataset.format = value('format');
    }

    function renderPalettes(templateKey, keepSlug) {
        const palettes = catalog.templates[templateKey].palettes;
        const slugs = Object.keys(palettes);
        const selected = slugs.includes(keepSlug) ? keepSlug : slugs[0];
        paletteList.innerHTML = '';
        slugs.forEach((slug) => {
            const p = palettes[slug];
            const label = document.createElement('label');
            label.className = 'ce-swatch';
            label.title = p.name;
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = 'palette';
            input.value = slug;
            input.checked = slug === selected;
            const dot = document.createElement('span');
            dot.className = 'ce-swatch-dot';
            dot.style.setProperty('--a', p.bg);
            dot.style.setProperty('--b', p.bg2);
            dot.style.setProperty('--c', p.accent);
            const name = document.createElement('span');
            name.className = 'ce-swatch-name';
            name.textContent = p.name;
            label.append(input, dot, name);
            paletteList.appendChild(label);
        });
    }

    function applyAll() {
        applyClasses();
        applyColors();
        applyFont();
        refresh();
    }

    form.addEventListener('change', (event) => {
        const target = event.target;
        if (target.name === 'template') {
            renderPalettes(target.value, value('palette'));
            const defaultFont = catalog.templates[target.value].font;
            const fontInput = form.querySelector(`[name="font"][value="${defaultFont}"]`);
            if (fontInput) fontInput.checked = true;
        }
        if (target === accentPicker) return;
        applyAll();
    });

    accentPicker.addEventListener('input', () => {
        accentInput.value = accentPicker.value.toUpperCase();
        accentReset.hidden = false;
        applyColors();
    });

    accentReset.addEventListener('click', () => {
        accentInput.value = '';
        accentReset.hidden = true;
        applyColors();
    });

    // Тексты: сразу в карточку (textContent — без HTML)
    form.querySelectorAll('[data-bind-input]').forEach((input) => {
        input.addEventListener('input', () => {
            const key = input.dataset.bindInput;
            const target = card.querySelector(`[data-bind="${key}"]`);
            if (!target) return;
            target.textContent = input.value || (key === 'title' ? '…' : '');
            target.hidden = !input.value && key !== 'title';
            if (window.InviteCard) window.InviteCard.fit(card);
        });
    });
})();
