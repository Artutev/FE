// Пригласительное: подгонка текста под «холст», масштаб превью, скачивание PNG и печать.
(function () {
    const HTML_TO_IMAGE = 'https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js';

    function size(card) {
        const style = getComputedStyle(card);
        return { w: parseFloat(style.getPropertyValue('--ic-w')), h: parseFloat(style.getPropertyValue('--ic-h')) };
    }

    // Длинный заголовок/текст уменьшаем, пока всё не влезет в карточку
    function fit(card) {
        const content = card.querySelector('.ic-content');
        const title = card.querySelector('.ic-title');
        const message = card.querySelector('.ic-message');
        if (!content || !title) return;
        title.style.fontSize = '';
        if (message) message.style.fontSize = '';
        const overflowing = () => content.scrollHeight > content.clientHeight + 1;
        // Слово не должно рваться посреди: меряем без переноса внутри слов
        title.style.overflowWrap = 'normal';
        title.style.wordBreak = 'normal';
        const wordTooWide = () => title.scrollWidth > title.clientWidth + 1;
        let titleSize = parseFloat(getComputedStyle(title).fontSize);
        while ((overflowing() || wordTooWide()) && titleSize > 24) {
            titleSize -= 2;
            title.style.fontSize = `${titleSize}px`;
        }
        // Совсем длинное слово — уже на минимальном размере разрешаем перенос
        title.style.overflowWrap = '';
        title.style.wordBreak = '';
        if (message) {
            let messageSize = parseFloat(getComputedStyle(message).fontSize);
            while (overflowing() && messageSize > 13) {
                messageSize -= 1;
                message.style.fontSize = `${messageSize}px`;
            }
        }
    }

    // Вписать карточку в контейнер .ic-stage (ширина контейнера, высота не больше maxHeight)
    function scale(stage) {
        const card = stage.querySelector('.ic');
        if (!card) return;
        const { w, h } = size(card);
        let maxHeight = parseFloat(stage.dataset.maxHeight || '0') || Infinity;
        // На узком экране превью не больше доли высоты окна (data-mobile-vh="0.5")
        const vh = parseFloat(stage.dataset.mobileVh || '0');
        if (vh && window.innerWidth <= 640) maxHeight = Math.min(maxHeight, window.innerHeight * vh);
        const k = Math.min(1, stage.clientWidth / w, maxHeight / h);
        card.style.transform = `scale(${k})`;
        card.style.transformOrigin = 'top left';
        stage.style.height = `${h * k}px`;
        const holder = stage.querySelector('.ic-stage-inner');
        if (holder) holder.style.width = `${w * k}px`;
    }

    function refresh(root = document) {
        root.querySelectorAll('.ic-stage').forEach((stage) => {
            const card = stage.querySelector('.ic');
            if (card) fit(card);
            scale(stage);
        });
    }

    let loader = null;
    function loadLib() {
        if (window.htmlToImage) return Promise.resolve(window.htmlToImage);
        if (!loader) {
            loader = new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = HTML_TO_IMAGE;
                script.onload = () => resolve(window.htmlToImage);
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }
        return loader;
    }

    async function download(card, filename) {
        const lib = await loadLib();
        await document.fonts.ready;
        const { w, h } = size(card);
        const url = await lib.toPng(card, {
            width: w,
            height: h,
            pixelRatio: 2,
            cacheBust: true,
            style: { transform: 'none', margin: '0' },
        });
        const link = document.createElement('a');
        link.href = url;
        link.download = filename || 'invitation.png';
        document.body.appendChild(link);
        link.click();
        link.remove();
    }

    window.InviteCard = { fit, scale, refresh, download };

    document.addEventListener('DOMContentLoaded', () => {
        refresh();
        if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => refresh());
        let timer;
        window.addEventListener('resize', () => {
            clearTimeout(timer);
            timer = setTimeout(() => refresh(), 120);
        });

        document.querySelectorAll('[data-card-download]').forEach((button) => {
            button.addEventListener('click', async () => {
                const card = document.querySelector(button.dataset.cardDownload);
                if (!card) return;
                const label = button.innerHTML;
                button.disabled = true;
                try {
                    await download(card, button.dataset.filename);
                } catch (error) {
                    console.error('PNG export failed', error);
                    alert(etT('Не получилось сохранить картинку. Попробуйте ещё раз.', "Couldn't save the image. Please try again.", 'Obrázek se nepodařilo uložit. Zkuste to znovu.'));
                } finally {
                    button.disabled = false;
                    button.innerHTML = label;
                }
            });
        });

        document.querySelectorAll('[data-card-print]').forEach((button) => {
            button.addEventListener('click', () => window.print());
        });
    });
})();
