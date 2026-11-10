// Фото (обложка мероприятия, аватар): предпросмотр и уменьшение в браузере до отправки.
// Снимок с телефона 4000×3000 / 5–8 МБ превращается в ~2000 px / 300–600 КБ,
// поэтому загрузка идёт в разы быстрее, а сервер сжимает меньше. Окончательную
// обработку (WebP, обрезка, удаление метаданных) всё равно делает сервер.
(function () {
    const MAX_BYTES = 5 * 1024 * 1024;
    const RESIZABLE = ['image/jpeg', 'image/webp'];

    async function decode(file) {
        if ('createImageBitmap' in window) {
            try { return await createImageBitmap(file, { imageOrientation: 'from-image' }); } catch (error) { /* fallback below */ }
        }
        const url = URL.createObjectURL(file);
        try {
            const img = new Image();
            img.src = url;
            await img.decode();
            return img;
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    async function shrink(file, maxSide) {
        if (!RESIZABLE.includes(file.type)) return file;
        const image = await decode(file);
        const width = image.width;
        const height = image.height;
        const k = Math.min(1, maxSide / Math.max(width, height));
        if (k === 1 && file.size <= 1024 * 1024) return file; // и так небольшое
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(width * k);
        canvas.height = Math.round(height * k);
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
        if (image.close) image.close();
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.88));
        if (!blob || blob.size >= file.size) return file;
        const name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
        return new File([blob], name, { type: 'image/jpeg', lastModified: Date.now() });
    }

    function replaceFile(input, file) {
        try {
            const transfer = new DataTransfer();
            transfer.items.add(file);
            input.files = transfer.files;
            return true;
        } catch (error) {
            return false; // старый браузер — отправим оригинал
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.photo-input').forEach((input) => {
            const drop = document.querySelector(`label.photo-drop[for="${input.id}"]`);
            if (!drop) return;
            const preview = drop.querySelector('.photo-preview');
            const maxSide = Number(input.dataset.maxSide || 2000);
            let busy = null;

            input.addEventListener('change', async () => {
                const original = input.files && input.files[0];
                if (!original) return;
                drop.classList.add('is-processing');
                let file = original;
                busy = (async () => {
                    try {
                        file = await shrink(original, maxSide);
                        if (file !== original && !replaceFile(input, file)) file = original;
                    } catch (error) {
                        file = original;
                    }
                })();
                await busy;
                busy = null;
                drop.classList.remove('is-processing');

                if (file.size > MAX_BYTES) {
                    alert(etT('Фото больше 5 МБ. Выберите файл поменьше.', 'The photo is larger than 5 MB. Choose a smaller file.', 'Fotka je větší než 5 MB. Vyberte menší soubor.'));
                    input.value = '';
                    return;
                }
                preview.src = URL.createObjectURL(file);
                drop.classList.add('has-photo');
                const remove = drop.parentElement.querySelector('input[name="remove_cover"], input[name="remove_avatar"]');
                if (remove) remove.checked = false;
                if (input.dataset.autosubmit !== undefined) input.form.submit();
            });

            // Если отправили форму, пока фото ещё уменьшается, — дождаться
            if (input.form) {
                input.form.addEventListener('submit', async (event) => {
                    if (!busy || input.form.dataset.waited) return;
                    event.preventDefault();
                    await busy;
                    input.form.dataset.waited = '1';
                    input.form.requestSubmit ? input.form.requestSubmit() : input.form.submit();
                });
            }
        });
    });
})();
