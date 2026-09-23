document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.login-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const togglePassword = document.querySelector('.toggle-password');
    const submitButton = document.querySelector('.login-button');
    const buttonText = submitButton?.querySelector('.btn-text');
    const errorMessage = document.getElementById('error-message');

    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', () => {
            const isVisible = passwordInput.type === 'text';
            passwordInput.type = isVisible ? 'password' : 'text';
            togglePassword.setAttribute('aria-pressed', String(!isVisible));
            togglePassword.setAttribute('aria-label', isVisible ? 'Mostrar contraseña' : 'Ocultar contraseña');
            togglePassword.title = isVisible ? 'Mostrar contraseña' : 'Ocultar contraseña';
            passwordInput.focus({ preventScroll: true });
        });
    }

    [usernameInput, passwordInput].forEach((input) => {
        input?.addEventListener('input', () => {
            input.classList.remove('input-error');
            if (errorMessage) {
                errorMessage.textContent = '';
                errorMessage.classList.remove('is-visible');
            }
        });
    });

    form?.addEventListener('submit', (event) => {
        const username = usernameInput?.value.trim() || '';
        const password = passwordInput?.value || '';

        if (!username || !password) {
            event.preventDefault();
            usernameInput?.classList.toggle('input-error', !username);
            passwordInput?.classList.toggle('input-error', !password);
            if (errorMessage) {
                errorMessage.textContent = 'Ingresa tu usuario y contraseña para continuar.';
                errorMessage.classList.add('is-visible');
            }
            (!username ? usernameInput : passwordInput)?.focus();
            return;
        }

        if (submitButton && !submitButton.disabled) {
            submitButton.classList.add('is-loading');
            submitButton.disabled = true;
            submitButton.setAttribute('aria-busy', 'true');
            if (buttonText) buttonText.textContent = 'Validando acceso';
        }
    });
});
