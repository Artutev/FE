const EYE_ICON = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>';
const EYE_OFF_ICON = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18M10.6 5.1A10.6 10.6 0 0 1 12 5c6.4 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.2M6.6 6.6A17.4 17.4 0 0 0 2 12s3.6 7 10 7a9.7 9.7 0 0 0 5.4-1.6M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="password"]').forEach((input) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'password-field';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'password-toggle';
        toggle.setAttribute('aria-label', etT('Показать пароль', 'Show password', 'Zobrazit heslo'));
        toggle.setAttribute('title', etT('Показать пароль', 'Show password', 'Zobrazit heslo'));
        toggle.setAttribute('aria-pressed', 'false');
        toggle.innerHTML = EYE_ICON;
        wrapper.appendChild(toggle);

        toggle.addEventListener('click', () => {
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            toggle.classList.toggle('is-visible', isPassword);
            toggle.innerHTML = isPassword ? EYE_OFF_ICON : EYE_ICON;
            toggle.setAttribute('aria-pressed', String(isPassword));
            toggle.setAttribute('aria-label', isPassword ? etT('Скрыть пароль', 'Hide password', 'Skrýt heslo') : etT('Показать пароль', 'Show password', 'Zobrazit heslo'));
            toggle.setAttribute('title', isPassword ? etT('Скрыть пароль', 'Hide password', 'Skrýt heslo') : etT('Показать пароль', 'Show password', 'Zobrazit heslo'));
        });
    });
});
