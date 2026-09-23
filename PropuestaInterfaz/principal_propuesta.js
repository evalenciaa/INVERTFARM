document.addEventListener('DOMContentLoaded', () => {
    const dateElement = document.getElementById('current-date');

    dateElement.textContent = new Intl.DateTimeFormat('es-MX', {
        day: 'numeric', month: 'long', year: 'numeric'
    }).format(new Date());
    dateElement.dateTime = new Date().toISOString().slice(0, 10);
});
