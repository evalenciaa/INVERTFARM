document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");
    const errorMessage = document.getElementById("error-message");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    form.addEventListener("submit", function (e) {
        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();
        let isValid = true;

        // Resetear mensajes de error
        errorMessage.textContent = "";
        errorMessage.style.display = "none";
        usernameInput.classList.remove("input-error");
        passwordInput.classList.remove("input-error");

        // Validación 1: Campos vacíos
        if (!username || !password) {
            showError("Por favor, completa todos los campos.");
            highlightField(usernameInput, !username);
            highlightField(passwordInput, !password);
            isValid = false;
        }
        // Validación 2: Longitud mínima
        else if (username.length < 4 || password.length < 8) {
            showError("Usuario mínimo 4 caracteres. Contraseña mínimo 8.");
            highlightField(usernameInput, username.length < 4);
            highlightField(passwordInput, password.length < 8);
            isValid = false;
        }
        // Validación 3: Caracteres no permitidos (opcional)
        else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
            showError("El usuario solo puede contener letras, números y guiones bajos.");
            highlightField(usernameInput, true);
            isValid = false;
        }

        if (!isValid) {
            //e.preventDefault();
        }
    });

    // Funciones auxiliares
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = "block";
    }

    function highlightField(field, shouldHighlight) {
        if (shouldHighlight) {
            field.classList.add("input-error");
            field.focus();
        }
    }
});