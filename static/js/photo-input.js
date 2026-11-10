// Предпросмотр выбранного фото (обложка мероприятия, аватар) до отправки формы.
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.photo-input').forEach((input) => {
        const drop = document.querySelector(`label.photo-drop[for="${input.id}"]`);
        if (!drop) return;
        const preview = drop.querySelector('.photo-preview');
        input.addEventListener('change', () => {
            const file = input.files && input.files[0];
            if (!file) return;
            if (file.size > 5 * 1024 * 1024) {
                alert(etT('Фото больше 5 МБ. Выберите файл поменьше.', 'The photo is larger than 5 MB. Choose a smaller file.', 'Fotka je větší než 5 MB. Vyberte menší soubor.'));
                input.value = '';
                return;
            }
            const url = URL.createObjectURL(file);
            preview.src = url;
            drop.classList.add('has-photo');
            const remove = drop.parentElement.querySelector('input[name="remove_cover"], input[name="remove_avatar"]');
            if (remove) remove.checked = false;
            if (input.dataset.autosubmit !== undefined) input.form.submit();
        });
    });
});
