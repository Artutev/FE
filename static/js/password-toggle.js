document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="password"]').forEach((input) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'password-field';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'password-toggle';
        toggle.setAttribute('aria-label', 'Показать пароль');
        toggle.setAttribute('title', 'Показать пароль');
        toggle.setAttribute('aria-pressed', 'false');
        toggle.textContent = '◌';
        wrapper.appendChild(toggle);

        toggle.addEventListener('click', () => {
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            toggle.classList.toggle('is-visible', isPassword);
            toggle.textContent = isPassword ? '◉' : '◌';
            toggle.setAttribute('aria-pressed', String(isPassword));
            toggle.setAttribute('aria-label', isPassword ? 'Скрыть пароль' : 'Показать пароль');
            toggle.setAttribute('title', isPassword ? 'Скрыть пароль' : 'Показать пароль');
        });
    });
});
