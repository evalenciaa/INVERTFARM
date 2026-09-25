// La maqueta puede abrirse como archivo local; sus rutas siguen siendo las del sistema.
if (window.location.protocol === 'file:') {
    const requestedOrigin = new URLSearchParams(window.location.search).get('app');
    let appOrigin = 'http://127.0.0.1:8000';

    if (requestedOrigin) {
        try {
            const parsed = new URL(requestedOrigin);
            if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
                appOrigin = parsed.origin;
            }
        } catch (error) {
            // Se conserva el servidor local predeterminado.
        }
    }

    document.querySelectorAll('a[href^="/"]').forEach((link) => {
        link.href = new URL(link.getAttribute('href'), appOrigin).href;
    });
}
