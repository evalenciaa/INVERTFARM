document.addEventListener('DOMContentLoaded', () => {
    const dateElement = document.getElementById('current-date');
    const now = new Date();

    dateElement.textContent = new Intl.DateTimeFormat('es-MX', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    }).format(now);
    dateElement.dateTime = now.toISOString().slice(0, 10);
});
